# 02. Threat Model and Security Goals

## 2.1 Principals and channels

- **User (U)** — trusted as a source of *intent*, but **possibly non-expert**: may issue ambiguous requests and may approve actions whose canonical form they do not fully understand. This non-expertise is itself an attack surface (see §2.6 and the ambiguity-exploit adversary in §09).
- **System policy (P)** — trusted, administrator-authored, static for a task.
- **LLM agent(s)** — **untrusted**. May be fully compromised by injection. Only proposes actions and witnesses; decides nothing about security.
- **Tools/executors** — assumed **honest relative to their declared contracts** (a tool labeled `read_file` reads files; it does not secretly exfiltrate). Hidden side effects not in the contract are out of the *guarantee* but *measured* (adapter coverage, §05).
- **External environment (E)** — fully **attacker-controlled**: webpages, emails, documents, search results, tool *return values*, MCP server metadata, skill files, entries injected into long-term memory, and natural-language messages from lower-privilege agents.

## 2.2 Attacker capabilities

The attacker **can**:

- Control the content and metadata of any untrusted channel in E.
- Inject content into long-term memory (via untrusted content the agent chooses to store).
- Cause a low-privilege agent to send arbitrary natural-language messages to a high-privilege agent.
- Read the *public* CapProof specification, tool schemas, inference rules, public APIs, and (in one experimental condition) the verifier's **denial reasons**.
- Adapt across turns and across attempts (multi-round adaptive attacks).
- Exploit **ambiguity** in a genuine user request to steer the AuthSpec toward an over-broad scope (this is a distinct adversary; see §2.6).

The attacker **cannot**:

- Compromise the reference monitor, capability minting service, capability store, receipt store, tool adapters, executor, or canonicalizer (these are in the TCB).
- Forge or guess a valid capability handle or its MAC/signature, or read/modify the capability store.
- Forge a signed receipt.
- Modify the trusted user's original request text or the system policy.
- Compromise the cryptographic keys (minting key, receipt-signing key, agent identity keys).
- Compromise the underlying OS/tool binaries below the adapter boundary.

We **do not** assume the attacker is unable to influence the LLM's reasoning — we assume the opposite. The LLM is a hostile-controlled component inside the dataflow but outside the TCB.

## 2.3 Trusted Computing Base

| Component | Trusted? | Why it must be trusted | Failure consequence |
|---|---|---|---|
| Reference Monitor | **Yes** | Final allow/deny/ask boundary; implements inference rules deterministically | Any bug ⇒ unauthorized action admitted; soundness void |
| Capability Minting Service | **Yes** | Sole minter of capabilities; holds minting key | Forgery ⇒ attacker mints authority |
| Capability Store | **Yes** | Holds opaque caps, consumption/revocation/TTL state; atomic consume | Tamper/race ⇒ replay or forged consumption |
| Receipt Store | **Yes** | Holds signed receipts of derivations and outcomes | Forgery ⇒ false provenance accepted |
| Provenance Runtime | **Yes** | Records value origin and derivation; labels trust roots | Mislabel ⇒ proof built on false facts (measured, §08) |
| Tool Adapter + Contract Registry | **Yes** | Exposes *all* authority-bearing arguments and side effects of a tool | Missing field ⇒ silent bypass (residual characterized by coverage, not bounded, §05) |
| Canonicalizer | **Yes** | Maps arguments to canonical form for predicate matching | Incomplete ⇒ alias bypass (per-role decidability declared, §06) |
| Cryptographic keys | **Yes** | Root of unforgeability for caps/receipts/agent IDs | Compromise ⇒ total break (key mgmt, §06) |
| **AuthSpec Builder** | **No (untrusted)** | It is an LLM; cannot be a silent trust root | Misencoding ⇒ wrong scope; *handled by relativization + measurement, §2.6/§05* |
| Proof Synthesizer | **No (untrusted)** | Proposes witnesses; monitor re-verifies | Bad/forged witness ⇒ rejected by monitor |
| LLM agent(s) | **No (untrusted)** | Hostile-controlled reasoner | Compromise ⇒ contained: cannot mint/forge caps |
| External content / MCP metadata / skill files | **No (untrusted)** | Attacker-controlled | Cannot mint authority by `NO-MINT-UNTRUSTED` |
| Memory content | **No by default** | Attacker can inject | Cannot become authority root (stripping, §03.9) |

**TCB summary:** the deterministic enforcement core (monitor, stores, minting, adapters, canonicalizer, keys) is trusted; **every LLM in the system — including the AuthSpec Builder — is untrusted.** This is the central design discipline and the answer to "is AuthSpec generation trusted?": *no*.

## 2.4 Security property: Authorization Integrity

Let `roots = {TrustedUser, SystemPolicy, ExplicitEndorsement, ValidDelegation}`.

> **Authorization Integrity.** For every high-impact action *a* for which `Monitor.verify(a, π, State) = ALLOW`, there exists, for every authority-bearing argument `arg_i` of *a*, a capability chain `C_i` such that:
> 1. `C_i` is rooted in `roots`;
> 2. `C_i` authorizes `bind(arg_i = canon(v_i))` (predicate match on the canonical value);
> 3. `C_i` is unexpired, unrevoked, scope-matching, and (for high-impact roles) unconsumed at the moment of verification; and
> 4. no capability in `C_i` was created, widened, transferred, persisted, or forged by untrusted context.

