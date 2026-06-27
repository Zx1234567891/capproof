# TOP_10_ACTION_ITEMS

Prioritized for the current version. Validate the thesis cheaply, close the PCAA-proximity risk, then scale.

### 1. Run the kill test (`KILL_TEST_PLAN.md`) — before anything else
Stand up real **CaMeL** (original or faithful, tuned — not strawmanned), **PACT-style**, **AUTHGRAPH-style** (clean graph + tool + parameter-source alignment, no consumption/memory/delegation), **CLAWGUARD-style** (boundary + approval, approval not a one-shot capability), Native; run the 12 cross-boundary tasks (`KILLER_EXAMPLES.md`) in both AuthSpec modes; check the go/no-go (CaMeL-behavior scenarios).
**Why first:** it validates the irreplaceable-value thesis or tells us to pivot (§5) before months of benchmark work. It is Figure 1.

### 2. Close the PCAA-proximity risk in the writing (§12.4, §00)
PCAA owns proof-carrying. Lead with consumption + authority-provenance calculus + cross-boundary mechanisms; frame complementarity (CapProof can emit PCAA-style receipts); pre-commit to dropping the proof framing via `ProofObjectRemoved`.

### 3. Build the TCB core with two-phase consumption, prove concurrency-safe (`TCB_AND_ADAPTER_COVERAGE.md`)
Core Verifier < 1,500 LoC; Minting + Verifier + Store < 5,000 LoC; adapters counted separately. Property-test: no double-spend under concurrency; **false-allow = 0** on the mechanism suite.

### 4. Implement the four cross-boundary mechanisms (§03)
Memory-authority stripping, delegation certificates (+ agent PKI), one-shot canonical-bound endorsement, and the `binding_status` discipline. These are what the ablations must show are *necessary* and what the kill test must show comparators lack.

### 5. Run `ProofObjectRemoved` (§09.4) early to decide the title
6 axes: security (expect unchanged), latency (deep vs shallow), explainability, failure localization, auditability, replayability. If no benefit, rename around "capability-consuming reference monitor" and cite PCAA for the certificate layer.

### 6. Build AuthLaunderBench (§07) with observable-side-effect oracles + threat sourcing
6 suites × 25, oracles on observable effects only, `ground_truth_authspec` for internal scoring only, `threat_source` per task. Populate from `KILLER_EXAMPLES.md` first.

### 7. Integrate baselines on a shared harness with the reproduction policy (§09.1)
CaMeL (orig/faithful, calibrated), PACT-oracle/auto, AUTHGRAPH-style, CLAWGUARD-style, PFI-style, Task Shield, PromptArmor-style, CapProof-oracle/auto — each labeled Original / faithful reimpl (calibrated on the source benchmark subset) / representative. Never claim to beat a representative-only system.

### 8. Measure the three assumption-grounding quantities
(a) AuthSpec faithfulness incl. ambiguity adversary, §3.11 ON/OFF (`AUTHSPEC_FAITHFULNESS_GATE.md`); (b) provenance sensitivity oracle-vs-auto + error-injection curve (§08); (c) adapter **residual sets** + the five coverage metrics on real MCP tools (`TCB_AND_ADAPTER_COVERAGE.md`).

### 9. Run the canonicalization/adapter bypass gate (`CANONICALIZATION_BYPASS_GATE.md`) and the full matrix with statistics
≥30 per-vector tests (bcc/cc/reply_to/headers/attachments/traversal/symlink/case/Unicode/punycode/redirect/encoded/query-smuggling/cwd/env/stdin/sh-c/base64) + the full defense×suite×variant matrix across ≥3 backbones with Wilson CIs, McNemar, paired bootstrap, Holm.

### 10. Harden and release the artifact
Docker, mock/sandboxed tools, sandboxed shell with the CommandTemplate allowlist, published traces/oracles/proof-DAGs, finalized `prior_work.bib`. Target AE badges.

---

**If you can only do three:** #1 (kill test — is there a paper?), #2 (PCAA repositioning — is the framing correct?), #8 (faithfulness + residual + provenance — is the soundness story honest?). Those decide existence, framing, and integrity; the rest is scaling a validated thesis.
