# 11. Limitations, Ethics, and TCB

## 11.1 Limitations (stated up front, before a reviewer finds them)

1. **Enforcement is sound only relative to the AuthSpec in force.** In Deployed-AuthSpec Mode the guarantee is relative to `G_sys`, not true intent `G*`; the gap is measured as AuthSpec faithfulness (§05.7, `AUTHSPEC_FAITHFULNESS_GATE.md`), not eliminated. Over-broadening under ambiguity is the residual risk.
2. **Coverage is incomplete; exposure is a set, not zero.** Effects expressible only through unobserved authority-bearing fields (`Residual(t)`) get no guarantee (Characterization 1′, §05.6). We measure the residual on real tools (`TCB_AND_ADAPTER_COVERAGE.md`) rather than claim completeness.
3. **Data exfiltration through an authorized channel is only partly addressed.** We adopt CaMeL-style data-flow capabilities for G4, but the content of an authorized document sent to an authorized recipient is out of scope (§01.7).
4. **`command` is not canonicalizable; `run_shell` is allowlisted-templates-only.** We do not claim Authorization Integrity for arbitrary shell (§06.4, `CANONICALIZATION_BYPASS_GATE.md`). Semantic command equivalence is undecidable.
5. **Provenance fidelity is assumed (A1) and only as good as the tracker.** Automatic-provenance results may trail oracle-provenance results; we report the gap and an error-injection sensitivity curve (§08.5).
6. **Delegation soundness assumes an agent PKI** (A-PKI, §06.5). A compromised delegating agent can pass on a *subset* it holds to a colluder — contained, not prevented (Thm 3 non-guarantee).
7. **Endorsement adds user-interaction cost.** On dynamic tasks the endorsement count may be high; if so the contribution narrows to high-impact/static-authority settings (§10.5). Measured as a distribution, not a mean.
8. **The proof object may not earn its place.** If `ProofObjectRemoved` (§09.4) shows no security/latency/audit/replan/localization benefit, we drop the proof-carrying framing and cite PCAA for the certificate layer (§12.1).

## 11.2 Out of scope (restated)

Model/prompt jailbreaks that do not touch an authority-bearing argument; content truthfulness / same-source poisoning; availability/DoS; side channels; physical/host compromise of the TCB; exfiltration via authorized channel+recipient+data-class (beyond the adopted data-flow capability).

## 11.3 Trusted Computing Base — component accounting

Every LLM, including the AuthSpec Builder, is **outside** the TCB. The TCB is the set of deterministic components whose compromise breaks Authorization Integrity. For each: trust boundary, **LoC target** (kept small on purpose — a small monitor is part of the soundness argument), failure mode, and test strategy. LoC targets are budgets for the prototype, reported as an actual metric in results (§08.6).

