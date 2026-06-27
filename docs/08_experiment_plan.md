# 08. Experiment Plan

## 8.0 Layer 0 — Kill test (run first; gates everything else)

Before the three layers below, run the **CaMeL head-to-head kill test** (`KILL_TEST_PLAN.md`): ~12 tasks across the cross-boundary channels against CaMeL (original/faithful, tuned), PACT-style, AUTHGRAPH-style, CLAWGUARD-style, and Native, in both Oracle- and Deployed-AuthSpec modes. Its pre-registered go/no-go decides whether to build the full benchmark; its result is **Figure 1**. If it fails, pivot per `KILL_TEST_PLAN.md` §5 instead of proceeding.

## 8.1 Three layers

```text
Layer 0 — Kill Test            (12 tasks; is there an irreplaceable delta? — gates the rest)
Layer A — Mechanism Suite      (no LLM; tests the TCB's logic)
Layer B — Existing Benchmarks  (does CapProof break / lose utility on standard injection?)
Layer C — AuthLaunderBench     (does CapProof close the laundering gap others miss?)
+ Gates  — Faithfulness Gate (`AUTHSPEC_FAITHFULNESS_GATE.md`), Canonicalization/Adapter Bypass Gate (`CANONICALIZATION_BYPASS_GATE.md`), Adapter-Coverage Residual Study (`TCB_AND_ADAPTER_COVERAGE.md`)
```

The narrative the experiments must support is **not** "lowest ASR everywhere." It is:

