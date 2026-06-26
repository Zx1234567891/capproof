# CHANGELOG

## v7 (this revision) — typo, history, and metric-naming fixes

| # | Issue | v7 fix |
|---|---|---|
| 1 | README typo "no raw-ASR-rout promise" | Reworded: "no promise of outperforming CLAWGUARD-style on raw ASR in the MCP/skill suites" |
| 2 | CHANGELOG v3-history row read as "AgentArmor … All removed" | Rewritten current-state-oriented: **ARGUS/Progent/StruQ removed**; historical note states v3's dropping of AgentArmor was itself an error, **restored in v4** as real trace-analysis related work + auxiliary/optional baseline, where it remains |
| 3 | **Metric naming error:** `Faithfulness_over = Pr[AuthClosure(G_sys) ⊆ AuthClosure(G*)]` labeled "the dangerous direction" (it is the *safe containment*) | Renamed in §05/§08: **No-Over-Broadening Rate** `= Pr[⊆]` (safe containment) vs **AuthSpec Over-Broadening Rate** `= Pr[⊄] = 1 − No-Over-Broadening Rate` (the risk headline); `Faithfulness_over/under` labels retired; definitions now match `AUTHSPEC_FAITHFULNESS_GATE.md` |
| 4 | "bounds the rest by measurement" (bypass gate intro) implied a strict bound | → "empirically characterizes the residual risk by measurement"; stale assumption labels in the same sentence updated to A5/A6 |
| 5 | Re-verified (no change needed): G*/G_sys/G_force usage incl. the Oracle-game preamble in §02; MCP/skill success bars; no `[VERIFY]`/TBD notes; related-work accuracy incl. AgentArmor; `run_shell` template-only; tool-contract field completeness; kill-test-first ordering; no over-strong/strawman claims | — |

---

## v6 (this revision) — final consistency & small-fix pass

v6 changes **no design**; it removes the residual inconsistencies a reviewer would notice:

| # | Issue | v6 fix |
|---|---|---|
| 1 | Version-history sentences could read as "AgentArmor was removed / related work is confused" | Unified to **current version**; every current-state sentence states **AgentArmor is a real system, retained** as trace-analysis related work + auxiliary/optional baseline. Only ARGUS/Progent/StruQ are described as removed erroneous comparators (README, ACCEPTANCE_GAP, TOP_10, CHANGELOG history rows) |
| 2 | `G*`/`G_sys` mode could be misread in the attack game | Added to §2.5: *this is the Oracle-AuthSpec enforcement game (`G_force=G*`); deployed experiments replace `G*` with `G_sys` and separately measure faithfulness; no capability is ever minted from `G*` in a deployed system* |
| 3 | MCP/skill success bars | Re-verified everywhere: **Memory/Delegation/Endorsement** → significantly reduce ASR / unauthorized persistence / replay-risk / delegation amplification; **MCP/Skill** → at least competitive ASR with CLAWGUARD-style **+** proof/auditability / replay-prevention / endorsement-scoping / failure-localization / audit-replay; **no raw-ASR-rout promise** (§00, §10, README, §13) |
| 4 | Benchmark internal notes | Added a **Benchmark / Status / Intended Use / Required Verification Before Submission** table; AgentDojo confirmed, the rest **planned external validation / subject to availability and licensing** (§08.3) |
| 5 | "bounded by coverage" phrasing in §02 | Changed to **characterized by coverage (not bounded)**; full vs partial coverage soundness stated (`TCB_AND_ADAPTER_COVERAGE.md`, §05) |
| 6 | Tool Contract Registry | Added memory **persistence_flag**; memory now covers content/authority_claims/provenance/persistence_flag; delegation covers parent/child/scope/TTL/redelegation; file covers path/mode/overwrite/symlink_policy; send_email and HTTP complete (§06) |
| 7 | Threat sourcing lacked observable conditions | Added per-suite **Observable attack-success condition** + **Expected safe behavior** table (§07.6.1) |
| 8 | PFI-style status vague | Clarified: real adjacent work; **auxiliary in MVP due to architectural mismatch; promoted to main on Delegation/data-injection suites if resources allow, else evaluated on a subset** (§09) |
| 9 | TCB component statuses | Added explicit: **Proof Synthesizer is NOT in the security TCB** (monitor re-verifies; malicious synthesizer ⇒ rejected proof, never a wrong admit); AuthSpec Builder outside *mechanism-soundness* TCB but affects deployed faithfulness; tool honesty (A7) is an assumption; adapter completeness is a measured experimental object (`TCB_AND_ADAPTER_COVERAGE.md`) |
| 10 | Rebuttal | Added **Q18 "Why not start with AuthLaunderBench instead of the kill test?"** (now 18 questions) |
| 11 | Bypass gate isolated to one file | Cross-referenced: the ≥34 vectors also run in the **adaptive-attack matrix** (§09.5), the **WeakCanonicalization ablation** (§09.3), and the **adapter-coverage sweep**; the contract-field column is the join key |
| 12 | Killer-example baseline hedge | Standardized: a baseline **may block, over-block, require approval, lack proof/audit/replay semantics, or not directly model persistent/transferred authority depending on configuration** — hypotheses, not verdicts (KILLER_EXAMPLES) |

