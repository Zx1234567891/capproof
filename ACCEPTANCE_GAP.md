# ACCEPTANCE_GAP

What still stands between this **plan** and a USENIX Security **Accept**. Prior revisions closed the *fatal* related-work risk (mischaracterizing real systems) and the rigor gaps (G*/G_sys conflation, probabilistic coverage bound); the remaining gap is execution + one positioning risk (PCAA proximity) that the kill test and `ProofObjectRemoved` must resolve.

## A. The gap is execution (a plan cannot be accepted; a paper with results can)

| Gap | What's missing | Why it gates acceptance | Effort |
|---|---|---|---|
| **Kill test executed** | The 12-task head-to-head vs **CaMeL, PACT-style, AUTHGRAPH-style, CLAWGUARD-style** showing cross-boundary separation | This *is* the contribution's evidence; without it a reviewer assumes CapProof ⊆ {CaMeL, PACT, AUTHGRAPH} | **High / first** |
| **AuthLaunderBench built** | 150 tasks, observable-side-effect oracles, held-out red team, threat-sourced distribution | The instrument that generalizes the kill-test finding | High |
| **System implemented** | TCB core (Core Verifier <1,500 LoC; Minting+Verifier+Store <5,000 LoC) + memory strip, delegation cert, one-shot endorsement | No system, no systems paper | High |
| **AuthSpec faithfulness measured** | Over/Under-Broadening, High-Impact Grant Precision/Recall, Endorsement Trigger Accuracy, Endorsement Recovery — incl. under the ambiguity adversary, §3.11 ON/OFF | Answers "AuthSpec is an LLM" with numbers | Medium |
| **Adapter residual measured** | `Residual(t)` sets + the five coverage metrics on real MCP tools + coverage sweep | Turns the soundness caveat into a finding | Medium |
| **Provenance sensitivity** | PACT/CapProof oracle-vs-auto + error-injection curve | Answers "what if provenance is wrong" with a curve | Medium |
| **ProofObjectRemoved** | 6-axis result deciding whether to keep "proof-carrying" | Pre-empts "is this just PCAA?" — decides the title | Low–Medium |
| **Statistics + multi-model** | ≥3 backbones, Wilson CIs, McNemar, paired bootstrap, Holm | Single-model + uncorrected p-values is a methods reject | Medium |
| **Artifact** | Docker, mock/sandboxed tools, traces/oracles/proof-DAGs, `prior_work.bib` finalized | AE badges help borderline papers | Medium |

## B. The one positioning risk: PCAA proximity

PCAA already carries action certificates / proof bundles with receipts and runtime-neutral governance. The most dangerous neighbor. CapProof's defense:
- Lead with **consumption (linearity)** and the **authority-provenance calculus** (`NO-MINT-UNTRUSTED`, roots, `G*`-relative soundness), which PCAA does not provide.
- Lead with the **cross-boundary mechanisms** (memory strip, delegation attenuation, one-shot canonical endorsement) — PCAA's certificate governs portable accountability, not preventing authority from being laundered across memory/agents/approvals.
- **Frame complementarity:** CapProof can emit PCAA-style receipts; the contributions stack.
- **Pre-commit** (via `ProofObjectRemoved`) to dropping "proof-carrying" if the witness adds nothing beyond a PCAA certificate.

If we do not do this before a reviewer reads PCAA, "this is PCAA + a button" is a credible reject. The package makes the repositioning explicit (§12.4, §00).

## C. Honest risk register (what could still sink it after execution)

1. **Memory covered by a specialist.** DRIFT-style memory isolation (or PACT/AUTHGRAPH extended across turns) may block the memory cases at comparable utility. Mitigation: kill test targets exactly this; the honest bar is "at least as good as DRIFT, unified with delegation/endorsement"; pivot (`KILL_TEST_PLAN.md` §5) if a specialist dominates.
2. **MCP/skill owned by CLAWGUARD.** CLAWGUARD is a strong MCP/skill defense; CapProof should **not** expect an ASR win there. Risk: if the *usability/auditability* gap on MCP/skill is small or unmeasured, the MCP/skill contribution evaporates. Mitigation: quantify endorsement count, over-block, failure-localization on K7/K8; do not claim raw blocking.
3. **CaMeL blocks the cross-boundary suites at similar utility.** Then narrow to the consuming-authorization calculus, or pivot to usability if CaMeL over-asks.
4. **Faithfulness low under ambiguity.** Then `G*`-relative soundness feels academic. Mitigation: §3.11 confirmation + report; narrow to high-impact-confirmed settings; >5–10% high-impact over-broadening gates submission.
5. **Automatic provenance weak.** Then it is a "given good provenance" result. Mitigation: report oracle-vs-auto honestly.
6. **Argument-channel regression vs PACT/AUTHGRAPH.** Implementation/coverage bug, not thesis failure; fix via the bypass gate + coverage doc.
7. **Proof object adds nothing.** Then the proof object is not the identity (pre-committed, §09.4); keep capability-consuming authorization as the main line; cite PCAA.
8. **PCAA proximity.** Addressed by leading with consumption + authority calculus + cross-boundary mechanisms and framing complementarity (§B above, §12.4).

## D. Disposition

- **Today (current version):** not acceptable as a paper; structurally a credible **Borderline-if-executed** plan. The package states each adjacent system accurately (PACT, AUTHGRAPH, CaMeL, CLAWGUARD, PFI, **AgentArmor** — a real trace-analysis system retained as related work + auxiliary baseline, PCAA), uses a defensible consumable-authority claim (not "single-trajectory"), does not strawman CLAWGUARD on MCP/skill, and keeps the rigor fixes. The kill test and PCAA-proximity repositioning remain decisive.
- **After A + the kill test + ProofObjectRemoved:** a defensible **Weak Accept**, **Accept reachable** if a real gap is shown and attributed (security on delegation/endorsement; at-least-DRIFT on memory; usability/auditability on MCP/skill), faithfulness is acceptable with confirmation, and the artifact reproduces.
- **Single highest-leverage action:** the kill test (A, row 1). It validates the thesis or tells us to pivot — do it before building the full benchmark.