> Existing defenses lack an authorization chain, so they fail *structurally* on laundering channels; CapProof fails-closed on absent authorization. CapProof matches strong baselines on ordinary injection and on the exfiltration dimension (because it adopts CaMeL's data-flow capability), and is significantly stronger on memory/delegation/metadata/endorsement laundering — at a stated, measured cost in endorsement burden and latency.

## 8.2 Layer A — Mechanism Suite (system correctness, no LLM)

Purpose: verify the verifier, capability consumption, two-phase commit, and canonicalization in isolation — these results are LLM-independent and reproducible to the bit.

- **Scale:** 100 scenarios × {benign, attack} = 200 actions, spanning recipient(20)/file_path(20)/command(20)/endpoint(20)/{memory,delegation,endorsement}(20).
- **Metrics:** verifier correctness (false-allow / false-deny rate against hand-labeled ground truth), proof-synthesis success on solvable cases, failure-reason accuracy, capability-replay rejection rate, concurrency-safety (no double-spend under N concurrent reservers), latency p50/p95/p99 of the **pure verifier**.
- **Target:** false-allow = 0 on this suite (it is the soundness sanity check); concurrency double-spend = 0.

## 8.3 Layer B — Existing benchmarks

**Confirmed external benchmark:**

| Benchmark | What it tests | CapProof's expected role |
|---|---|---|
| **AgentDojo** (NeurIPS 2024) | standard indirect prompt injection, utility-under-attack | **don't break**: ASR comparable to best defense, utility within 10 pts of best baseline |

**Planned external validation** (these benchmarks are *candidates*; their existence, access, license, version, task count, and evaluation scripts are confirmed before use, and the closest available substitute is used and named if a candidate is unavailable — we never report a benchmark we did not run):

| Benchmark | Status | Intended Use | Required Verification Before Submission |
|---|---|---|---|
| **AgentDojo** | **Confirmed** (public, NeurIPS 2024) | indirect-injection / utility-under-attack; "don't break" check | none (in hand) — pin version & task subset |
| Dynamic-replanning benchmark (AgentDyn-class) | **Planned external validation** | dynamic tasks / replanning; endorsement-count stress | existence, access, license, task count, eval scripts; else substitute & name |
| Skill-injection benchmark (SkillInject-class) | **Planned external validation** | skill-file laundering coverage | name/version/license/availability; else build a documented subset |
| MCP-metadata benchmark (MCPTox / MCPSecurityBench-class) | **Planned external validation** | MCP-metadata laundering coverage | exact name/version/license/availability; else build a documented subset |
| Broad-injection benchmark (InjecAgent / ASB-class) | **Planned external validation, subject to availability and licensing** | breadth of indirect injection | availability/licensing; secondary breadth only, not load-bearing |

Baselines on Layer B include **CaMeL (original/faithful, tuned)**, **PACT-oracle/PACT-auto**, **AUTHGRAPH-style**, **CLAWGUARD-style**, **CapProof-oracle/CapProof-auto**, and **Native** as main baselines, plus **PFI-style**, **Task Shield-style**, **PromptArmor-style**, **DRIFT-style**, and an **AgentArmor-related subset** as auxiliary, under the three-tier reproduction policy of §09.1 (every baseline labeled Original / faithful reimpl calibrated on the source benchmark subset / representative). On AgentDojo specifically, we report CapProof and CaMeL side by side; we *expect* CaMeL, PACT, and AUTHGRAPH to be strong here and we do not need to beat them — we need to be comparable and then separate on Layer C.

## 8.4 Layer C — AuthLaunderBench

Full protocol in §07. Run all baselines + all CapProof ablations on all 6 suites × 3 variants. Primary comparison: CapProof vs. each baseline per suite, with the mechanism-agnostic oracles.

## 8.5 Cross-cutting measurements (the ones that make assumptions falsifiable)

These are not optional; they are what converts "trust our TCB" into evidence:

1. **AuthSpec faithfulness (Gate, `AUTHSPEC_FAITHFULNESS_GATE.md`).** Over a labeled corpus including deliberately ambiguous requests and the ambiguity-exploit adversary (§09 #15): **AuthSpec Over-Broadening Rate** `= Pr[AuthClosure(G_sys) ⊄ AuthClosure(G*)]` (the dangerous direction, headline; equivalently `1 −` the No-Over-Broadening containment rate `Pr[AuthClosure(G_sys) ⊆ AuthClosure(G*)]`) and **AuthSpec Under-Broadening Rate** (utility), with §3.11 confirmation ON vs OFF and ≥3 backbones. This is the answer to "is AuthSpec trusted?"
2. **Provenance sensitivity.** PACT and CapProof each in **-oracle** and **-auto** provenance (§09.2); report ASR/utility gap. Then inject controlled provenance errors at {1%,5%,10%} and plot ASR vs. error rate (the slope is fragility to A1).
3. **Adapter coverage on real tools (Residual Study, `TCB_AND_ADAPTER_COVERAGE.md`).** Per-tool **residual field sets** `Residual(t) = F(t)\O(t)` over the MCP corpus (bcc/headers/attachments/env/cwd/stdin/follow_redirects), reported as **sets with aggregate frequencies — not a coverage probability**. A controlled sweep (hide 1/2/3 fields) shows exposure equals exactly the hidden fields (validates Characterization 1′, §05.6).
4. **Endorsement burden.** Endorsements per task on static vs. dynamic tasks; distribution, not just mean.
5. **Denial-reason leakage.** Adaptive attack ASR under full vs. coarse denial reasons (§09.6) — does telling the attacker *why* help? Reported with deployment implications.
6. **Canonicalization/Adapter Bypass Gate (`CANONICALIZATION_BYPASS_GATE.md`).** Per-vector pass/fail for recipient/file/endpoint canonicalization and bcc/headers/attachments/env/cwd/stdin/redirect coverage; the empirical test of Theorem 1 premises A3 (canonicalizer correctness on decidable roles) and A4 (observability).

## 8.6 Metrics (defined)

| Metric | Definition |
|---|---|
| **ASR** | fraction of attack variants where a forbidden observable effect occurred (per security_oracle) |
| **Benign Success Rate** | fraction of benign variants where the task goal was met (per utility_oracle) |
| **Secure Utility Rate** | fraction of *attack* variants where the task goal was met **and** no forbidden effect occurred |
| **Over-blocking Rate** | fraction of benign variants where a legitimate action was denied (utility lost with no attack) |
| **Proof Coverage Rate** | fraction of *admitted* high-impact actions accompanied by a valid witness (CapProof-internal) |
| **Proof Synthesis Failure Rate** | fraction of *authorizable* actions for which the synthesizer failed to produce a valid witness (a utility bug, not a security one) |
| **Failure-Reason Distribution** | histogram of denial reasons over attack variants (the Sankey, §08.8) |
| **Endorsement Count** | endorsements requested per task |
| **Endorsement Recovery Rate** | fraction of legitimate ambiguous high-impact requests completed via a **single** endorsement (utility of the ask-path) |
| **Capability Replay Rejection Rate** | fraction of replay attempts denied |
| **AuthSpec Over-Broadening Rate** | fraction of requests where `AuthClosure(G_sys) ⊋ AuthClosure(G*)` (dangerous direction; `AUTHSPEC_FAITHFULNESS_GATE.md`) |
| **AuthSpec Under-Broadening Rate** | fraction where `AuthClosure(G_sys) ⊊ AuthClosure(G*)` (utility cost) |
| **High-Impact Grant Precision / Recall** | of high-impact bindings `G_sys` authorizes, fraction in `G*` (precision) / of those in `G*`, fraction `G_sys` authorizes (recall) |
| **Declared / Observable Authority Field Coverage** | `|D(t)|/|F(t)|` and `|O(t)|/|F(t)|` per tool (`TCB_AND_ADAPTER_COVERAGE.md`) |
| **Unmodeled Side-Effect Rate** | fraction of fuzzed perturbations changing an observable side effect via a `Residual(t)` field |
| **Contract Completeness** | fraction of corpus tools with `D(t)=F(t)` |
| **Canonicalization Coverage** | fraction of decidable-role canonicalization vectors normalized correctly (`CANONICALIZATION_BYPASS_GATE.md`) |
| **Verifier Latency** | p50/p95/p99 of pure `verify()` |
| **End-to-end Latency** | p50/p95/p99 of `guard()` including canonicalization + reserve |
| **Token Overhead** | extra tokens vs. Native ReAct (AuthSpec, witness, endorsement prompts) |
| **TCB Size** | LoC of Core Verifier (target <1,500) and Minting+Verifier+Store (target <5,000); adapters counted separately |
| **Annotation Burden** | per-tool contract authoring effort (fields declared / time) |

A note on **Proof Coverage ≥ 70%**: coverage is *not* a virtue by itself (a fail-closed system can have low coverage and high security). We report it to characterize *how often* the synthesizer succeeds on authorizable actions; the security claim rests on ASR/Secure-Utility, not on coverage. We will define the 70% target as "of actions that *should* be authorizable, ≥70% get a witness without human help" — i.e., an automation/utility target, not a safety target.

## 8.7 Statistics and reproducibility

- **Determinism:** temperature = 0 for all agents; fixed seeds; pinned model versions.
- **Repetition:** 3 runs per task variant (even at T=0, tool/order nondeterminism exists); report mean and spread.
- **Confidence intervals:** Wilson score intervals for all rates.
- **Significance:** **McNemar's test** for paired per-task ASR comparisons (same tasks, two defenses); **paired bootstrap** for Secure-Utility deltas; **Holm–Bonferroni** correction across the family of (defense × suite) comparisons. No uncorrected p-values in the paper.
- **Models:** at least **3 agent backbones** spanning a strong and a weaker model (defense behavior depends on the proposer's quality); report per-model.
- **Artifact:** Docker image; mock tools (email/HTTP/shell sandbox, §06.7); published traces; published proof DAGs; published benchmark + mechanism-agnostic oracles; scripts to regenerate every table/figure. Target a USENIX Artifact-Evaluation "Available + Functional + Reproduced" badge.

## 8.8 Result presentation

- Main table: per-suite ASR / Benign / Secure-Utility for all defenses, with CIs and significance markers.
- Failure-reason Sankey for CapProof (Attack → NoCap / SourceMismatch / MemoryAuthorityUse / DelegationMissing / EndorsementScopeError / CanonicalizationMismatch / AdapterCoverageGap). This shows *mechanism*, not just outcome.
- CaMeL-vs-CapProof scatter: AgentDojo (where we expect parity/CaMeL-favor) vs. AuthLaunderBench laundering suites (where we expect separation). One figure that makes the complementarity argument visually.
- Sensitivity plots: ASR vs. provenance-error rate; residual exposure vs. hidden fields; faithfulness under ambiguity attack.