**Net effect:** consistent versioning with no "AgentArmor removed" confusion, unambiguous Oracle-vs-Deployed AuthSpec language, no MCP/skill over-claim, honest benchmark status, a complete tool-contract registry, explicit TCB statuses, and a bypass gate wired into the adaptive/ablation matrix — with the capability-consuming-authorization main line untouched.

---

## v5 (this revision) — final consistency pass

v5 keeps the v4 main line and fixes the residual small issues a reviewer would catch:

| # | Issue | v5 fix |
|---|---|---|
| 1 | Success bars still implied an MCP/skill ASR win over CLAWGUARD | Unified everywhere: **Memory/Delegation/Endorsement** → significantly reduce ASR / replay-risk / unauthorized persistence; **MCP/Skill** → at least **competitive** on ASR + show proof/auditability / capability-replay-prevention / one-shot-endorsement-scoping / failure-localization / audit-replay advantage (§00 bar, §10 bar 1, README, §13) |
| 2 | Benchmark internal notes ("verify availability / exact names / to be confirmed") | Removed. **AgentDojo confirmed**; dynamic/skill/MCP/broad-injection benchmarks marked **planned external validation** (verified before use; substitute named; never reported unless run) (§08.3, §13) |
| 3 | Theorem assumptions missing tool-honesty | Added **A7 tool implementation honesty relative to declared schema**; each theorem's non-guarantees now list **content truthfulness, same-source authoritative-data poisoning, unmodeled tool side effects, AuthSpec-Builder imperfection** (§05) |
| 4 | Tool Contract Registry incomplete | Added **memory (content/authority_claims/provenance)** and **delegation (parent_agent/child_agent/delegated_scope/TTL/redelegation)** contracts; `write_file` extended with **overwrite/symlink_policy**; HTTP and `send_email` already complete (§06) |
| 5 | Bypass gate lacked field attribution | Added a **Contract/adapter field** column to all ≥30 attacks + memory/delegation rows — every deny reason maps to a declared field (the audit hook) (`CANONICALIZATION_BYPASS_GATE.md`) |
| 6 | Rebuttal missing "optional proof" question | Added **Q17 "Why not make the proof object optional?"** (design separates proof from identity; `ProofObjectRemoved` decides) (§14) |
| 7 | Adapter coverage full-vs-partial not explicit | Stated: **full coverage** → sound over all declared+observable fields; **partial** → sound only over contract/receipt-exposed fields; residual characterized empirically by the five coverage metrics (`TCB_AND_ADAPTER_COVERAGE.md`) |

**Net effect:** no MCP/skill over-claim, no unverified benchmark presented as confirmed, a complete assumption set with honest non-guarantees, a complete tool-contract registry, and a fully field-attributed bypass gate — while keeping capability-consuming authorization as the identity.

---

