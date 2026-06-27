# TCB_AND_ADAPTER_COVERAGE

Two things a PC will probe: **how large and how testable is the trusted base**, and **what does the system fail to observe**. This document gives a per-component TCB accounting (trusted status, LoC target, failure mode, mitigation, test strategy) and replaces any probabilistic coverage "bound" with a **coverage-dependent residual characterization** plus concrete coverage metrics.

## Part A — Trusted Computing Base

Every LLM, including the AuthSpec Builder, is **outside** the TCB. The TCB is the set of deterministic components whose compromise breaks Authorization Integrity. A small, deterministic, tested monitor is part of the soundness argument.

> **The Proof Synthesizer is NOT in the security TCB.** Whatever builds the proof DAG (LLM or heuristic) is untrusted: the **Reference Monitor independently re-verifies** every step, so a malicious or buggy synthesizer can at worst produce a proof the monitor **rejects** (a liveness/utility issue), never one that wrongly admits an action. This is also why `ProofObjectRemoved` (§09.4) is coherent — if the monitor re-derives anyway, the carried proof is an optional artifact, not a trusted input. Likewise the **AuthSpec Builder** is outside the *mechanism-soundness* TCB (Theorems hold for any `G_force`), but it **does** affect *deployed faithfulness* (the `G_sys`-vs-`G*` gap), which is measured, not trusted. **Tool implementation honesty relative to declared schema (A7) is an assumption; tool-adapter completeness is a key experimental object**, not an assumption — it is measured as residual sets (Part B).

| Component | Trusted? / role | LoC target | Failure mode | Mitigation | Test strategy |
|---|---|---|---|---|---|
| **Reference Monitor (Core Verifier)** | Yes — the decision boundary; implements the inference rules + observability gate; deterministic ALLOW/DENY/ASK | **< 1,500** | False ALLOW (admits out-of-closure action) → integrity broken | Keep deterministic; no LLM in the path; minimal surface | **Mechanism suite: false-allow must = 0**; per-rule property tests; differential test vs a reference spec; 100% branch coverage on the decision path |
| **Capability Minting Service** | Yes — mints caps only via USER/POLICY/ENDORSE/DELEGATE; signs handles | (in <5k bundle) | Mints unauthorized cap / accepts untrusted mint → laundering | `NO-MINT-UNTRUSTED` enforced; root required per mint | Negative tests that untrusted sources cannot mint; MAC tests; every mint path requires a valid root |
| **Capability Store** | Yes — holds caps; atomic reserve/commit/consume/release; linearity | (in <5k bundle) | Double-spend / lost consumption → replay or DoS | Atomic CAS; idempotent consume; lease expiry | Concurrency property tests (no double-spend under N concurrent verifies); crash-recovery; fuzz the CAS path |
| **Receipt Store** | Yes — append-only signed receipts for transforms/actions | ~400 | Forgeable/mutable receipts → fake `DERIVE-CONTENT` | Append-only; signatures | Append-only invariant; signature verification; tamper tests |
| **Provenance Runtime** | Yes (assumption A1) — assigns/propagates source labels to values | ~1,000–1,500 | Mislabels untrusted as trusted → laundering | Conservative labeling; fail-closed on unknown | Oracle-vs-auto gap; error-injection {1,5,10}% ASR curve; taint-propagation unit tests |
| **Tool Adapters** | Yes — surface authority-bearing fields; map calls to roles | **counted separately**, ~300/tool | Drops a field (`Residual`) → unobserved effect | Observe-don't-just-declare; fail-closed on observable-but-undeclared | Adapter fuzzing to estimate `F(t)`; per-field bypass tests (bcc/headers/attachments/env/cwd/stdin/follow_redirects) |
| **Canonicalizer** | Yes — per-role normalization with `total` flags (decidable roles only) | ~900 (counted with adapters) | Misnormalization → predicate matches wrong value | Per-role modules; `command` declared non-total | Per-vector tests (`CANONICALIZATION_BYPASS_GATE.md`); recipient full; file/endpoint modulo TOCTTOU/rebinding |
| **Tool Contract Registry** | Yes — source of truth for tool schemas/roles/data-classes | ~600 | Wrong role/data-class mapping → wrong predicate | Review gate to add tools; registry-vs-adapter consistency | Schema-validation; registry-adapter consistency check |
| **Keys** (minting / receipt-signing / agent identity) | Yes — roots of unforgeability (A2) and delegation authenticity | n/a (config) | Key leak → forge caps/receipts/delegations | KMS / isolated signer; rotation; **no key in logs** | Key isolation; rotation tests; **key compromise = total break, stated** |