| Component | Trust boundary / responsibility | LoC target | Failure mode if buggy | Test strategy |
|---|---|---|---|---|
| **Reference monitor (verifier)** | The decision boundary; implements §05.3 rules + §03.13 gate; deterministic ALLOW/DENY/ASK | **≤ ~1.5k** core | False ALLOW (admits out-of-closure action) → Authorization Integrity broken | Layer-A correctness suite (false-allow must be **0**); property tests on every rule; differential test vs a reference Python spec of §05.3; 100% branch coverage target on the decision path |
| **Capability store** | Holds caps; atomic `reserve`/`commit`/`consume`/`release`; linearity | **≤ ~800** | Double-spend / lost consumption → replay or denial-of-service | Concurrency property tests (no double-spend under N concurrent verifies; idempotent consume); crash-recovery tests (reserved-but-not-committed leases expire); fuzz the CAS path |
| **Minting service** | Mints caps only via USER/POLICY/ENDORSE/DELEGATE rules; signs handles | **≤ ~500** | Mints unauthorized cap / accepts untrusted mint request → laundering | Unit tests that every mint path requires a valid root; negative tests that `untrusted` sources cannot mint (`NO-MINT-UNTRUSTED`); MAC verification tests |
| **Receipt store** | Append-only signed receipts for transforms/actions; replay evidence | **≤ ~400** | Forgeable/mutable receipts → `DERIVE-CONTENT` accepts fake derivations | Append-only invariant tests; signature-verification tests; tamper tests (mutated receipt must fail `verify`) |
| **Provenance runtime** | Assigns/propagates source labels to values; A1 | **≤ ~1.2k** | Mislabels untrusted as trusted → laundering (A1 violated) | Oracle-vs-auto gap measurement (§08.5); error-injection at {1,5,10}% with ASR curve; taint-propagation unit tests on transforms |
| **Tool adapters + contract registry** | Surface authority-bearing fields `O(t)`; declare `D(t)`; map tool calls to roles | **≤ ~300/tool** + ~600 registry | Drops a field (`Residual`) → unobserved effect (no guarantee) | Adapter fuzzing to estimate `F(t)` and report `Residual(t)` (`TCB_AND_ADAPTER_COVERAGE.md`); `CANONICALIZATION_BYPASS_GATE.md` bypass gate per field (bcc/headers/attachments/env/cwd/stdin/follow_redirects); fail-closed test on observable-but-undeclared fields |
| **Canonicalizer** | Per-role normalization with `total` flags; decidable roles only | **≤ ~900** | Misnormalization → predicate matches wrong value (alias/punycode/symlink/redirect bypass) | `CANONICALIZATION_BYPASS_GATE.md` per-vector canonicalization tests (recipient full; file/endpoint modulo TOCTTOU/rebinding); `command` declared non-total and routed to template membership |
| **Contract registry** *(if separated from adapters)* | Source of truth for tool schemas/roles/data-classes | (in adapter row) | Wrong role/data-class mapping → wrong predicate applied | Schema-validation tests; registry-vs-adapter consistency check; review gate for adding tools |
| **Keys** (minting key, receipt-signing key, agent-identity keys) | Roots of unforgeability (A2) and delegation authenticity | n/a (config) | Key leak → forge caps/receipts/delegations | Key isolation (separate signing service / KMS); rotation tests; **threat: key compromise = total break**, stated explicitly; no key material in logs |

**Aggregate TCB target: ≈ 6–7k LoC** of deterministic, testable code, reported as an actual figure. The argument is not "trust us" but "the trusted part is small, deterministic, and tested to these specific failure modes; everything stochastic is outside it."

### TCB test-strategy summary (what we run)
- **Layer-A correctness suite** (no LLM): adversarial inputs to the monitor; **false-allow = 0** is a hard gate.
- **Concurrency/crash suite** for the store (double-spend, lease expiry, idempotent consume).
- **Coverage/residual study** for adapters (`TCB_AND_ADAPTER_COVERAGE.md`) and the **bypass gate** for canonicalizer+adapters (`CANONICALIZATION_BYPASS_GATE.md`).
- **Provenance sensitivity** for the provenance runtime (§08.5).
- **Crypto/forgery tests** for minting/receipts/keys.
Each TCB row maps to a concrete suite; a reviewer can check that no trusted component lacks a test.

## 11.4 Ethics

- **Evaluation safety.** All attacks run against **mock or sandboxed tools** (no real email egress, no real shell side effects outside a container, no real network POST). Secret-egress oracles use planted canary values.
- **Dual use.** AuthLaunderBench contains attack patterns; we release it for defense evaluation under terms consistent with AgentDojo, with no live exploit payloads against real services.
- **Responsible disclosure.** Residual coverage gaps found in real MCP servers/adapters (`TCB_AND_ADAPTER_COVERAGE.md`) are disclosed to the relevant maintainers before publication where applicable.
- **Human-subjects.** If the faithfulness/endorsement studies use human annotators or participants, obtain IRB review; report annotator agreement; no deception beyond standard injected-context tasks.
- **Honesty.** We pre-register falsification conditions (§09.7, `KILL_TEST_PLAN.md` §4) and report negative results (§10.5), including dropping the proof-carrying framing if the data says so.