## v4 (this revision) — AgentArmor restored, conservative framing, CLAWGUARD un-strawmanned, assumptions named

v4 keeps the v3 main line (capability-consuming authorization) and every v3/v2 mechanism, and fixes the positioning/accuracy issues that remained:

| # | Issue in v3 | v4 fix |
|---|---|---|
| 1 | **AgentArmor needed to be present as real related work** | **Present and retained.** AgentArmor abstracts the runtime trace into CFG/DFG/PDG with a graph annotator/inspector; §12 row + identity. Delta: AgentArmor infers dependencies from the trace and checks security types (detection); CapProof requires pre-execution capability consumption + authorization-chain verification, focused on memory/delegation/endorsement laundering. Placed as **trace-analysis related work + auxiliary/optional baseline** (§09); rebuttal Q16 explains why it is auxiliary, not a main baseline |
| 2 | **"single-trajectory defenses" framing** (inaccurate: DRIFT has memory isolation, CLAWGUARD covers MCP/skill, PFI models agent flow) | **Replaced everywhere** with the conservative claim: *existing defenses can often detect or block unsafe actions, but do not primarily model authority itself as a consumable resource with explicit lifetime, scope, delegation attenuation, endorsement semantics, persistence restrictions, and spend state across memory/delegation/endorsement boundaries* (README, §00, §07, §09, §12, §13, §14, REVIEWER_SIMULATION, ACCEPTANCE_GAP) |
| 3 | **CLAWGUARD risked being strawmanned** | **Tightened.** CLAWGUARD stated as a **strong MCP/skill defense**; CapProof does **not** promise to out-ASR it on MCP/skill — the distinct win is proof semantics, one-shot endorsement, capability-replay prevention, delegation/endorsement scoping, failure localization, audit/replay (§12, §14 Q5, KILLER_EXAMPLES KE-5/KE-6, §10 bar 1, KILL_TEST_PLAN) |
| 4 | Residual wrong-name/arXiv risk | Re-scrubbed: no `[VERIFY]`, no ARGUS-for-PACT, no Progent-for-PFI, no CLAWGUARD-unconfirmed, no arXiv IDs asserted in-text; PACT/AUTHGRAPH/CaMeL/PFI/CLAWGUARD/PCAA/AgentArmor each described by correct mechanism; **no prior contribution claimed as ours** |
| 5 | Theorem assumptions implicit | **Named explicitly: A1 provenance fidelity, A2 capability-store unforgeability, A3 minting-service correctness, A4 monitor correctness, A5 tool-adapter observability, A6 canonical-action binding**; each theorem followed by "what it does not guarantee"; collected non-guarantees added (§05) |
| 6 | Kill test read like a normal experiment | **Reframed as the go/no-go lifeline** with three acceptable outcomes (security gap / usability gap / proof-auditability gap) and an explicit No-Go + pivot; CLAWGUARD-strong-on-MCP/skill handled (KILL_TEST_PLAN) |
| 7 | Killer-example baseline claims too strong | Each example now describes what each system *primarily models* and why a laundering class is *not its central object* — **not** "definitely misses"; AgentArmor added to every example; DRIFT/PFI/CLAWGUARD credited where strong (KILLER_EXAMPLES) |
| 8 | Baselines flat | **Main vs auxiliary split**: main = CaMeL, PACT-oracle/auto, AUTHGRAPH-style, CLAWGUARD-style, Native, CapProof-oracle/auto; auxiliary = DRIFT-style, PFI-style, AgentArmor-related subset, Task Shield, PromptArmor (§09) |
| 9 | ProofObjectRemoved risk understated | Strengthened: if removing the proof DAG keeps security and lowers/keeps latency, **the proof object is not the identity** — main line stays capability-consuming authorization; proof value confined to auditability/replayability/failure-localization/decoupled-construction (§09.4) |

**Net effect:** the package no longer denies a real adjacent system (AgentArmor), no longer overclaims a "single-trajectory" weakness that several baselines do not have, and no longer risks strawmanning CLAWGUARD on MCP/skill — while keeping the capability-consuming-authorization main line and all rigor fixes.

