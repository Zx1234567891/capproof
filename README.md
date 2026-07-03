# CapProof — Revised USENIX Security Submission Package (v7)

**Working title:** CapProof: Capability-Consuming Authorization for Tool-Using AI Agents
*("Proof-carrying" is not a headline claim — PCAA owns it; see §12.4.)*

> One-line claim (calibrated, non-marketing):
> *The strongest adjacent agent defenses — CaMeL (value data-flow), PACT (argument-level provenance), AUTHGRAPH (dual-graph detection), CLAWGUARD (tool-call boundary, strong on MCP/skill), PFI (trusted/untrusted agents), AgentArmor (trace-graph type-checking), DRIFT (memory isolation) — can often detect or block unsafe actions. What they do not primarily do is model **authority itself as a consumable resource** — with explicit lifetime, scope, delegation attenuation, endorsement semantics, persistence restrictions, and spend state across memory, delegation, and endorsement boundaries. CapProof requires **high-impact actions to consume scoped capabilities and pass deterministic authorization-proof verification, especially across memory, delegation, endorsement, and persistent authority boundaries.** We make this property — Authorization Integrity — precise relative to an explicit AuthSpec, bound it to a stated TCB and assumptions, and test whether the difference is real with a CaMeL head-to-head kill test (run first).*

This package is a **research/paper plan**, not a finished paper. Each file lifts into a draft. It deliberately under-claims: no "solve prompt injection," no "fully secure," every theorem assumption listed and slated for measurement, and **no prior system's contribution claimed as ours**.

## What v7 fixes (typo, history, and metric-naming pass)

v7 fixes four residual nits: the README "raw-ASR-rout" typo; the CHANGELOG history row that could read as "AgentArmor removed" (now: ARGUS/Progent/StruQ removed; AgentArmor restored in v4 and retained); the **metric naming error** where `Pr[AuthClosure(G_sys) ⊆ AuthClosure(G*)]` was labeled `Faithfulness_over` and "the dangerous direction" (it is the safe containment — now **No-Over-Broadening Rate**, with **AuthSpec Over-Broadening Rate = Pr[⊄]** as the risk headline, matching the gate file); and the bypass-gate phrase "bounds the rest by measurement" (now "empirically characterizes the residual risk"). See `CHANGELOG.md`.

## What v6 fixed (history: final consistency & small-fix pass)

v6 changes **no design** — it removes residual inconsistencies a reviewer would notice:

1. **Versioning unified; no "AgentArmor removed" confusion.** Every current-state sentence states AgentArmor is a **real system, retained** (trace-analysis related work + auxiliary/optional baseline); only ARGUS/Progent/StruQ are the removed erroneous comparators.
2. **Oracle-vs-Deployed AuthSpec made explicit in the attack game** (§2.5): the game is the Oracle-AuthSpec game (`G_force=G*`); deployed experiments use `G_sys` and separately measure faithfulness; **no capability is ever minted from `G*` in a deployed system**.
3. **MCP/skill success bars re-verified** — competitive ASR with CLAWGUARD-style **plus** proof/auditability/replay/scoping/localization advantage; **no promise of outperforming CLAWGUARD-style on raw ASR in the MCP/skill suites** anywhere.
4. **Benchmark status table** (Benchmark / Status / Intended Use / Required Verification) — AgentDojo confirmed, the rest **planned external validation / subject to availability and licensing**.
5. **Tool Contract Registry completed** — memory adds **persistence_flag** (content/authority_claims/provenance/persistence_flag); delegation, file, send_email, HTTP complete.
6. **TCB statuses explicit** — **Proof Synthesizer NOT in the security TCB** (monitor re-verifies); AuthSpec Builder outside mechanism-soundness TCB but affects deployed faithfulness; A7 tool honesty an assumption; adapter completeness a measured object.
7. **Rebuttal +Q18** ("Why not start with AuthLaunderBench instead of the kill test?"); **threat sourcing +observable success/safe-behavior table**; **PFI-style status clarified** (promotable auxiliary); **bypass gate wired into the adaptive/ablation matrix**; **"bounded by coverage" → "characterized by coverage"**.

