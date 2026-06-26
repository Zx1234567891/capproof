# REVIEWER_SIMULATION

Three simulated reviews of the **revised plan, assuming the experiments and the kill test are executed as described**. Each reviewer gives a **score**, **strengths**, **weaknesses**, **required rebuttal**, and **what experiment would change their mind**. Prior systems are named per their real mechanism (§12). Written adversarially on purpose.

---

## Reviewer A — Systems Security

**Score: Weak Accept (Accept reachable)** · **Confidence: High**

**Strengths.**
- Deterministic capability-consuming monitor with every LLM (incl. the AuthSpec Builder) outside the TCB; `reserve→commit→consume` with atomic CAS and idempotent consume is the right construction for replay/TOCTTOU.
- **Per-component TCB accounting** with LoC budgets (Core Verifier < 1,500; Minting+Verifier+Store < 5,000; adapters counted separately), failure modes, and a test per component (`TCB_AND_ADAPTER_COVERAGE.md`). False-allow = 0 as a hard mechanism-suite gate is the right bar.
- Coverage is honest: a **residual characterization** (named unobserved fields + five coverage metrics) replaces any probability bound. `run_shell` reduced to allowlisted templates with env/cwd/stdin contracts, and arbitrary-shell non-soundness stated.

**Weaknesses.**
- Agent PKI (delegation Theorem prerequisite) is sketched; key distribution/rotation needs a paragraph, and key compromise is correctly flagged as a total break.
- Automatic-provenance soundness is where reality bites; the oracle-vs-auto gap must be small or the result is "sound given an oracle."
- TOCTTOU/DNS-rebinding residuals for path/endpoint are acknowledged but the atomic resolve-and-act adapters must be demonstrated.

**Required rebuttal.** Report actual TCB LoC; show automatic-vs-oracle provenance gap; show the bypass gate passing on all decidable vectors.
**What would change my mind (toward Accept).** A measured small provenance gap + a clean concurrency/replay result (double-spend = 0 under load) + the residual sweep validating the characterization.

---

## Reviewer B — LLM Agent Security

**Score: Weak Accept** · **Confidence: High**

**Strengths.**
- The cross-boundary framing is sharp and *correctly positioned*: CaMeL (value data-flow), PACT (argument provenance), AUTHGRAPH (dual-graph detection), CLAWGUARD (tool boundary, strong on MCP/skill), PFI (trusted/untrusted agents), AgentArmor (trace-graph) can detect or block unsafe actions but do not center authority as a consumable resource; CapProof does, across memory/delegation/endorsement/metadata. The related-work deltas are accurate and the "not first to do capability/provenance/graph/boundary" disclaimer is exactly right.
- The kill test (`KILL_TEST_PLAN.md`) is the experiment I want *first*, with go/no-go tied to CaMeL behavior and a real pivot plan. The **delegation** channel (KE-4, ResearchAgent→EmailAgent) is the strongest lever, and PFI is the right comparator there.
- Treating the AuthSpec Builder as untrusted, separating Oracle/Deployed modes, and **measuring** over-broadening under an ambiguity adversary (`AUTHSPEC_FAITHFULNESS_GATE.md`) shows the elicitation layer is taken seriously.

**Weaknesses.**
- The kill test is everything. If DRIFT-style memory isolation, or AUTHGRAPH/PACT-auto extended across turns, already blocks memory laundering, or CaMeL blocks the cross-boundary cases at similar utility, the delta shrinks. The pivot plan is reassuring but the *result* must show a real gap.
- **MCP/skill**: CLAWGUARD is a strong defense here. The authors are right not to promise an ASR win — but then the MCP/skill contribution rests entirely on the usability/auditability story, which must be *quantified* (endorsement count, over-block, failure-localization), not asserted.
- Endorsement burden on dynamic tasks — measure the distribution and Endorsement Recovery Rate, or narrow the claim.
- "Beat Native ReAct" is uninteresting; the comparison that matters is CaMeL/PACT/AUTHGRAPH/CLAWGUARD.

**Required rebuttal.** A real, attributed gap (security on delegation/endorsement; usability/auditability on MCP/skill) per the three kill-test outcomes; parity (not regression) on the argument channel; benign endorsement distribution (or an honest scope narrowing).
**What would change my mind (toward Accept).** The kill test landing in a go scenario (security on memory/delegation/endorsement, or usability/auditability on MCP/skill) with mechanistic ablation flips.

---

## Reviewer C — Benchmark / Methodology Skeptic

**Score: Borderline (lean accept if oracles and baselines hold up)** · **Confidence: Medium-High**

**Strengths.**
- Mechanism-agnostic oracles (observable side effects only; `ground_truth_authspec` quarantined), held-out red team, a **threat sourcing table** with `threat_source` per task and equal channel weighting — directly addresses task-authorship bias.
- **Three-tier reproduction policy**: a faithful reimpl must be calibrated on the source paper's own benchmark or be labeled representative, and CapProof never claims to beat a representative-only system. The **oracle-vs-auto** axis (PACT and CapProof both) separates idea from implementation.
- Pre-registered falsification (§09.7) and a negative-result plan (§10.5) raise my trust.
- **Baseline scoping is defensible:** AgentArmor (trace-graph type-checking) is cited as related work and run as an auxiliary, subset baseline rather than a main one, with the reason stated (detector-vs-enforcer, calibration risk). I would have flagged it as missing; the authors pre-empted that.

**Weaknesses.**
- Even with sourcing, per-channel **difficulty** must be matched across baselines — report per-role, not just per-channel, so I can re-weight.
- Baseline faithfulness: PACT-style/AUTHGRAPH-style/CLAWGUARD-style reimplementations must be calibrated, or downgraded to representative and not attributed. Hold the line; do not claim to beat the named systems with uncalibrated reimplementations.
- Statistical multiplicity is large (defenses × suites × models × conditions × gates); declare the correction family up front.
- The "proof" framing: I appreciate `ProofObjectRemoved`, but the title should not bet on the proof until the data is in.

**Required rebuttal.** Matched per-role difficulty; demonstrated baseline calibration; pre-declared statistics family; `ProofObjectRemoved` either justifying or removing "proof" from the framing.
**What would change my mind (toward Accept).** Calibrated baselines reproducing their source numbers on a shared subset + a difficulty-matched per-role table + the faithfulness gate under the threshold with confirmation ON.

---

## Meta-review (synthesis)

**Consensus (assuming execution): Weak Accept, Accept reachable.**

- **Agreement:** the *accurately positioned* cross-boundary framing, the honesty (untrusted Builder, residual-set coverage, conceded argument-channel parity, PCAA-acknowledged proof demotion), and the per-component TCB accounting are credited by all three.
- **The hinge:** B's and C's accept hinge on the **kill test** (separation, especially on delegation where existing systems do not model authority transfer as a consumable, attenuable object) and **baseline/threat-sourcing discipline**. If a correctly-configured comparator matches CapProof on the cross-boundary channels, all three drop toward reject and the pivot applies.
- **Cheapest path to consensus Accept:** (1) kill-test separation (scenario 2 or 3); (2) calibrated baselines; (3) faithfulness/residual/provenance measurements; (4) resolve the proof framing via `ProofObjectRemoved`. None is conceptual; all are execution and discipline.

**Calibration.** A *plan* earns none of these scores; these are what a *paper* executing this plan could earn. Today the honest disposition is "Borderline-if-executed." The related-work corrections made across prior revisions remove a fatal-error risk (mischaracterizing real systems) rather than adding capability.