---

## v3 (this revision) — CORRECTION of related-work / baseline factual errors

v3 is a **targeted correction**, not a redesign. It keeps every v2 improvement (formal `G*`/`G_sys` separation, Oracle/Deployed modes, residual characterization, `run_shell` templates, kill test, ProofObjectRemoved, faithfulness gate, bypass gate, TCB tightening, memory strip, delegation cert, one-shot endorsement) and **fixes the related-work errors v2 introduced**:

| Area | v2 (WRONG) | v3 (corrected) |
|---|---|---|
| **PACT** | v2 claimed "PACT" was unverifiable and **substituted ARGUS** | **Restored.** PACT = *The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck* — argument-level provenance; roles target/command/credential/content/selector/control. ARGUS removed everywhere |
| **PFI** | v2 **mapped PFI → Progent** | **Corrected.** PFI = *Prompt Flow Integrity to Prevent Privilege Escalation in LLM Agents* — trusted/untrusted agent, Data ID, DataGuard, CtrlGuard. Progent removed |
| **CLAWGUARD** | v2 flagged it unconfirmed / another system | **Confirmed.** CLAWGUARD = *A Runtime Security Framework for Tool-Augmented LLM Agents Against Indirect Prompt Injection* — deterministic tool-call boundary; covers content injection, MCP poisoning, skill injection |
| **AUTHGRAPH / CaMeL / PCAA** | mostly right | Stated precisely: AUTHGRAPH = clean Authorization Graph + Injected Reasoning Graph (tool + parameter-source); CaMeL = P-LLM/Q-LLM + capability metadata + data-flow graph + custom interpreter + policies; PCAA = proof-carrying actions / certificate / receipts / proof bundle |
| **Erroneous comparators** | ARGUS, Progent, StruQ used as comparators (and AgentArmor temporarily dropped) | **ARGUS/Progent/StruQ removed** as not matching any real adjacent system. *(Historical note: v3 also dropped AgentArmor; this was itself an error — AgentArmor is a real trace-analysis system and was **restored in v4** as related work + auxiliary/optional baseline, where it remains.)* |
| **arXiv IDs** | v2 asserted specific (mis-mapped) IDs in-text | **Stripped.** Cite by title/system name; IDs filled from `prior_work.bib` at submission |
| **Core delta table** | absent | **Added** (§12.3): `Prior Work | What It Solves | What It Does Not Solve | CapProof Delta`; delta = consume-rooted-capability-before-execution vs cross-boundary laundering, **not** "first to do capability/provenance/graph/boundary" |
| **Baselines** | PACT-oracle/auto used "ARGUS"; AUTHGRAPH/CLAWGUARD configs vague | PACT-oracle/auto restored; AUTHGRAPH-style = clean graph + tool + parameter-source alignment, **no** consumption/memory/delegation; CLAWGUARD-style = boundary + approval, **approval not a one-shot capability**; PFI-style added; CaMeL taken seriously (§09.2) |
| **Files renamed** | numbered 15–18 | `KILL_TEST_PLAN.md`, `TCB_AND_ADAPTER_COVERAGE.md`, `AUTHSPEC_FAITHFULNESS_GATE.md`, `CANONICALIZATION_BYPASS_GATE.md` |
| **Metrics** | faithfulness over/under only | Added High-Impact Grant Precision/Recall, Endorsement Recovery Rate, and coverage metrics (Declared/Observable Authority Field Coverage, Unmodeled Side-Effect Rate, Contract Completeness, Canonicalization Coverage) (§08.6, gates) |
| **Acceptance criteria** | partial | Updated: ASR < PACT/AUTHGRAPH/CLAWGUARD-style; Benign within 10 pts; Proof Coverage ≥70%; endorsement ≤0.5/task; end-to-end p99 ≤200 ms + pure verifier separate; high-impact over-broadening ≤5–10%; near-0 ASR for fake-proof/replay/scope/task/memory; ablations show memory/delegation/endorsement necessary; kill test shows security/usability/auditability gap (§10) |
| **Rebuttal / Reviewer sim** | referenced wrong systems | Rewritten with correct identities; rebuttal answers the 15 specified questions (§14, REVIEWER_SIMULATION) |