(See `CHANGELOG.md` for the full v6 table; v5/v4/v3 notes remain for history.)

## What v5 fixed (history)

v5 was a consistency pass that unified MCP/skill success bars, added theorem assumption A7, completed the tool-contract registry, added the bypass-gate contract-field column, and added rebuttal Q17:

1. **Success bars unified on MCP/skill.** Nowhere do we promise CapProof out-ASRs CLAWGUARD-style on MCP/skill. **Memory/Delegation/Endorsement** → significantly reduce ASR / replay-risk / unauthorized persistence; **MCP/Skill** → at least competitive on ASR **plus** a proof/auditability / capability-replay-prevention / one-shot-endorsement-scoping / failure-localization / audit-replay advantage (§00, §10, README, checklist).
2. **Benchmarks: confirmed vs planned.** Only **AgentDojo** is treated as confirmed; dynamic-replanning / skill-injection / MCP-metadata / broad-injection benchmarks are marked **planned external validation** (verified for version/license/task-count/scripts before use; substitute named if unavailable; never reported unless run). No "verify availability / exact names / to be confirmed" notes remain (§08, §13).
3. **Formal model: assumption A7 added.** Theorem assumptions are now A1 provenance fidelity, A2 store unforgeability, A3 minting correctness, A4 monitor correctness, A5 adapter observability, A6 canonical-action binding, **A7 tool implementation honesty relative to declared schema**; each theorem's "what it does not guarantee" now lists content truthfulness, same-source authoritative-data poisoning, unmodeled tool side effects, and AuthSpec-Builder imperfection (§05).
4. **Tool Contract Registry completed.** `send_email` (to/cc/bcc/reply_to/headers/attachments), HTTP (url/method/headers/body/follow_redirects), `write_file` (path/mode/overwrite/symlink_policy), **memory (content/authority_claims/provenance)**, **delegation (parent_agent/child_agent/delegated_scope/TTL/redelegation)** (§06).
5. **Bypass gate: contract-field column.** Every one of the ≥30 attacks now maps to the **adapter/contract field** that must surface it (plus memory/delegation rows) — the audit hook tying each deny reason to a declared field (`CANONICALIZATION_BYPASS_GATE.md`).
6. **Rebuttal: +Q17 "Why not make the proof object optional?"** (the design already separates the proof from the identity; `ProofObjectRemoved` decides). AgentArmor's "why not a main baseline" stays as Q16.
7. **Adapter coverage: full-vs-partial soundness stated.** Full coverage → sound over all declared+observable authority-bearing fields; partial → sound only over contract/receipt-exposed fields; residual characterized empirically by the five coverage metrics (`TCB_AND_ADAPTER_COVERAGE.md`).

(See `CHANGELOG.md` for the full v5 table; v4/v3 notes remain for history.)

## What v4 fixed (history)

v4 restored AgentArmor, removed the inaccurate "single-trajectory" framing, and un-strawmanned CLAWGUARD:

1. **AgentArmor restored** as real related work (CFG/DFG/PDG over the runtime trace + graph annotator/inspector). Delta: AgentArmor detects from the trace; CapProof consumes a capability **before execution**. Placed as **trace-analysis related work + auxiliary subset baseline**, not a main baseline (§09, §12, rebuttal Q16).
2. **"Single-trajectory" framing removed everywhere** — it was inaccurate (DRIFT isolates memory, CLAWGUARD covers MCP/skill, PFI models agent flow). Replaced with: *existing defenses can detect/block, but do not primarily model authority as a consumable resource with explicit lifetime/scope/attenuation/endorsement/persistence/spend across memory, delegation, endorsement boundaries.*
3. **CLAWGUARD un-strawmanned** — a strong MCP/skill defense; CapProof does **not** promise to out-ASR it there. Distinct win = proof semantics, one-shot endorsement, capability-replay prevention, delegation/endorsement scoping, failure localization, audit/replay.
4. **Theorem assumptions named explicitly** — A1 provenance fidelity, A2 store unforgeability, A3 minting correctness, A4 monitor correctness, A5 adapter observability, A6 canonical-action binding; each theorem followed by "what it does not guarantee" (§05).
5. **Kill test = go/no-go lifeline** with three acceptable outcomes (security / usability / proof-auditability gap) and an explicit No-Go + pivot (KILL_TEST_PLAN).
6. **Killer-example baseline claims made cautious** (what each system *primarily models*, not "definitely misses"); AgentArmor added to each. **Baselines split** into main {CaMeL, PACT-oracle/auto, AUTHGRAPH-style, CLAWGUARD-style, Native, CapProof-oracle/auto} and auxiliary {DRIFT-style, PFI-style, AgentArmor-related, Task Shield, PromptArmor}.
7. **ProofObjectRemoved risk stated**: if removing the proof DAG keeps security and doesn't raise latency, the proof object is **not** the identity — main line stays capability-consuming authorization (§09.4).

