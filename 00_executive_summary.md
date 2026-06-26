# 00. Executive Summary

## Thesis

Tool-using LLM agents take high-impact actions — sending email, writing files, executing shell, calling external endpoints — on the basis of a **mixed-trust context** that fuses the trusted user request with untrusted webpages, emails, tool outputs, MCP metadata, skill files, long-term memory, and messages from lower-privilege agents. Today, when such an action fires, the system cannot answer the question that actually matters:

> *Does this action's authority derive from trusted user intent, system policy, an explicit one-shot endorsement, or an attenuation-preserving delegation — or has it been laundered out of untrusted context?*

We call the inability to answer this **Unverifiable Authorization**, the attack that exploits it **Authority Laundering**, and the property a defense should provide **Authorization Integrity**. CapProof enforces Authorization Integrity by making every high-impact action **consume** a scoped, non-forgeable, **linear** capability whose chain terminates in a trusted root, checked by a **deterministic** reference monitor. The LLM is outside the TCB; it only proposes actions and witnesses.

> **A positioning correction this revision makes explicit.** "Proof-carrying agent actions" is **not** our novelty — **PCAA** already owns that framing (action certificates, receipts, proof bundles, runtime-neutral governance). We retire "proof-carrying" as a headline and reposition CapProof's identity around **capability-consuming authorization**: modeling **authority itself as a consumable resource** (explicit lifetime, scope, delegation attenuation, one-shot endorsement, memory-authority persistence restriction, and spend state). Adjacent defenses (CaMeL, PACT, AUTHGRAPH, CLAWGUARD, PFI, AgentArmor, DRIFT) can often detect or block unsafe actions but do not primarily center this consumable-authority model. Whether CapProof should carry a witness *at all* is settled empirically by the `ProofObjectRemoved` ablation (§09.4); if it adds nothing beyond a PCAA-style certificate, we keep capability-consuming authorization as the identity and cite PCAA for that layer.

## What this is and is not

This is a paper plan engineered to be competitive at USENIX Security if executed. It is **not** the paper. We therefore avoid the three over-claims that sink agent-security submissions:

- We do **not** claim to "solve prompt injection." We enforce *authorization integrity for high-impact tool effects* — a narrower, checkable property.
- We do **not** claim guaranteed safety. Every theorem is stated relative to an explicit TCB and a list of assumptions, each of which we plan to *measure* (provenance fidelity, adapter coverage, AuthSpec faithfulness).
- We do **not** let any LLM be the final security boundary, including our own AuthSpec Builder, which we treat as untrusted.

## Contributions (calibrated)

1. **Problem framing.** A precise definition of Unverifiable Authorization and a taxonomy of *Authority Laundering* across six channels (argument, memory, delegation, MCP metadata, skill workflow, endorsement), distinguishing it from indirect prompt injection: a defense can drive ASR to near-zero on AgentDojo and still be unable to verify an authorization chain. (§01)
2. **Security property + attack game.** A formal statement of Authorization Integrity and an Authority-Laundering security game whose win condition is defined relative to a fixed ground-truth AuthSpec, decoupling the *enforcement* claim from the *intent-elicitation* claim. (§02, §05)
3. **Mechanism.** A capability-consuming reference monitor with: two orthogonal capability dimensions — **action-authority capabilities** (linear/affine, consumable) and **data-flow capabilities** (CaMeL-style readers, adopted, for exfiltration); **memory-authority stripping**; **delegation certificates** (attenuation-only); and **one-shot, non-transferable endorsement** bound to a canonical action. (§03, §04)
4. **Formalization.** Inference rules and four theorems — Authorization Integrity Soundness (as a function of adapter coverage), No Authority Laundering, Delegation Non-Amplification, and Prefix Soundness for Replanning — each with a proof sketch and an explicit statement of what it does *not* guarantee. (§05)
5. **Evaluation + artifact.** AuthLaunderBench (six laundering suites) with **mechanism-agnostic** oracles and **held-out** adaptive attacks, plus evaluation on **AgentDojo** (confirmed) and **planned external validation** on dynamic-replanning / skill-injection / MCP-metadata benchmarks, against **strong** baselines including CaMeL (original or faithful). Built **after** the kill test passes. (§07–§10)