**Net effect:** the fatal error of *mischaracterizing real adjacent systems* (which would draw an immediate reject) is removed, while all of v2's rigor is preserved. The note in the v2 row below ("PACT → ARGUS") was itself the error v3 corrects.

---

## v2 — citation resolution (PARTIALLY ERRONEOUS; superseded by v3)

> **Correction:** the "Related work" row below recorded an *incorrect* resolution — it substituted ARGUS for PACT and mapped PFI→Progent. v3 reverses both. Retained here only for history.

Changes on top of v1, each tied to the demand it answers:

| Area | v1 state | v2 change |
|---|---|---|
| **Related work** *(ERRONEOUS — see v3)* | PCAA/AUTHGRAPH/PACT flagged `[VERIFY]` | v2 wrongly substituted ARGUS for PACT and mapped PFI→Progent; **corrected in v3** |
| **Headline claim** | "proof-carrying" was central | **Demoted** — PCAA owns proof-carrying. Identity moved to consumable-linear-capabilities + authority-provenance calculus + cross-boundary mechanisms (§00, §12.4) |
| **Formal model** | `G*`/`G_sys` conflated; theorem mixed them | **Separated.** Oracle-AuthSpec vs Deployed-AuthSpec modes; T1 parametric in the AuthSpec in force; faithfulness defined (§05) |
| **Coverage bound** | `Pr[win] ≤ Σ(1−κ)` (unrigorous) | **Deleted.** Replaced by residual field *sets* `Residual(t)=F(t)\O(t)`, no probability (§05.6, `TCB_AND_ADAPTER_COVERAGE.md`) |
| **run_shell** | "allowlist" mentioned | **Full allowlisted CommandTemplate schema** (typed holes, env/cwd/stdin contract) (§06.4, `CANONICALIZATION_BYPASS_GATE.md`) |
| **Shell/canon attacks** | absent | Added adaptive #16 (env/cwd/stdin) and #17 (template-argument injection) (§09.5) |
| **Kill test** | absent | **New** `KILL_TEST_PLAN.md` — CaMeL head-to-head, 12 cross-boundary tasks, run first, pivot |
| **Killer examples** | 3 inline in §01 | **New `KILLER_EXAMPLES.md`** — 10 complete, full schema |
| **AuthLaunderBench** | mechanism-agnostic oracles (v1) | Added **threat sourcing table** (§07.6) |
| **Baselines** | strong baselines + tiers (v1) | Added **oracle-vs-auto provenance** axis; *names corrected in v3* (§09) |
| **ProofObjectRemoved** | ablation #11 stub | **Full 6-axis treatment** + pre-committed drop rule (§09.4) |
| **TCB** | basic table (v1) | **Per-component LoC target + failure mode + test strategy** (`TCB_AND_ADAPTER_COVERAGE.md`) |
| **Faithfulness gate** | metric mentioned | **New `AUTHSPEC_FAITHFULNESS_GATE.md`** — over/under-broadening, ambiguity-exploit, §3.11 ON/OFF |
| **Bypass gate** | canonicalization caveats only | **New `CANONICALIZATION_BYPASS_GATE.md`** — ≥30 per-vector tests |
| **Experiment plan** | 3 layers | Added **Layer 0 kill test** + gates + residual study; baseline names corrected (§08) |

Net effect: the two defects a PC would catch (G*/G_sys conflation, probabilistic coverage bound) are fixed; the related-work risk (unverified citations) is closed; the proof-carrying overlap with PCAA is acknowledged and the contribution repositioned; and the thesis is now falsifiable up front via the kill test.

---

## v1 — original → first revision

Concrete diff from the original `CapProof_USENIX_Package` to the first revision. Organized as (1) structural changes, (2) the substantive fixes that address specific reject risks, (3) per-file changes.

## 1. Structural changes

