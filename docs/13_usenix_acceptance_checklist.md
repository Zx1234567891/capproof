# 13. USENIX Acceptance Checklist

A reviewer-facing self-audit. Each row: the bar, where the package addresses it, and the residual risk that keeps it from a clean check until the work is *executed*.

## 13.1 Problem and motivation

| Bar | Where | Residual |
|---|---|---|
| Problem is real, sharp, non-incremental | §01 (Unverifiable Authorization, Authority Laundering) | Must show, empirically, that it is *distinct* from injection (Layer C vs. Layer B separation) |
| Distinct from prompt injection | §01.1, §08.1 | The distinction is argued; the *evidence* is the CaMeL-vs-CapProof laundering gap |
| Motivating examples are concrete | §01.5 (3 killer examples with proof-failure reasons) | Examples must appear as real benchmark tasks (they do: §07.3) |

## 13.2 Threat model and property

| Bar | Where | Residual |
|---|---|---|
| Threat model explicit, attacker/defender boundary clear | §02.1–02.3, full TCB table | — |
| LLM outside TCB; **AuthSpec Builder outside TCB** | §02.3, §03.3 | The faithfulness number must be reported (§08.5) |
| Security property formally stated | §02.4 (Authorization Integrity), §05 | — |
| Attack game well-defined, win condition crisp | §02.5 (relative to `G*`) | — |

## 13.3 Mechanism

| Bar | Where | Residual |
|---|---|---|
| Deterministic reference monitor is the boundary | §03.13 | LoC/TCB size to be reported |
| Capabilities opaque, scoped, expirable, revocable, **consumable** | §04.1 | — |
| Two-phase consumption; TOCTTOU/replay handled | §03.5, §03.14, §06.6 | Concurrency safety must be demonstrated (Layer A) |
| Memory cannot store authority by default | §03.9, rule MEMORY-STRIP | Must match the memory specialist (DRIFT-style) on Suite 2; do not overclaim vs PACT/AUTHGRAPH |
| Delegation attenuation-only | §03.10, Thm 3 | Requires agent PKI (§06.5) |
| Endorsement = one-shot, canonical-bound capability | §03.11, rule ENDORSE-ONCE | Confused-deputy mitigation (canonical challenge) to be user-validated if claimed |

## 13.4 Formalization

| Bar | Where | Residual |
|---|---|---|
| Inference rules | §05.3 (9 rules) | — |
| Soundness theorem **not vacuous** | §05.5 Thm 1 (parametric in AuthSpec-in-force) + **Characterization 1′** (residual sets, no probability) | residual must be measured as field sets on real tools (`TCB_AND_ADAPTER_COVERAGE.md`) |
| Non-amplification | §05.5 Thm 3 | — |
| Prefix soundness for replanning | §05.5 Thm 4 | — |
| Assumptions & non-guarantees explicit | every theorem + §05.7, §11 | — |

## 13.5 Evaluation

| Bar | Where | Residual |
|---|---|---|
| Mechanism suite (no LLM) | §08.2 | Build + run |
| Existing-benchmark eval (don't break) | §08.3 | **AgentDojo** confirmed; skill/MCP/dynamic/broad-injection benchmarks marked **planned external validation** (verified for version/license/task-count/scripts before use; closest substitute named if unavailable; never reported unless run) |
| New benchmark with **mechanism-agnostic** oracles | §07 | Build 150 tasks; held-out red team |
| **Strong** baselines incl. **CaMeL (tuned)** | §09.1–09.2 | Integrate CaMeL original/faithful (calibrated, not strawmanned); faithful reimpls calibrated on the source benchmark subset for PACT-style/AUTHGRAPH-style/CLAWGUARD-style/PFI-style; oracle-vs-auto for PACT/CapProof; never claim to beat a representative-only system |
| ≥10 ablations, ≥12 adaptive attacks | §09.3 (12 ablations incl. ProofObjectRemoved), §09.5 (17 adaptive incl. shell env/cwd/stdin + template-arg injection) | Run with held-out authorship |
| **Kill test** vs corrected comparators (run first) | `KILL_TEST_PLAN.md` | 12 cross-boundary tasks; go/no-go scenarios; pivot if failed |
| AuthSpec Faithfulness Gate; Canonicalization/Adapter Bypass Gate; Residual study | `AUTHSPEC_FAITHFULNESS_GATE.md`, `CANONICALIZATION_BYPASS_GATE.md`, `TCB_AND_ADAPTER_COVERAGE.md` | Over/under-broadening + grant precision/recall; ≥30 bypass vectors; residual sets + coverage metrics on real tools |
| Metrics defined; statistics (CI, McNemar, bootstrap, Holm) | §08.6–08.7 | — |
| Multi-model (≥3 backbones) | §08.7 | Compute budget |
| Artifact / reproducibility (Docker, traces, oracles) | §08.7 | Target AE badges |

## 13.6 Honesty / scope

| Bar | Where | Residual |
|---|---|---|
| Limitations stated up front | §11.1 (8 limitations) | — |
| Out-of-scope explicit | §01.7, §11.2 | — |
| No over-claims ("solve injection", "fully secure", unconditional "guaranteed") | enforced throughout; README | Keep this discipline in the draft |
| Related work accurate; novelty conservative | §12 (identities **corrected**; framing **softened** this revision) | PACT/PFI/CLAWGUARD/AUTHGRAPH/CaMeL/PCAA/**AgentArmor** cited by correct mechanism; AgentArmor restored as trace-analysis related work + auxiliary baseline; CLAWGUARD un-strawmanned (strong MCP/skill); "single-trajectory" claim replaced with consumable-authority claim; no arXiv IDs asserted in-text; **PCAA-proximity is the top positioning risk** (§12.4) |

## 13.7 The checks that are currently *open* (and gate acceptance)

1. **Kill test executed** showing cross-boundary separation vs **CaMeL, PACT-style, AUTHGRAPH-style, CLAWGUARD-style** (not just argued). — `KILL_TEST_PLAN.md`, §09.7.
2. **AuthSpec faithfulness measured** (over/under-broadening, grant precision/recall, endorsement recovery), under the ambiguity adversary, §3.11 ON/OFF. — `AUTHSPEC_FAITHFULNESS_GATE.md`, §08.5.
3. **Adapter residual measured** as field sets + the five coverage metrics on real MCP tools + coverage sweep. — `TCB_AND_ADAPTER_COVERAGE.md`, §08.5.
4. **`ProofObjectRemoved` resolved** — keep or drop "proof-carrying" based on the 6-axis result. — §09.4.

Until these are done, the honest disposition of the *work* is "promising plan, not yet a paper." The *plan* is structured to make all of them falsifiable, and the kill test is designed to fail fast if the thesis is wrong (`KILL_TEST_PLAN.md` §5).
