# 03. System Design

## 3.1 Architecture and dataflow

```text
                          (trusted)                         (untrusted)
  User request ──▶ AuthSpec Builder*  ──┐               ┌── External env E
                   (LLM, untrusted;     │               │   web/email/docs/
                    high-impact args    │               │   tool outputs/
                    confirmed, §3.11)   ▼               │   MCP metadata/
  System policy ─────────────▶ Capability Minting ──▶ Capability Store     skill files
                                  Service (TCB)          (TCB)              │
                                                          ▲                 │
                                                          │                 ▼
                          ┌───────────────────────────────┴──────────┐  Agent Runtime
                          │                                            │  (LLM, untrusted)
                          │   Provenance Runtime (TCB) ── Receipt      │     │ proposes
                          │   Memory Authority Stripper (TCB)  Store   │     │ (action a,
                          │   Delegation Manager (TCB)        (TCB)    │     │  witness π)
                          │   Canonicalizer (TCB)                      │     ▼
                          │   Tool Contract Registry (TCB)             │  Proof Synthesizer*
                          └───────────────────────────────┬───────────┘  (untrusted)
                                                           ▼
                                          Deterministic Reference Monitor (TCB)
                                                           │
                                          verify → reserve → execute → commit → consume
                                                           │
                                              ALLOW / DENY(reason) / ASK(challenge)
                                                           │
                                                    Tool Executor (TCB)
```

`*` = untrusted component. Everything else is in the TCB (§02.3).

**Design discipline:** the AuthSpec Builder runs **before** the agent touches any untrusted content. Capabilities are minted from the AuthSpec (with high-impact arguments confirmed, §3.11) so that the set of mintable authorities is fixed before E can influence anything. This "plan-before-untrusted" structure is shared with CaMeL; CapProof's additions are the consumable action-authority dimension, memory stripping, delegation certificates, and one-shot endorsement.

## 3.2 Component responsibilities

| Component | TCB | Responsibility |
|---|---|---|
| AuthSpec Builder | No | NL request → structured AuthSpec; proposes scope, never finalizes high-impact bindings |
| Capability Minting Service | Yes | Mints opaque, signed capabilities from AuthSpec/policy/endorsement/delegation |
| Capability Store | Yes | Stores caps + consumption/revocation/TTL/nonce; atomic reserve+consume |
| Provenance Runtime | Yes | Tracks value origin + derivation; assigns trust-root labels |
| Receipt Store | Yes | Stores signed receipts (derivation, endorsement, outcome) |
| Memory Authority Stripper | Yes | Strips authority on memory write; gates trust upgrade on read |
| Delegation Manager | Yes | Issues/validates attenuation-only delegation certificates |
| Controlled Endorsement Manager | Yes | Turns user approval into one-shot, non-transferable capability bound to canonical action |
| Tool Contract Registry | Yes | Declares every authority-bearing arg + side effect per tool; reports coverage |
| Canonicalizer | Yes | Per-role canonicalization; declares decidability per role |
| Proof Synthesizer | No | Searches for a witness π given AuthSpec/caps/receipts/contracts |
| Reference Monitor | Yes | Deterministically verifies (a, π); orchestrates two-phase commit |
| Tool Executor | Yes | Executes only after reserve; emits outcome receipt |

## 3.3 AuthSpec Builder (untrusted; with confirmed high-impact bindings)

Input: `user_request + tool_catalog + system_policy`. Output: structured AuthSpec.

```json
{
  "auth_id": "auth_001",
  "task_id": "task_42",
  "principal": "user_alice",
  "intent": "summarize_and_send",
  "resources": [{"kind": "file", "path": "/workspace/report.pdf", "permission": "read"}],
  "transforms": [{"op": "summarize", "input": "/workspace/report.pdf",
                  "output_class": "summary(report.pdf)"}],
  "actions": [{"tool": "send_email", "recipient": "alice@example.com",
               "data_class": "summary(report.pdf)", "max_uses": 1,
               "binding_status": "user_confirmed"}],
  "forbidden": ["raw_file_egress", "shell_exec",
                "write_outside_workspace", "send_to_unlisted_recipient"],
  "expires_at": "task_end"
}
```