Equivalently, in the projection used by the monitor:

```
verify(a, π, State) = ALLOW
  ⇒ ∀ authority-bearing arg_i ∈ a :
       ∃ capability chain C_i with root(C_i) ∈ roots
         ∧ C_i ⊢ bind(arg_i = canon(v_i))
         ∧ valid(C_i) ∧ scope_match(C_i, arg_i)
         ∧ (high_impact_role(arg_i) ⇒ unconsumed(C_i))
```

This property is about **authority provenance**. It is *agnostic to whether the LLM is compromised*.

### What Authorization Integrity does NOT assert

- It does not assert the *content* carried by an authorized action is benign or true.
- It does not assert the AuthSpec faithfully captured user intent — that is a **separate** property (§2.6), measured, not proven.
- It does not assert completeness of tool-adapter side-effect declarations — residual is bounded as a function of coverage (§05).

## 2.5 Authority-Laundering attack game

> **This game is the Oracle-AuthSpec enforcement game** (`G_force = G*`): it isolates *mechanism* soundness by giving the challenger the ground-truth AuthSpec. **Deployed experiments replace `G*` with the system-generated `G_sys`** (`G_force = G_sys`), can claim Authorization Integrity only relative to `G_sys`, and **separately measure AuthSpec faithfulness** (the `G_sys`-vs-`G*` gap, §2.6, §08). No capability is ever minted from `G*` in a deployed system — `G*` exists only in this game and in Oracle-AuthSpec Mode (§05).

**Setup.** Challenger fixes a trusted user request `u`, system policy `P`, tool catalog `Σ`, and — crucially — a **ground-truth AuthSpec `G*`** that encodes the authorization the user *actually* intended (authored by the task designer, not by the system's AuthSpec Builder). From `G*` the challenger mints initial capabilities `C0`. The reference monitor, stores, minting service, adapters, canonicalizer, and keys are honest.

**Adversary.** Controls all untrusted channels E and may run the (untrusted) agent and proof synthesizer adversarially. May read public spec and (in one condition) denial reasons.

**Execution.** The agent interacts with E and emits high-impact action `a` with witness candidate `π`.

**Win condition (laundering win).** The adversary wins iff:

```
Monitor.verify(a, π, State) = ALLOW
  ∧ ∃ authority-bearing arg_i ∈ a : canon(v_i) ∉ AuthClosure(G*, roots)
```

i.e., the monitor admitted an action one of whose authority-bearing arguments is **outside the authorization closure of the ground-truth AuthSpec**.

**Why `G*` (not the system's AuthSpec) defines the win.** This decouples two failure modes that the original plan conflated:
- *Enforcement failure*: the monitor admits an argument outside `G*`'s closure even though the system's AuthSpec was correct. Theorems 1–4 target this.
- *Elicitation failure*: the system's AuthSpec Builder produced an AuthSpec broader than `G*` (the ambiguity-exploit adversary, §2.6). This is **not** covered by the soundness theorems; it is measured as *AuthSpec faithfulness* (§08).

A reviewer asking "what if the AuthSpec is wrong?" gets a precise answer: enforcement soundness is relative to `G*`; faithfulness of `G*`'s machine-generated approximation is a separate, empirically reported quantity, with its own adversary and its own mitigation (canonical-action confirmation for high-impact roles, §03.11).

## 2.6 The AuthSpec faithfulness sub-problem (made explicit)

The AuthSpec Builder maps a natural-language request to a structured AuthSpec and is an **LLM**. Therefore:

- **It is not a trust root.** Capabilities are minted from the AuthSpec, but the *binding of high-impact authority-bearing arguments* (which recipients/paths/commands/endpoints are authorized) is **confirmed against the user**, not taken from the LLM's interpretation, whenever the request is ambiguous or the role is high-impact (§03.3, §03.11).
- **Faithfulness is measured, not assumed.** We define `AuthSpec faithfulness = Pr[ AuthClosure(G_sys) ⊆ AuthClosure(G*) ]` over a labeled set including deliberately ambiguous requests, and we report it as a first-class metric (§08, §10). Over-broadening (closure strictly larger than `G*`) is the dangerous direction and is reported separately from under-broadening (utility loss).
- **Adversary.** The *ambiguity-exploit* attack (§09) injects no instructions; it shapes untrusted context so that an ambiguous request ("send it to the team", "reply to whoever filed the ticket") is most naturally resolved toward an attacker-chosen value. This attacks the elicitation layer, and CapProof's defense is *not* a theorem but a mechanism (confirm canonical high-impact arguments) plus a measurement (faithfulness under attack).

This is the single most important honesty fix relative to the original plan and pre-empts the strongest reviewer objection.

## 2.7 Security goals (ranked)

1. **G1 (primary).** Enforce Authorization Integrity relative to `G*`: no laundering win under the game of §2.5, conditional on the assumptions of Theorem 1.
2. **G2.** Non-amplification under delegation: child agents cannot exceed parent authority.
3. **G3.** Prefix soundness: replanning cannot retroactively authorize past actions or revive consumed linear capabilities.
4. **G4 (adopted from CaMeL, secondary).** Prevent exfiltration of secret data over unauthorized data flows via data-flow capabilities.
5. **G5 (non-formal, measured).** High AuthSpec faithfulness, including under the ambiguity-exploit adversary, with low endorsement burden.
