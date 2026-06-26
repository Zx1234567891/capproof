# 10. Expected Results and Success Criteria

## 10.1 Pre-submission bars (all must hold; else do not submit as-is)

1. **Laundering separation (the core result), stated by channel.** On the **Memory / Delegation / Endorsement** suites, CapProof ASR is significantly lower than at least one strong comparator that mis-allows (McNemar, Holm-corrected, per suite), and **at least as good as the channel specialist** (DRIFT-style on memory, PFI-style on delegation). On the **MCP metadata / Skill** suites, where **CLAWGUARD-style is a strong defense**, we do **not** promise an ASR win; the claim there is a **usability and/or proof-auditability gap** (fewer endorsements / lower over-block, or reusable-explainable-consumable-replayable authorization chains and failure localization). On the **Argument** suite we target **parity** with PACT/AUTHGRAPH.
2. **No collapse on ordinary injection.** On AgentDojo, CapProof ASR is comparable to the best defense and Benign Success is within 10 points of the best baseline.
3. **Parity on exfiltration.** On the exfiltration-tagged tasks (G4), CapProof is *no worse* than CaMeL (we adopt its data-flow capability; if we are worse, the integration is broken).
4. **Runtime-attack near-immunity.** Replay / fake-proof / cap-forgery / scope-confusion / task-confusion / agent-confusion / **memory-replay** adaptive attacks: ASR ≈ 0%.
5. **Necessity of each mechanism.** NoMemoryStrip, NoDelegCert, NoOneShot each raise ASR on their target suite by a large, significant margin vs. full CapProof — clearly establishing memory/delegation/endorsement are necessary, not redundant.
6. **Stated, acceptable costs.** Average endorsement **≤ 0.5/task** on static tasks (distribution reported on dynamic); **pure verifier p99 reported separately** and **end-to-end guard p99 ≤ 200 ms**; token overhead and TCB size (Core Verifier <1,500 LoC; Minting+Verifier+Store <5,000 LoC) reported.
7. **Proof coverage.** **Proof Coverage ≥ 70%** of authorizable high-impact actions get a witness without human help (an automation/utility target — the security claim rests on ASR/Secure-Utility, not coverage).
8. **Faithfulness under ambiguity.** **High-impact AuthSpec over-broadening ≤ 5–10%** (with §3.11 confirmation ON, on the ambiguous strata); above that gates submission or forces a narrowed deployment claim.
9. **Kill test shows a gap.** The CaMeL head-to-head (`KILL_TEST_PLAN.md`) lands in a go scenario: a **security gap** (CaMeL mis-allows on memory/delegation/endorsement), a **usability gap** (CaMeL blocks but over-asks/over-blocks), or a **proof/auditability gap** — and the gap is mechanistically attributed via ablation flips.
10. **Falsifiable assumptions measured.** AuthSpec faithfulness (incl. ambiguity attack), provenance sensitivity (oracle-vs-auto + error curve), and adapter-coverage residual sets are all reported — including where CapProof loses.

## 10.2 Expected main table (illustrative shape, not promised numbers)

```text
                         AuthLaunderBench (ASR ↓ / Secure-Utility ↑), by suite
Defense           Arg     Mem     Deleg   MCP     Skill   Endorse | AgentDojo ASR | Benign
Native            high    high    high    high    high    high    | high         | high
PromptArmor-style mid     high    high    mid     mid     high    | mid          | high
Task Shield       low     mid     mid     mid     mid     mid     | low          | high
CaMeL             low     mid     mid     mid     mid     mid     | low          | mid
PACT-auto         low*    high    high    mid     mid     high    | low          | mid
AUTHGRAPH-style   low*    mid     mid     mid     mid     mid     | low (strong) | mid
CLAWGUARD-style   low     mid     mid     low**   low**   mid     | low          | mid
PFI-style         mid     mid     low***  mid     mid     mid     | low          | mid
CapProof (full)   low*    low     low     low     low     low     | low (~parity)| within 10pts
```

`*` PACT/AUTHGRAPH/CaMeL/CapProof are all expected **strong (parity)** on the argument channel — we do *not* claim to dominate there; it is included to show no regression.
`**` CLAWGUARD explicitly targets MCP poisoning and skill injection, so it is expected **strong** on those suites — a co-winner, not a foil; the separation there is smaller.
`***` PFI's trusted/untrusted-agent separation is the closest defense on delegation and is the comparator to beat on Suite 3; CapProof's delegation *attenuation certificate* + per-cap agent binding is the claimed delta.
(Cells are qualitative placeholders, not promised numbers.)

The result that earns the paper is **the CapProof row being uniformly low across the laundering suites while each baseline has at least one suite where it structurally fails**, with the failure explained by the missing mechanism (no consumption → replay; no memory-strip → memory laundering; no delegation cert → delegation laundering; no one-shot → endorsement laundering; metadata-trust → metadata laundering).

## 10.3 Expected ablation outcome

Each removed mechanism should produce a localized ASR spike on its target suite while leaving other suites roughly unchanged — demonstrating that the mechanisms are *orthogonal and individually necessary*, not redundant. The two diagnostic ablations:

- **ProofObjectRemoved:** expected *no* security change; latency benefit concentrated on deep-derivation / delegation-chain actions. The size of that benefit decides whether "proof-carrying" stays in the title.
- **NoFaithfulnessConfirm:** expected over-broadening and ASR spike *only* under the ambiguity-exploit attack — showing §3.11 is the right (and necessary) mitigation for the elicitation layer.

## 10.4 Expected sensitivity behavior

- **Provenance:** ASR should degrade gracefully (roughly linearly) with injected provenance error; a cliff would indicate brittleness and must be reported.
- **Adapter coverage:** exposure should equal exactly the *unobserved* authority-bearing fields (validating **Characterization 1′**, §05.6, `TCB_AND_ADAPTER_COVERAGE.md`) — the controlled sweep that hides 1/2/3 fields should admit only effects expressible through those fields. The real-tool **residual sets** will likely show common gaps (bcc/headers/env/redirects) — a finding in itself, reported as sets, not a coverage probability.
- **Faithfulness:** high (≈ near-1) on explicit requests; the interesting, honestly-reported number is faithfulness under the ambiguity adversary with §3.11 on vs. off.

## 10.5 What a *negative* result looks like (and the plan for it)

This plan is engineered so that even a partial negative is publishable honestly:

- If CapProof only separates on memory + endorsement (not delegation/metadata), the contribution narrows to "authority persistence and approval laundering," still novel relative to CaMeL.
- If automatic provenance is weak, the paper becomes "an enforcement layer that is sound *given* provenance, plus a measurement of how good provenance must be" — a legitimate systems result.
- If the proof object adds nothing, the paper is "a capability-consuming reference monitor for authorization integrity" — still the core contribution, minus a buzzword.

We will not chase a clean win by hiding the dimensions where CapProof loses (exfiltration vs. CaMeL, dynamic-task endorsement burden, shell). Reviewers reward this; the original plan's "minimal success standard" omitted it.