**Key rule (faithfulness mitigation):** for any **high-impact authority-bearing argument** (recipient/path/command/endpoint), the AuthSpec records a `binding_status`:
- `explicit` — the value appears verbatim and unambiguously in the user request → mint directly.
- `user_confirmed` — value was confirmed via a canonical-action challenge (§3.11) → mint.
- `inferred` — value was inferred by the LLM from an ambiguous request → **do not mint a usable capability**; require one-shot endorsement at action time.

This is how the untrusted AuthSpec Builder is prevented from being a silent trust root: it can *propose* but cannot *authorize* a high-impact binding by inference alone.

## 3.4 Capability Minting Service

Mints from four roots only (USER, POLICY, ENDORSEMENT, DELEGATION). Each capability is an **opaque handle** (random 128-bit id) plus a stored record (schema in §04). The handle is bound to the record via a MAC under the minting key; capabilities are never natural-language strings and never leave the store as plaintext records to the agent.

## 3.5 Capability Store and two-phase consumption

The store is the linchpin for replay/TOCTTOU resistance. Capabilities (for high-impact roles) are **linear/affine** and consumed via a two-phase protocol:

```
verify(a, π) ──▶ reserve(cap_ids, action_hash, lease=τ) ──▶ execute(a)
        ──▶ commit(receipt) ──▶ consume(cap_ids)
on any failure / lease expiry ──▶ release(cap_ids)
```

- **`reserve`** is an atomic compare-and-set on each capability's status: `available → reserved(action_hash, nonce, lease)`. Two agents presenting the same `max_uses=1` cap cannot both reserve (CAS resolves one winner; the loser gets `ConsumedCap`/`Reserved`). This closes the concurrency TOCTTOU the original plan ignored.
- **`commit`** records a signed outcome receipt and flips `reserved → consumed`. Consumption is **idempotent** keyed by `(cap_id, nonce)` so retried commits do not double-spend or revive.
- **`release`** returns a leased-but-unused cap to `available` (e.g., tool failed before side effect) without consuming a use, gated by the executor's outcome receipt so the agent cannot force a release after a side effect occurred.
- **Reusable** caps (e.g., `read_file` within scope) skip consumption but still respect TTL/revocation.

State machine per capability: `available → reserved → consumed` (+ `revoked` reachable from any state; + `expired` on TTL).

## 3.6 Provenance Runtime

Every runtime value `v` carries a provenance record: origin source, derivation chain, trust-root label. Sources are partitioned into trusted roots vs. untrusted (`{Webpage, EmailBody, ToolOutput, MCPMetadata, SkillFile, UnendorsedMemory, LowPrivAgentMsg}`). Derivations through declared-safe transforms preserve a *derived-from* relation used by `DERIVE-CONTENT`.

Two implementations are built and **both reported** (§08): an **oracle** provenance (ground-truth labels from the benchmark) and an **automatic** provenance (taint-style propagation from adapter I/O). The gap between them is the system's exposure to provenance error and is measured by sensitivity analysis — *not* assumed away.

## 3.7 Receipt Store

Signed receipts for: (a) safe derivations (`y = summarize(x)`), (b) endorsements, (c) tool outcomes. Receipts are the witness's evidence that a derivation/endorsement actually occurred; the monitor verifies receipt signatures under the receipt-signing key.

## 3.8 Proof Synthesizer (untrusted)

