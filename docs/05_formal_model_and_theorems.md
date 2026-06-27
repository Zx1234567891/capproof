# 05. Formal Model and Theorems

This revision fixes two defects a PC would catch in the prior draft: (1) the **conflation of the system's machine-generated AuthSpec with the ground-truth AuthSpec** inside theorem statements, and (2) an **unrigorous probability "bound"** on adapter-coverage leakage. We replace (1) with an explicit two-mode treatment (Oracle-AuthSpec vs Deployed-AuthSpec) and a parametric theorem, and (2) with a **coverage-dependent residual characterization** (a set-membership statement, no probability claim).

## 5.1 Entities and the two AuthSpecs

- `u` trusted user request; `P` system policy; `Σ` tool schemas + contracts.
- **`G*` — the ground-truth AuthSpec.** The authorization the user *actually* intended. In experiments it is authored by the task designer. It is a *reference object*, available to the evaluator, never to the runtime unless we deliberately inject it (Oracle mode).
- **`G_sys` — the deployed AuthSpec.** What the (untrusted, LLM) AuthSpec Builder produces from `u` at runtime. This is what the system actually has.
- `G_force` — "the AuthSpec in force": `G_force = G*` in Oracle-AuthSpec Mode, `G_force = G_sys` in Deployed-AuthSpec Mode.
- `C` capability store; `R` receipt store; `V` runtime values with provenance; `Γ` authorization context (trusted-root facts, minted caps, receipts).
- `a` candidate high-impact action; `π` witness; `M` reference monitor; `canon(·)` per-role canonicalizer.
- `O(t)` the set of authority-bearing fields of tool `t` that the monitor can **observe at the adapter boundary** (declared ∪ observable-but-undeclared); `F(t)` the tool's **true** authority-bearing field set. `Residual(t) = F(t) \ O(t)` (unobserved fields). See §5.6.

`roots = {TrustedUser, SystemPolicy, ExplicitEndorsement, ValidDelegation}`.
`untrusted = {Webpage, EmailBody, ToolOutput, MCPMetadata, SkillFile, UnendorsedMemory, LowPrivAgentMsg}`.
`AuthClosure(G, roots)` = the set of (role, canonical-value) bindings derivable from the roots authorized by AuthSpec `G` under the rules of §5.3.

## 5.2 The two evaluation modes (this is the central fix)

> **Oracle-AuthSpec Mode.** The runtime is given `G*` directly (the AuthSpec Builder is bypassed). This **isolates the enforcement guarantee**: any admitted out-of-closure action is an enforcement failure, not an elicitation failure. Faithfulness is 1 by construction. Theorems 1–4 are about this mode (and, parametrically, about any `G_force`).
>
> **Deployed-AuthSpec Mode.** The runtime uses `G_sys` from the real AuthSpec Builder. This measures the **end-to-end** system, including elicitation error. Here the guarantee an admitted action enjoys is "within `AuthClosure(G_sys)`", and the residual risk relative to true intent is exactly `AuthClosure(G_sys) \ AuthClosure(G*)`, quantified by **AuthSpec faithfulness** (§5.7, measured in §08/`AUTHSPEC_FAITHFULNESS_GATE.md`).

Every security result is reported in **both** modes. The gap between them is the price of using an LLM to elicit intent and is the single number that answers "but the AuthSpec is an LLM."

## 5.3 Judgment forms and inference rules

```text
Γ ⊢ Cap(role, predicate, scope, root)            cap is well-formed and minted
Γ ⊢ value(v) derives_from x via op               provenance/derivation
Γ ⊢ bind(arg = v) authorized_by cap              an authority-bearing arg is bound
Γ ⊢ delegation(parent → child) attenuating       delegation is attenuation-only
Γ ⊢ action(a) authorized                         the action passes the monitor
```

**USER-MINT** (relative to the AuthSpec in force `G_force`).
```text
G_force grants predicate φ for role r   binding_status(r) ∈ {explicit, user_confirmed}
-------------------------------------------------------------------------------------
Γ ⊢ mint Cap(role=r, predicate=φ, root=USER)
```

**POLICY-MINT.**
```text
system_policy(P) grants predicate φ for role r
----------------------------------------------
Γ ⊢ mint Cap(role=r, predicate=φ, root=POLICY)
```