(See `CHANGELOG.md` for the full v4 table; the v3 correction notes below remain for history.)

## What v3 fixed (history)

v3 was a **targeted correction** that fixed the related-work / baseline factual errors:

1. **Prior-work identities corrected (the central fix).** Using the authoritative identities:
   - **PACT** = *The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck* — argument-level provenance; authority-bearing-argument roles target/command/credential/content/selector/control. **(v2 wrongly substituted "ARGUS" for PACT — removed.)**
   - **PFI** = *Prompt Flow Integrity to Prevent Privilege Escalation in LLM Agents* — trusted/untrusted agent, Data ID, DataGuard, CtrlGuard. **(v2 wrongly mapped PFI→"Progent" — removed.)**
   - **CLAWGUARD** = *A Runtime Security Framework for Tool-Augmented LLM Agents Against Indirect Prompt Injection* — deterministic tool-call boundary; covers web/local content injection, MCP poisoning, skill-file injection. **(v2 flagged it unconfirmed — now stated correctly.)**
   - **AUTHGRAPH** = clean Authorization Graph + Injected Reasoning Graph; tool-level + parameter-source-level detection.
   - **CaMeL** = P-LLM/Q-LLM isolation; capability metadata; data-flow graph; custom interpreter; security policies.
   - **PCAA** = proof-carrying agent actions; action certificate; runtime-neutral governance; receipts; proof bundle.
   - Comparators erroneously introduced in v2 (**ARGUS, Progent, StruQ**) were **removed** as not matching any real adjacent system. **AgentArmor is a real system and is retained** (trace-analysis related work + auxiliary/optional baseline — see §12, §09); it is **not** an erroneous comparator. Current comparator set: main {Native, CaMeL, PACT-oracle/auto, AUTHGRAPH-style, CLAWGUARD-style, CapProof-oracle/auto}, auxiliary {PromptArmor-style, Task Shield-style, PFI-style, DRIFT-style, AgentArmor-related subset}.
2. **arXiv IDs stripped.** v2 mis-mapped IDs; v3 cites by **paper title / system name**, with exact arXiv/venue filled from `prior_work.bib` at submission. No fabricated or mis-attributed IDs remain.
3. **New core delta table** (§12.3): `Prior Work | What It Solves | What It Does Not Solve | CapProof Delta`, making explicit that CapProof's delta is **not** "first to do capability/provenance/authorization-graph/tool-boundary" but **consume-a-rooted-capability-before-execution against cross-boundary authority laundering**.
4. **Kept from v2 (unchanged-in-spirit, names corrected):** `G*`/`G_sys` separation + Oracle/Deployed modes; adapter-coverage **residual characterization**; **`run_shell` allowlisted command templates**; CaMeL head-to-head **kill test**; **ProofObjectRemoved** ablation; **AuthSpec Faithfulness Gate**; **Canonicalization/Adapter Bypass Gate**; **TCB tightening**; memory stripping; delegation certificate; one-shot endorsement.
5. **Scrubbed** for `[VERIFY]`, wrong paper names, wrong arXiv mappings, unverified claims, over-strong theorems, pseudo-probability bounds, arbitrary-shell canonicalization claims, and LLM-as-security-boundary phrasing.

## File map

Design, release, status, and reviewer Markdown files live under `docs/`;
generated top-level reports live under `artifact_reports/`; repository tools
and reproduction harnesses live under `tools/`. The repository root keeps
`README.md` as the single top-level Markdown entry point. See
`docs/status/PROJECT_LAYOUT.md` for the current directory convention.