Given a candidate action, the AuthSpec, the capability store view, receipts, and tool contracts, it **searches** for a witness π (schema §04): the set of capability uses, argument bindings, derivation steps, and delegation/endorsement chains that, if valid, justify the action. It may be the agent LLM itself or a separate module. Because it is untrusted, it can return garbage or adversarial witnesses; the monitor independently re-verifies everything. Its only job is to make the monitor's job a *verification* (linear in |π|) rather than a *search* (see §04.4 and the complexity argument for why carrying π is worthwhile, and the `ProofObjectRemoved` ablation in §09 that tests it).

## 3.9 Memory Authority Stripper (core mechanism)

Principle: **memory stores content/facts, never authority, by default.**

```python
def strip_authority(entry, provenance):
    # entry: {kind, payload, proposed_role?}
    if provenance.root in TRUSTED_ROOTS_FOR_PERSISTENCE:   # {ExplicitEndorsement(persistent=True)}
        return entry  # may carry persistent authority ONLY if explicitly approved as persistent
    # otherwise: demote any authority-bearing role to inert content
    entry.proposed_role = None
    entry.trust_root = "UnendorsedMemory"
    return entry  # readable as fact, never usable to bind an authority-bearing argument
```

On **read**, a memory value is never trust-upgraded: a value whose stored root is `UnendorsedMemory` resolves to a runtime value with that same untrusted root, so `NO-MINT-UNTRUSTED` blocks its use as recipient/path/command/endpoint. The *only* way memory carries authority is an endorsement explicitly minted as `persistent=True` (rare, logged, revocable). This is what blocks Example A (§01.5).

## 3.10 Delegation Manager (attenuation-only)

Cross-agent authority requires a signed certificate:

```text
DelegationCert {
  parent_agent, child_agent,
  parent_caps:   [cap_id...],
  child_caps:    [cap_id...],       # each minted as an attenuation of a parent cap
  attenuation_proof,                # witness that child ⊆ parent (per dimension)
  expires_at,                       # ≤ min(TTL(parent_caps))
  non_redelegable: bool,            # default true
  signature                        # under delegating agent's key
}
```

Monitor checks, per child cap: scope(child) ⊆ scope(parent); `TTL(child) ≤ TTL(parent)`; `max_uses(child) ≤ max_uses(parent)`; **no new recipient/endpoint/command/file_path** outside the parent predicate; redelegation only if `delegable` was explicitly preserved. A natural-language relay carries no certificate and therefore no authority — this blocks Example B.

## 3.11 Controlled Endorsement Manager (one-shot, canonical-bound)

Ordinary human-in-the-loop is insufficient: a natural-language "yes" can be re-used, widened, persisted, or transferred. CapProof's endorsement:

- is **scoped, one-shot (linear, `max_uses=1`), non-transferable, non-persistent**, bound to `task_id`;
- is bound to the **canonical** action (canonical recipient/path/command/endpoint and data_class), and **the challenge displays the canonical meaning to the user** — closing the approval-screen confused-deputy where the user approves a human-readable string but the system binds a different canonical value;
- is **revocable** and **logged as a structured receipt**.

Endorsement challenge template:

```text
CapProof needs your approval for a high-impact action.

  Task:        task_42  ("Summarize report and send")
  Action:      SEND EMAIL
  Recipient:   bob@example.com         ← canonical, resolved (not a display alias)
  Data:        summary(report.pdf)     ← NOT the raw file
  Endpoint:    (none)
  One-time:    this approval authorizes exactly ONE send to this recipient,
               for this task only, and cannot be reused, widened, or transferred.

Approve?  [Approve once]  [Deny]
```

Approval mints `Cap(root=ENDORSEMENT, linearity=linear, max_uses=1, task_id=task_42, action_hash=H(canonical_action))`. The verifier consumes it exactly once.

## 3.12 Public API