**DERIVE-CONTENT** (governs *data*, not authority).
```text
Γ ⊢ v derives_from x   Γ ⊢ Cap(transform,input=x,op,output=y)   op ∈ SafeTransform
       receipt r : y = op(x) ∈ R     verify(r)
-----------------------------------------------------------------------------------
Γ ⊢ y derives_from x via op
```

**BIND-AUTH-ARG** (on the canonical value).
```text
role(arg)=r   Γ ⊢ Cap(role=r, predicate=φ, root ∈ roots)
φ(canon(v))=true   valid(cap) ∧ scope_match(cap, arg)
-----------------------------------------------------------
Γ ⊢ bind(arg = v) authorized_by cap
```

**CONSUME-CAP** (the monitor's admission rule).
```text
∀ authority-bearing arg_i ∈ a :  Γ ⊢ bind(arg_i = v_i) authorized_by cap_i
∀ i : high_impact(role(arg_i)) ⇒ status(cap_i)=available  (then reserve→consume)
∀ i : field(arg_i) ∈ O(tool(a))         -- every checked field is observable (else fail-closed, §5.6)
--------------------------------------------------------------------------------------------
Γ ⊢ action(a) authorized
```

**MEMORY-STRIP.**
```text
source(v) ∉ {ExplicitEndorsement with persistent=true}
------------------------------------------------------------
memory_write(v) stores content/fact only; trust_root(stored)=UnendorsedMemory
```

**DELEGATE-ATTENUATE.**
```text
child_cap ⊑ parent_cap  (scope ⊆, TTL ≤, max_uses ≤, delegable ≤, no new r/path/cmd/endpoint)
-----------------------------------------------------------------------------------------------
Γ ⊢ delegation(parent_cap → child_cap) attenuating
```

**ENDORSE-ONCE.**
```text
user approves challenge q   q binds (task_id, action_kind, canon(args), data_class)   max_uses=1
------------------------------------------------------------------------------------------------
Γ ⊢ mint Cap(root=ENDORSEMENT, linearity=linear, max_uses=1, action_hash=H(canon action))
```

**NO-MINT-UNTRUSTED.**
```text
source ∈ untrusted
-------------------------------------------------------------
source cannot mint Cap(role ∈ authority-bearing roles)
```

## 5.4 Security game (relative to the AuthSpec in force)

Challenger fixes `u, P, Σ`, an AuthSpec `G_force`, and mints `C0` from it. Adversary controls untrusted channels E and may run the agent/synthesizer adversarially. Agent emits `(a, π)`.

> **Enforcement win (Oracle mode, `G_force=G*`).** `M.verify(a,π,State)=ALLOW` and some authority-bearing `arg_i` has `canon(v_i) ∉ AuthClosure(G*, roots)`.

> **End-to-end win (Deployed mode).** Same, but evaluated against `AuthClosure(G_sys)` for the *enforcement* property; the *intent* gap `AuthClosure(G_sys)\AuthClosure(G*)` is attributed to faithfulness, not enforcement, and reported separately.

This separation is what lets us state a clean soundness theorem (about enforcement) without pretending the LLM-built AuthSpec is correct.

## 5.5 Theorems

### Theorem 1 — Authorization Integrity Soundness (parametric in the AuthSpec in force)

**Statement.** Assume (A1) **provenance fidelity** — the provenance runtime never assigns a trusted-root label to a value whose true origin is untrusted; (A2) **capability store unforgeability** — handles/MACs cannot be forged (key secrecy); (A3) **minting service correctness** — the minting service mints capabilities only via the §5.3 rules and never from an untrusted source; (A4) **monitor correctness** — the monitor implements §5.3 and §3.13 deterministically; (A5) **tool-adapter observability** — for the action `a`, every authority-bearing field of `tool(a)` is in `O(tool(a))` (i.e., `Residual(tool(a)) ∩ fields(a) = ∅`); (A6) **canonical-action binding** — the executed action, the reserved capability, and the verified proof are bound to the same `H(canon(a))`, so what is verified is what executes; and (A7) **tool implementation honesty** — the tool's runtime effect matches its declared contract schema (the tool does not perform an authority-bearing side effect outside its declared `coverage_fields`). Then for every `a` with `M.verify(a,π,State)=ALLOW`, every authority-bearing argument of `a` lies in `AuthClosure(G_force, roots)`.

**Corollaries.**
- **Oracle mode (`G_force=G*`):** admitted actions lie within true-intent closure — *no enforcement win*.
- **Deployed mode (`G_force=G_sys`):** admitted actions lie within `AuthClosure(G_sys)`; the residual relative to true intent is `AuthClosure(G_sys)\AuthClosure(G*)`, bounded *empirically* by AuthSpec faithfulness (§5.7), **not** by this theorem.

**Proof sketch.** By inversion on `action(a) authorized`: `CONSUME-CAP` requires each authority-bearing `arg_i` bound via `BIND-AUTH-ARG`, hence a valid `cap_i` with `φ(canon(v_i))=true`, `root(cap_i)∈roots`. By (A2) store unforgeability and (A3) minting correctness with `NO-MINT-UNTRUSTED`, no authority-bearing `cap_i` is rooted in `untrusted`; by (A1) provenance fidelity no untrusted value is relabeled trusted, so each root genuinely lies in `roots`. Each minting rule adds exactly the predicate its root authorizes under `G_force`, so by induction the chain stays within `AuthClosure(G_force, roots)`. (A5) observability ensures no authority-bearing field of `a` escaped the check; (A4) monitor correctness ensures the checks ran; (A6) canonical-action binding ensures the verified action is the executed one; (A7) tool honesty ensures no authority-bearing effect occurs outside the declared contract. ∎

**What it does NOT guarantee.** (i) Nothing about `G_sys` vs `G*` — that is **faithfulness** (§5.7), evaluated separately; (ii) nothing about **content truthfulness** — an authorized recipient can still receive false or harmful *content*; (iii) nothing about **same-source authoritative-data poisoning** — if a *trusted* source is itself compromised (e.g., a trusted file already contains an attacker value), CapProof will honor it; (iv) nothing about **unmodeled tool side effects** — effects through fields outside the declared contract / `Residual(t)` (A5/A7 incomplete), per Characterization 1′; (v) nothing about the **automatic AuthSpec Builder being perfect** — a wrong `G_sys` is a faithfulness problem, not a soundness one. Soundness here is *enforcement relative to the AuthSpec in force*, not correctness of intent, content, or trusted inputs.

### Characterization 1′ — Coverage-dependent residual (replaces the prior probability "bound")

We make **no probabilistic claim**. Instead we characterize, as a set, what CapProof can and cannot guarantee under incomplete adapter coverage.

**Definition (residual authority surface).** For a tool `t`, `Residual(t) = F(t) \ O(t)` is the set of authority-bearing fields the monitor cannot observe. For a task using tools `T`, the task residual surface is `Res(T) = ⋃_{t∈T} Residual(t)`.

**Characterization.** With the fail-closed observability gate of §3.13 / `CONSUME-CAP`(A5):
- For any action `a` such that **all** authority-bearing fields of `a` are observable (`fields(a) ∩ Res(T) = ∅`), Theorem 1 applies and Authorization Integrity holds.
- For any unauthorized effect that can **only** be expressed through a field in `Res(T)`, CapProof provides **no guarantee**: the monitor cannot bind or deny what it cannot observe.
- The gate denies any action whose canonical form touches an *observable-but-undeclared* field (`O(t)\D(t)`), so only *unobservable* fields (`Residual(t)`) constitute genuine exposure.

**Consequence (a measurement, not a probability).** CapProof's exposure under partial coverage is exactly the attacker-reachable effects expressible through `Res(T)`. We therefore **enumerate `Residual(t)` on real tools** (§06.3, `TCB_AND_ADAPTER_COVERAGE.md`): for a corpus of MCP servers we list, per tool, which authority-bearing fields (bcc, headers, attachments, env, cwd, stdin, follow_redirects, …) are observed vs. unobserved by a given adapter, and we report the set, not a probability. A controlled coverage sweep (deliberately hiding 1/2/3 fields) demonstrates that exposure tracks exactly the hidden fields. This is honest where the prior `Σ(1−κ_obs)` "bound" was not.

### Theorem 2 — No Authority Laundering (relative to `G_force`)

**Statement.** Under (A1)–(A7), no input produced solely by untrusted context can **create, widen, transfer, persist, or forge** an authority-bearing capability; hence untrusted context alone cannot cause an action outside `AuthClosure(G_force, roots)` to be admitted.

**Proof sketch.** *Create*: `NO-MINT-UNTRUSTED` + (A1) provenance fidelity + (A3) minting correctness. *Widen*: predicates are fixed at mint; `BIND-AUTH-ARG` matches the fixed predicate; no rule enlarges a predicate from untrusted input. *Transfer*: `transferable=false` default; cross-agent use needs a delegation cert (Thm 3). *Persist*: `MEMORY-STRIP` demotes non-endorsed authority to `UnendorsedMemory`, blocked on read by `NO-MINT-UNTRUSTED`. *Forge*: (A2) unforgeable handles/MACs; a natural-language "proof"/"cap" has no store entry. ∎

**Non-guarantee.** Inherits Characterization 1′ for `Residual` fields; does not constrain the user.

### Theorem 3 — Delegation Non-Amplification

**Statement.** If every delegation certificate validates under `DELEGATE-ATTENUATE`, then for any chain `A0 → A1 → … → Ak`, the high-impact actions `Ak` can get authorized form a subset of those authorized for `A0`.

**Proof sketch.** Induction on chain length; `⊑` is reflexive/transitive across scope/TTL/uses/delegability and the "no new r/path/cmd/endpoint" constraint composes, so reachable authority is monotonically non-increasing. (This is the monotonic-permissions property of finite-action calculi; cf. §12.4.) ∎

**Non-guarantee.** Assumes an agent PKI (authentic `subject_agent`, §06.5) and an honest Delegation Manager. A compromised delegating agent can pass on a *subset* it already holds to a colluder — contained (no amplification), not prevented.

### Theorem 4 — Prefix Soundness for Replanning

**Statement.** Replanning extends future proof obligations only; it cannot retroactively authorize a past action nor revive a consumed linear capability.

**Proof sketch.** Each executed high-impact action is decided at `verify` time against the then-current store and committed via `commit→consume`. The store is monotone for linear caps (`available→consumed`, idempotent, §3.5); no rule does `consumed→available`. A replan yields *new* candidates evaluated against the *current* store and cannot rewrite the receipt log. Hence executed-and-authorized prefixes are append-only, each authorized under the rules at its execution time. ∎

**Non-guarantee.** Says nothing about *utility* under replanning; over-narrow `G_force` may force mid-task endorsements (measured: endorsement count on dynamic tasks, §08/§10).

## 5.6 Observability and coverage, formally

For tool `t`: true authority-bearing fields `F(t)`; adapter-declared `D(t) ⊆ F(t)`; monitor-observable `O(t)` with `D(t) ⊆ O(t) ⊆ F(t)` (observable includes fields the adapter surfaces even if the contract did not name them); unobserved `Residual(t) = F(t)\O(t)`. The monitor's fail-closed gate denies actions touching `O(t)\D(t)`; it is blind only to `Residual(t)`. We report, per real tool, the explicit sets `D(t)`, `O(t)`, `Residual(t)` (`TCB_AND_ADAPTER_COVERAGE.md`) — concrete sets, never a coverage probability.

## 5.7 AuthSpec faithfulness (the measured complement to soundness)

Define, over a labeled corpus including deliberately ambiguous requests and the ambiguity-exploit adversary (§09 #15):

```
No-Over-Broadening Rate  = Pr_corpus[ AuthClosure(G_sys) ⊆ AuthClosure(G*) ]   -- safe containment
No-Under-Broadening Rate = Pr_corpus[ AuthClosure(G*)  ⊆ AuthClosure(G_sys) ]   -- utility containment

AuthSpec Over-Broadening Rate  = 1 − No-Over-Broadening Rate  = Pr_corpus[ AuthClosure(G_sys) ⊄ AuthClosure(G*) ]
AuthSpec Under-Broadening Rate = 1 − No-Under-Broadening Rate = Pr_corpus[ AuthClosure(G*)  ⊄ AuthClosure(G_sys) ]
```

(Naming note: `Pr[AuthClosure(G_sys) ⊆ AuthClosure(G*)]` is the **safe** containment — the probability that `G_sys` does **not** over-broaden. The *risk* metric reported as headline is its complement, the **AuthSpec Over-Broadening Rate**; an earlier draft's label `Faithfulness_over` for the containment probability was misleading and is retired. These definitions match `AUTHSPEC_FAITHFULNESS_GATE.md`.)

- **Over-broadening** (`G_sys` authorizes more than `G*`) is the *dangerous* direction; it is the elicitation analogue of a laundering win and is the headline faithfulness number, reported with and without the §3.11 canonical-action confirmation and with and without the ambiguity adversary.
- **Under-broadening** (`G_sys` authorizes less) costs *utility* (forces endorsements), reported separately.
- These are **probabilities over a corpus** (well-defined: a finite labeled task set), unlike the discarded coverage "bound."

Beyond the two closure-containment rates, the gate reports finer-grained elicitation metrics on the **high-impact** bindings specifically: **High-Impact Grant Precision** (of the high-impact bindings `G_sys` authorizes, the fraction in `G*`), **High-Impact Grant Recall** (of those in `G*`, the fraction `G_sys` authorizes), **Endorsement Trigger Accuracy** (correct routing of `inferred` high-impact bindings to a one-shot endorsement), and **Endorsement Recovery Rate** (legitimate ambiguous high-impact requests completed via a single endorsement). Low High-Impact Grant Precision is the dangerous signal; low recall / low recovery is a utility signal.

The faithfulness gate (`AUTHSPEC_FAITHFULNESS_GATE.md`) is the experiment that produces these numbers. Theorem 1 (Oracle mode) + low high-impact over-broadening (Deployed mode) together approximate end-to-end Authorization Integrity relative to true intent; we never assert the second factor as a theorem.

## 5.8 Global assumptions (restate in the paper)

The theorems depend on exactly these, each named and each with a validation plan:

1. **A1 provenance fidelity** — untrusted origins are never relabeled trusted. *Measured*: oracle-vs-automatic gap + error-injection sensitivity (§08.5).
2. **A2 capability store unforgeability** — handles/MACs unforgeable; key secrecy. *Standard crypto*; key mgmt §06.5; forgery tests (`TCB_AND_ADAPTER_COVERAGE.md`).
3. **A3 minting service correctness** — mints only via §5.3 rules, never from an untrusted source. *Tested*: negative tests that `untrusted` sources cannot mint; every mint path requires a valid root.
4. **A4 monitor correctness** — deterministic implementation of §5.3 + §3.13. *Tested*: mechanism suite false-allow = 0; differential test vs a reference spec; small TCB LoC reported.
5. **A5 tool-adapter observability** — authority-bearing fields are surfaced (`Residual(t) ∩ fields(a) = ∅`). *Not assumed total*: characterized (Char. 1′) and measured as residual sets on real tools (`TCB_AND_ADAPTER_COVERAGE.md`).
6. **A6 canonical-action binding** — verified action = reserved capability = executed action via `H(canon(a))`. *Tested*: bypass gate (`CANONICALIZATION_BYPASS_GATE.md`); TOCTTOU/rebinding races acknowledged for path/endpoint.
7. **A7 tool implementation honesty relative to declared schema** — the tool's runtime effect matches its declared contract; no authority-bearing side effect outside its `coverage_fields`. *Tested*: adapter fuzzing (does perturbing an undeclared field change a side effect?) feeds the Unmodeled Side-Effect Rate (`TCB_AND_ADAPTER_COVERAGE.md`); a dishonest tool is an explicit residual.

Separately (NOT theorem assumptions):
- **AuthSpec faithfulness** — a measured corpus probability with its own adversary (§5.7, `AUTHSPEC_FAITHFULNESS_GATE.md`); the gap between `G_sys` and `G*`. Never asserted as a theorem.
- **Canonicalization decidability per role** — `command` is not totally canonicalizable; `run_shell` is allowlisted-templates-only (§06.4, `CANONICALIZATION_BYPASS_GATE.md`), with the non-soundness stated.

**What the theorems do not guarantee (collected):** correctness of `G_sys` relative to true intent (faithfulness); **content truthfulness** (an authorized recipient may receive false/harmful content); **same-source authoritative-data poisoning** (a compromised *trusted* source is honored); **unmodeled tool side effects** (fields outside the contract / `Residual`, A5/A7 incomplete); **automatic AuthSpec Builder perfection** (a wrong `G_sys` is a faithfulness problem); soundness for arbitrary shell; protection against TCB/key compromise; anything about utility/over-blocking.