- **Split** the original `02_system_design.md` into `02_threat_model_and_security_goals.md` + `03_system_design.md`, and the original `03_formal_model.md` into `04_capability_and_proof_model.md` + `05_formal_model_and_theorems.md`. Rationale: a security venue reads threat-model and formalism as first-class, not as subsections of design.
- **Renamed/retargeted** `08_usenix_reviewer_assessment.md` → folded into `13_usenix_acceptance_checklist.md` (self-audit) + `REVIEWER_SIMULATION.md` (three external voices). Removed `09_ai_review_prompt.md` (meta-artifact, not part of the paper plan).
- **Added** `10_expected_results_and_success_criteria.md`, `11_limitations_ethics_and_tcb.md`, `12_related_work_positioning.md`, `14_rebuttal_preparation.md`, `ACCEPTANCE_GAP.md`, `TOP_10_ACTION_ITEMS.md`, `REVIEWER_SIMULATION.md`.

## 2. Substantive fixes (each maps to a reject risk in the original)

| # | Original reject risk | Fix in this revision | Where |
|---|---|---|---|
| 1 | **CaMeL overlap unaddressed; CaMeL absent from baselines** (paper-killer) | CaMeL is now (a) a mandatory original-implementation baseline, (b) an adopted component for the exfiltration dimension (G4), (c) explicitly *stronger than CapProof on exfiltration*. Positioning is complementarity, not dominance. | §00, §09.1, §12.2 |
| 2 | **AuthSpec Builder treated as trusted** (circular trust root) | AuthSpec Builder declared **untrusted**; theorems relativized to ground-truth `G*`; high-impact bindings need explicit/confirmed status; faithfulness is a separately measured property with its own adversary | §02.3, §02.5, §02.6, §03.3, §05 |
| 3 | **AuthLaunderBench self-dealing** (oracles used CapProof's own representation) | Oracles are **mechanism-agnostic** (observable side effects only); `ground_truth_authspec` used only for internal scoring; **held-out red team** authors adaptive attacks | §07.1, §07.2, §09.4 |
| 4 | **Strawman baselines** ("CapProof minus a feature" relabeled as prior systems) | Original implementations where available (CaMeL, Task Shield); faithful reimpls calibrated on the source benchmark subset otherwise; same backbone/harness/budget; ablations separated from external baselines | §09.1 |
| 5 | **"Proof" over-claimed** (monitor re-verifies, so proof looked redundant) | Proof demoted to a checkable witness/certificate; value argued (search-vs-verify, audit, cheap replan); `ProofObjectRemoved` ablation; pre-commitment to renaming if it adds nothing | §04.4, §09.2 #11 |
| 6 | **Data exfiltration through authorized channels out-of-scope** despite being core | Brought partially in-scope via adopted CaMeL-style data-flow capability (G4); the precise residual (content of an authorized doc to an authorized recipient) is stated, not hidden | §01.7, §02.7 G4, §11.1 #3 |
| 7 | **Theorem 1 vacuous** ("if TCB has no bugs, TCB is sound") | Theorem 1 recast as a function of adapter coverage; (NOTE: v2/v3 replaced the probabilistic leakage bound with a set-based residual characterization — see TCB_AND_ADAPTER_COVERAGE.md); coverage measured on real tools | §05.5, §05.6, §06.3 |
| 8 | **Canonicalization assumed solved** (esp. shell) | Per-role canonicalizer with a `total: bool` flag; `command` declared **not** totally canonicalizable; `run_shell` is **allowlist-only** with non-soundness stated | §06.4, §11.1 #4 |
| 9 | **No concurrency / TOCTTOU model for the capability store** | Two-phase `verify→reserve(atomic CAS)→execute→commit→consume(idempotent, nonce)`; state machine; lease-based release | §03.5, §03.14, §06.6 |
| 10 | **No key management / agent PKI** | Minting key, receipt-signing key, agent identity keys added; agent PKI declared a prerequisite for Theorem 3 | §06.5 |
| 11 | **Endorsement confused-deputy** (approve a string, bind a different value) | Endorsement bound to `H(canonical_action)`; challenge displays the **canonical** recipient/path/endpoint/data-class to the user | §03.11 |
| 12 | **Weak statistics / single model** | ≥3 backbones, Wilson CIs, McNemar, paired bootstrap, Holm–Bonferroni; 3 runs at T=0 | §08.7 |
| 13 | **Missing elicitation-layer attack** | Added the **ambiguity-exploit** adaptive attack (#15) that injects no instructions; mitigated by §3.11 and *measured* | §02.6, §09.3 #15 |
| 14 | **Citation credibility** (unverified PACT/AUTHGRAPH/PCAA/AgentArmor claimed as known) | Confirmed vs. `[VERIFY]` split; explicit instruction to read and accurately cite before submission; novelty stated conservatively and shown to survive narrowing | §12, README |

## 3. Per-file summary

- `README.md` — new: file map, five key changes, citation-hygiene warning.
- `00_executive_summary.md` — rewritten: calibrated contributions, explicit CaMeL relationship, accept-probability *ladder* (a plan ≠ Accept), pre-submission bars.
- `01_problem_definition.md` — rewritten: Unverifiable Authorization, laundering taxonomy table, three killer examples each with a proof-failure reason, explicit non-goals.
- `02_threat_model_and_security_goals.md` — new split: principals, attacker can/cannot, full TCB table (**AuthSpec Builder = untrusted**), Authorization Integrity, attack game relative to `G*`, the faithfulness sub-problem, ranked goals G1–G5.
- `03_system_design.md` — rewritten: architecture, component table, `binding_status`, two-phase consumption, both provenance modes, memory stripper pseudocode, delegation cert, canonical-bound endorsement challenge, public API, deterministic verifier pseudocode, defenses vs. four runtime attacks.
- `04_capability_and_proof_model.md` — new split: full capability schema + linearity policy, proof/witness schema, three proof DAGs, the honest "why carry a proof" argument + demotion commitment.
- `05_formal_model_and_theorems.md` — rewritten: 9 inference rules; T1 (coverage-dependent), Characterization 1′ (residual sets; the v1 "leakage bound" was removed as unrigorous), T2, T3, T4 — each with assumptions, proof sketch, and explicit non-guarantees; coverage formalized; global assumptions listed.
- `06_implementation_plan.md` — rewritten: build tiers; MVP tool contracts with *every* authority-bearing field (bcc/headers/env/redirects); κ-measurement experiment; canonicalizer decidability table; key management + agent PKI; sandboxing; milestones.
- `07_authlaunderbench_design.md` — rewritten: mechanism-agnostic oracle principle, red-team independence, 6 suites × 25, per-task layout, oracle sketches, 2 concrete tasks/suite, difficulty labels, relationship to existing benchmarks.
- `08_experiment_plan.md` — rewritten: three layers, existing-benchmark table, cross-cutting measurements (faithfulness/provenance-sensitivity/coverage/endorsement/denial-leakage), metric definitions, statistics + reproducibility, result-presentation plan.
- `09_baselines_ablations_adaptive.md` — rewritten: strong baselines with fairness controls (CaMeL mandatory, tuned), ablations-vs-baselines separation, 12 ablations, 15 adaptive attacks, attack-generation protocol, pre-registered falsification conditions.
- `10_expected_results_and_success_criteria.md` — new: pre-submission bars, illustrative main table, expected ablation/sensitivity outcomes, what a negative result looks like + the plan for it.
- `11_limitations_ethics_and_tcb.md` — new: 8 limitations up front, out-of-scope restate, TCB accounting, ethics (mock/sandboxed eval, responsible disclosure, dual-use, IRB).
- `12_related_work_positioning.md` — new: per-system delta table, confirmed vs. `[VERIFY]`, conservative novelty statement, related-work to-dos.
- `13_usenix_acceptance_checklist.md` — new: reviewer-facing self-audit + the three open checks that gate acceptance.
- `14_rebuttal_preparation.md` — new: 14 anticipated questions, each with a strong answer and the backing experiment.