```text
open_task(user_request, tool_catalog) -> {task_id, authspec_id, initial_caps_summary}
    Runs AuthSpec Builder, confirms high-impact explicit bindings, mints C0.

guard(task_id, action, runtime_state) -> ALLOW | DENY(reason) | ASK(challenge)
    The hot path. Canonicalizes action, accepts witness π from runtime_state,
    runs verify(), and on ALLOW performs reserve. Returns a challenge if the only
    obstacle is a missing endorsable high-impact binding.

record_endorsement(challenge_response) -> {cap_id} | REJECTED
    Validates the user's approval against the displayed canonical action; mints
    one-shot endorsement capability.

close_action(action_id, outcome) -> ok
    Executor reports outcome; monitor commits receipt and consumes/releases caps.
```

## 3.13 Reference Monitor verifier (deterministic)

```python
def verify(action, proof, cap_store, receipt_store, tool_contracts):
    # 0. canonicalize; reject if any high-impact arg lacks a total canonical form
    contract = tool_contracts.get(action.tool)            # DENY UnknownTool if missing
    cargs = canonicalize(action, contract)                # DENY CanonicalizationMismatch
    if contract.coverage < 1.0 and action.touches_uncovered_field(cargs):
        return DENY("AdapterCoverageGap")                 # fail-closed on undeclared fields

    # 1. structural well-formedness of the witness (no trust yet)
    if not proof.well_formed() or proof.action_hash != H(cargs):
        return DENY("ProofNotCanonical")

    # 2. every authority-bearing argument must be bound by a valid capability
    for arg in contract.authority_bearing_args(cargs):
        binding = proof.binding_for(arg)
        if binding is None:
            return DENY(f"NoCap(role={arg.role})")
        cap = cap_store.lookup(binding.cap_id)            # opaque; MAC-checked
        if cap is None:                                   return DENY("NoCap")        # forgery/guess
        if cap.revoked or cap.expired():                  return DENY("CapInvalid")
        if not predicate_matches(cap, arg.value):         return DENY("CapPredicateMismatch")
        if cap.task_id  != action.task_id:                return DENY("TaskMismatch")
        if cap.subject_agent != action.agent_id:          return DENY("AgentMismatch")
        if cap.root in UNTRUSTED_ROOTS:                   return DENY("MemoryAuthorityUse/NoMint")
        if high_impact(arg.role) and cap.status != "available":
            return DENY("ConsumedCap")                    # replay

    # 3. derivation steps must be backed by signed receipts (DERIVE-CONTENT)
    for step in proof.derivation_steps:
        if not receipt_store.verify(step.receipt) or step.op not in SAFE_TRANSFORMS:
            return DENY("BadDerivation")

    # 4. delegation chain must be attenuation-valid (DELEGATE-ATTENUATE)
    if proof.delegation_chain and not delegation_valid(proof.delegation_chain, cap_store):
        return DENY("DelegationAmplification/Missing")

    # 5. data-flow / readers check (adopted CaMeL-style; G4)
    if not dataflow_allows(action, proof, cap_store):
        return DENY("UnauthorizedDataFlow")

    return ALLOW   # caller then reserve()→execute()→commit()→consume()
```

The monitor **re-derives every check**; the witness is a hint that makes step 2–4 a lookup/verification rather than a search. The denial-reason taxonomy doubles as the failure-reason metric (§08) and is the thing whose information leakage to adaptive attackers we *measure* (§09.4).

## 3.14 Defenses against the four runtime attacks

- **Fake proof injection** (witness in untrusted content): step 1/2 — a "proof" that is a natural-language claim has no `cap_id` resolving in the store ⇒ `NoCap`/`ProofNotCanonical`.
- **Fake capability** (guessed/forged handle): step 2 — `cap_store.lookup` fails MAC/lookup ⇒ `NoCap`.
- **Replay** (re-using a consumed cap or old witness): step 2 status check + nonce ⇒ `ConsumedCap`; `action_hash` binding ⇒ `TaskMismatch`.
- **TOCTTOU** (concurrent use of one linear cap): two-phase `reserve` CAS (§3.5) ⇒ one winner, loser `Reserved`/`ConsumedCap`.