**LoC budgets (reported as actual metrics in results).** **Core Verifier < 1,500 LoC**; **Minting Service + Verifier + Capability Store < 5,000 LoC** together; **adapters counted separately** (they scale with the number of tools and are the least trusted of the trusted set). The argument is "the trusted part is small, deterministic, and tested to these specific failure modes; everything stochastic is outside it."

**TCB test-strategy summary.** Mechanism suite (false-allow = 0, hard gate); concurrency/crash suite for the store; coverage/residual study + bypass gate for adapters/canonicalizer; provenance sensitivity for the provenance runtime; crypto/forgery tests for minting/receipts/keys. Each row maps to a concrete suite; no trusted component lacks a test.

## Part B — Adapter Coverage as a Residual Characterization (no probability bound)

### Definitions (set-based)
For a tool `t`: `F(t)` = true authority-bearing fields; `D(t)` = contract-declared fields; `O(t)` = monitor-observable fields (`D(t) ⊆ O(t) ⊆ F(t)`); `Residual(t) = F(t) \ O(t)` = unobserved authority-bearing fields. For a task with tools `T`: `Res(T) = ⋃ Residual(t)`.

### Guarantee surface (a set-membership statement; full vs partial coverage)
- **Full adapter coverage** (`D(t)=O(t)=F(t)` for every tool in the task): soundness (Theorem 1) holds over **all declared and observable authority-bearing fields** — there is no residual, so every authority-bearing effect is bound or denied.
- **Partial coverage** (`Residual(t) ≠ ∅`): CapProof is sound **only over the authority-bearing fields exposed by the tool contracts and receipts** (`O(t)`). For effects expressible only through `Res(T)`, **no guarantee** is claimed; we *name* the exposed fields rather than claim completeness.
- Observable-but-undeclared fields (`O(t)\D(t)`): denied **fail-closed**.
- The residual risk under partial coverage is **characterized empirically**, not bounded analytically, by the five metrics below (Declared/Observable Authority Field Coverage, Unmodeled Side-Effect Rate, Contract Completeness, Canonicalization Coverage).

### Why no probability bound
A statement like `Pr[win] ≤ Σ_t (1−coverage(t))` is not sound: there is no defined probability space over an adaptive adversary, the sum can exceed 1, and a field-count ratio is not a probability of compromise. We make a precise, falsifiable claim instead: *name the unobserved fields, and you have named the exposure.*

### Coverage metrics (reported, not bounded)
- **Declared Authority Field Coverage** = `|D(t)| / |F(t)|` per tool (how much of the true authority surface the contract names).
- **Observable Authority Field Coverage** = `|O(t)| / |F(t)|` per tool (how much the adapter actually surfaces to the monitor).
- **Unmodeled Side-Effect Rate** = fraction of fuzzed perturbations that change an observable side effect but correspond to a field in `Residual(t)` (the empirical exposure).
- **Contract Completeness** = fraction of tools in the corpus whose `D(t)=F(t)` (fully declared).
- **Canonicalization Coverage** = fraction of decidable-role canonicalization vectors (`CANONICALIZATION_BYPASS_GATE.md`) the canonicalizer normalizes correctly.

These are **sets and fractions over a labeled corpus**, never a coverage→leakage probability.

### Measurement protocol
1. Corpus of real MCP servers / common tool wrappers (record versions).
2. Estimate `F(t)` by (a) reading schema/docs, (b) **adapter fuzzing** — perturb each candidate field (inject bcc, redirect, env var, symlinked path, stdin) and observe whether a side effect changes; a field that changes a side effect but is not surfaced is in `Residual`.
3. Report `Residual(t)` as a **set per tool** + aggregate frequency of each residual field + the five coverage metrics above.
4. **Controlled coverage sweep**: deliberately move 1/2/3 fields from `O` to `Residual` and show the only newly-admitted unsafe effects are exactly those expressible through the hidden fields — validating the residual characterization with no appeal to probability.

### Known residual fields (hypotheses to verify)
| Tool family | Commonly observed | Commonly residual | Effect if residual |
|---|---|---|---|
| email/send | to, subject, body | **bcc, reply_to, headers, attachments** | silent recipient, header routing, raw-file egress (KE-8) |
| file write | path, content | mode/flags, symlink target, `..` traversal | write outside scope |
| http/fetch | url, method | **follow_redirects, redirect target, headers, body** | endpoint laundering via redirect (KE-9) |
| shell | command | **cwd, env, stdin**, PATH inheritance | env/cwd/stdin side channel (KE-10) |

A recurring presence of bcc/headers/env/follow_redirects/cwd/stdin in `Residual` is itself a reportable finding: *real agent tool adapters systematically under-declare these authority-bearing fields.*

### Honest limits
For effects through truly unobservable fields, CapProof offers **no guarantee** and reports the residual rather than claim completeness. This is the boundary the Reviewer-A persona probes, and the reason the adapter row in Part A has its own bypass-gate test strategy.