The honest core, if reviewers force us to one sentence: **a reframing of agent risk as authorization integrity, plus the observation that adjacent defenses (CaMeL, PACT, AUTHGRAPH, CLAWGUARD, PFI, AgentArmor, DRIFT) can detect or block unsafe actions but do not primarily model authority as a consumable resource with explicit lifetime, scope, delegation attenuation, endorsement semantics, persistence restrictions, and spend state across memory/delegation/endorsement boundaries — and a mechanism that does, by requiring high-impact actions to *consume* a rooted capability rather than merely *pass a check*.** The CaMeL head-to-head kill test (`KILL_TEST_PLAN.md`) that checks whether this difference is *real* is the paper's **Figure 1** and the first experiment to run.

## Relationship to CaMeL (the load-bearing comparison)

CaMeL extracts control/data flow from the trusted query and attaches *data-flow* capabilities to values to prevent exfiltration over unauthorized flows. CapProof's design overlaps with CaMeL on the "plan before untrusted data, gate at the tool call, ask the user when unauthorized" backbone. We respond to this directly:

- We **adopt** CaMeL's data-flow capability for the exfiltration dimension rather than reinventing it, and we say so.
- CapProof's delta is a **second capability dimension** — consumable action-authority capabilities for authority-bearing arguments — plus three mechanisms CaMeL does not target: persistence of authority through memory, attenuation across multi-agent delegation, and the laundering of human approval.
- We are explicit that **CaMeL is stronger than CapProof on data-flow exfiltration** and that **CapProof is stronger on authority laundering**; the contribution is the laundering axis and the measurement that shows the gap, not a claim of strict dominance.

If we cannot demonstrate, against CaMeL's real implementation, attack classes where CaMeL admits a laundered action and CapProof does not, the paper has no delta and should not be submitted. This is action item #1.

## Accept-probability ladder (calibrated)

| State of the work | Likely reviewer lean |
|---|---|
| Concept + rules sketch, no system, self-built baselines | **Weak Reject** |
| MVP monitor + mechanism suite + proof rules, CaMeL still absent | **Borderline (lean reject)** |
| Full system + AuthLaunderBench + CaMeL baseline + adaptive attacks + ablations, but oracles still mechanism-coupled or single model | **Borderline → Weak Accept** |
| All of the above + mechanism-agnostic oracles + held-out red team + multi-model + measured adapter coverage and AuthSpec faithfulness + complete artifact | **Weak Accept (Accept reachable)** |

We do not promise Accept from a plan. Acceptance is gated on *executing* the measurements that make the assumptions falsifiable. See `ACCEPTANCE_GAP.md`.

## Pre-submission success bars (must all hold)

- On AuthLaunderBench **Memory / Delegation / Endorsement** suites, CapProof **significantly reduces** ASR, endorsement-replay risk, or unauthorized authority persistence (paired test, Holm-corrected) versus strong baselines, and is **at least as good as the channel specialist** (DRIFT-style on memory, PFI-style on delegation). On the **MCP metadata / Skill** suites — where **CLAWGUARD-style is a strong defense** — CapProof is **at least competitive on ASR** and demonstrates a **proof/auditability, capability-replay-prevention, one-shot-endorsement-scoping, failure-localization, or audit/replay** advantage, **not** an ASR rout.
- Benign Success Rate within **10 points** of the best baseline overall.
- On the argument-laundering and exfiltration suites, CapProof is **no worse** than CaMeL, **PACT-style**, and **AUTHGRAPH-style** (we expect parity, not dominance — these are strong there, and we adopt CaMeL's data-flow capability).
- Replay / fake-proof / scope-confusion / agent-confusion adaptive attacks: **near 0% ASR**.
- Average endorsements **≤ 0.5 / task** on static tasks; reported (not bounded) on dynamic tasks.
- Pure verifier latency p99 ideally < 20 ms; end-to-end guard overhead p99 ≤ 200 ms.
- Ablations show memory-strip, delegation-cert, and one-shot endorsement are each *necessary* (removing each raises ASR on its target suite by a large, significant margin).
- We **report**, not hide: AuthSpec faithfulness, provenance error sensitivity, and adapter coverage on real MCP tools, including the cases where CapProof loses.