| File | Contents |
|---|---|
| `00_executive_summary.md` | Cross-boundary thesis, proof-carrying demotion (PCAA), accept ladder |
| `01_problem_definition.md` | Unverifiable Authorization, Authority-Laundering taxonomy, examples |
| `02_threat_model_and_security_goals.md` | Attacker model, TCB table (AuthSpec Builder untrusted), attack game |
| `03_system_design.md` | Architecture, two-phase consumption, provenance modes, verifier pseudocode |
| `04_capability_and_proof_model.md` | Capability schema + linearity, proof DAGs, demotion commitment |
| `05_formal_model_and_theorems.md` | `G*` vs `G_sys`, Oracle/Deployed modes, rules, T1–T4 + residual characterization, faithfulness |
| `06_implementation_plan.md` | Build order, tool contracts, allowlisted `run_shell`, canonicalizer, keys, milestones |
| `07_authlaunderbench_design.md` | 6 suites, observable-side-effect oracles, threat sourcing table |
| `08_experiment_plan.md` | Kill test + Layers A/B/C + gates, metrics, statistics, reproducibility |
| `09_baselines_ablations_adaptive.md` | Reproduction tiers, oracle/auto, 12 ablations (incl. ProofObjectRemoved), 17 adaptive attacks |
| `10_expected_results_and_success_criteria.md` | Pre-submission bars, expected tables, falsification, negative-result plan |
| `11_limitations_ethics_and_tcb.md` | Limitations, ethics, TCB summary (detail in `TCB_AND_ADAPTER_COVERAGE.md`) |
| `12_related_work_positioning.md` | **Corrected identities**; core delta table; conservative novelty |
| `13_usenix_acceptance_checklist.md` | Reviewer-facing checklist mapped to files |
| `14_rebuttal_preparation.md` | 15 anticipated questions + strong answers + backing experiment |
| `KILLER_EXAMPLES.md` | **10 complete killer examples** across 5 channels |
| `KILL_TEST_PLAN.md` | **CaMeL head-to-head kill test**, go/no-go, pivot |
| `TCB_AND_ADAPTER_COVERAGE.md` | Per-component TCB (LoC/failure/test) + **residual characterization** + coverage metrics |
| `AUTHSPEC_FAITHFULNESS_GATE.md` | 50-request gate; over/under-broadening, grant precision/recall, endorsement recovery |
| `CANONICALIZATION_BYPASS_GATE.md` | ≥30 bypass attacks + expected deny reasons; `run_shell` templates |
| `REVIEWER_SIMULATION.md` | Three reviews (A systems / B agent-security / C methodology) |
| `CHANGELOG.md` | Diff: original → v1 → v2 → v3 → v4 → v5 → v6 → v7 |
| `ACCEPTANCE_GAP.md` | What still stands between this plan and an Accept |
| `TOP_10_ACTION_ITEMS.md` | Prioritized next actions |

## Citation status (v7)

**Cited by paper title / system name (arXiv/venue in `prior_work.bib` at submission):** CaMeL; PACT (*The Granularity Mismatch in Agent Security…*); AUTHGRAPH (clean Authorization Graph + Injected Reasoning Graph); CLAWGUARD (*A Runtime Security Framework for Tool-Augmented LLM Agents Against Indirect Prompt Injection*); PFI (*Prompt Flow Integrity to Prevent Privilege Escalation in LLM Agents*); **AgentArmor** (CFG/DFG/PDG trace abstraction + graph annotator/inspector — **a real adjacent system, retained** as trace-analysis related work + auxiliary/optional baseline); PCAA (*Proof-Carrying Agent Actions*); Task Shield; PromptArmor; DRIFT (memory isolation, auxiliary); AgentDojo. **No arXiv IDs are asserted in-text** (v2's were mis-mapped). **Removed (introduced in error in v2):** ARGUS, Progent, StruQ. Mischaracterizing a real system is a fast reject — §12 states each system's mechanism accurately and **claims none of them as CapProof's contribution**.
