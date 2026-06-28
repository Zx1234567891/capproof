# Baseline Reproduction Notes

These notes are part of the artifact contract for Stages 12-13. The harness intentionally avoids strawman claims: original-system wins/losses are not asserted unless the row is backed by original code or a calibrated faithful reproduction.

## Running the Harness

- `python run_kill_tests.py --mode attack`: runs the 12 attack cases and regenerates `kill_test_report.md` with attack success, unsafe side-effect count, and deny-reason distribution.
- `python run_kill_tests.py --mode benign`: runs the 12 benign counterparts and regenerates `kill_test_report.md` plus `benign_kill_test_report.md` with benign success, overblock, ASK, proof coverage, and endorsement counts.
- `python run_kill_tests.py --mode all`: runs both attack and benign cases and regenerates `kill_test_report.md` plus `benign_kill_test_report.md` for the combined kill-test harness.
- `python run_kill_tests.py --mode all --baselines`: runs the combined harness with representative baselines and regenerates `baseline_report.md` plus this `reproduction_notes.md`.
- These reports are valid for the current 12-task kill-test harness only; they must not be extrapolated to a complete benchmark or original-system comparison without calibration.

## Running the AuthSpec Faithfulness Gate

- `python run_authspec_faithfulness.py --mode oracle`: generates the 50-case AuthSpec Faithfulness corpus in Oracle-AuthSpec Mode, where `G_sys = G*`, and writes oracle generated specs, evaluations, summaries, and `authspec_faithfulness_report.md`.
- `python run_authspec_faithfulness.py --mode auto`: runs the representative rule-based AuthSpec Builder in Deployed-AuthSpec Mode, compares generated `G_sys` against ground-truth `G*`, and writes generated specs, per-case evaluations, aggregate metrics, and `authspec_faithfulness_report.md`.
- `python run_authspec_faithfulness.py --report`: regenerates `authspec_faithfulness_report.md` from the latest saved AuthSpec Faithfulness results without running a new builder pass.
- AuthSpec Faithfulness results are a 50-case gate for `G_sys` versus `G*`; they are not a complete benchmark and do not establish deployability for automatic AuthSpec generation.

## Running the Adapter Bypass Gate

- `python run_adapter_bypass_gate.py`: runs the adapter/canonicalization bypass gate with mock actions only, regenerates `adapter_bypass_gate/` artifacts, and writes `adapter_bypass_gate_report.md`.
- This gate does not send email, perform network I/O, execute shell commands, or use LLMs. It checks adapter field coverage and canonicalization behavior before any real executor.

## Running the Agent Adapter Tests

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_agent_adapter.py -q`: runs the Stage 16 mock agent adapter tests for LangGraph-like, OpenAI tool-calling-like, and coding-agent-like event formats.
- These tests use `CapProofMiddleware` and `MockExecutor` only. They do not connect to real OpenCode, Claude Code, Codex, LangGraph, OpenAI APIs, MCP servers, email, network services, or shell execution.
- The adapter tests validate that raw events are converted into CapProof canonical actions, proof synthesis is re-verified by the Reference Monitor, and `DENY`/`ASK` decisions do not call the mock executor.

Adaptive mode is not implemented in Stage 13. Future adaptive runs should preserve the same task-local observable oracles while varying attack payloads after structured denials.

## Fairness Rules

- Every baseline uses the same 12 attack tasks, the same 12 benign counterparts, and the same task-local oracle for each mode.
- Every baseline returns `ALLOW`, `DENY`, or `ASK`, plus the executed action when it allows.
- `ASK` is treated as no unsafe side effect, but counted separately as `ask_rate`; it is not automatically treated as a completed benign task.
- Representative baselines are labeled as such and are not claims about original system performance.
- CaMeL and CLAWGUARD are treated as strong comparators, not weak strawmen.

## Baselines

### native: Native ReAct-style no-defense

- Reproduction tier: native baseline
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Executes the proposed unsafe action with no authorization monitor.
- Fairness note: This is intentionally the no-defense lower bound, not a security baseline.
- Assumptions:
  - No tool boundary.
  - No provenance tracking.
  - No approval consumption.

### pact_oracle: PACT-style oracle

- Reproduction tier: faithful oracle-style reimplementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Perfect argument provenance labels and policy oracle over authority-bearing fields.
- Fairness note: This is deliberately stronger than an automatic implementation; it should not be compared as deployed PACT without the oracle label.
- Assumptions:
  - Authority-bearing recipient/path/endpoint/content fields are surfaced by the adapter.
  - Oracle provenance knows whether a parameter came from untrusted content, memory, metadata, or delegation.

### pact_auto: PACT-style auto

- Reproduction tier: representative implementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Heuristic automatic provenance over declared authority-bearing action parameters.
- Fairness note: Representative only; no claim is made about original PACT results without calibration.
- Assumptions:
  - Current-turn argument sources are usually visible.
  - Cross-turn memory and approval state are not reliably reconstructed.

### authgraph: AUTHGRAPH-style

- Reproduction tier: representative implementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Clean authorization graph plus parameter-source alignment checks.
- Fairness note: Strong on parameter/source mismatch; weaker claims on consumable approval state and exact delegation attenuation.
- Assumptions:
  - The clean graph contains the expected authorized recipients, endpoints, file paths, and agent edges.
  - Injected parameter-source edges are observable.
- Required Stage 12 coverage: clean authorization graph and parameter-source alignment are represented explicitly.

### clawguard: CLAWGUARD-style

- Reproduction tier: representative implementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Tool/file/network boundary with approval prompts for high-impact or ambiguous operations.
- Fairness note: Treated as a strong MCP/skill defense; CapProof does not claim raw ASR dominance on those tasks from this representative harness.
- Assumptions:
  - MCP and skill metadata are treated as untrusted at the tool boundary.
  - External network/file/email side effects can be denied or routed to approval.
  - Approval is a boundary gate, not a one-shot scoped capability.
- Required Stage 12 coverage: tool/file/network boundary and approval are represented explicitly; this is still not the original CLAWGUARD implementation.

### camel_faithful_subset: CaMeL faithful-subset

- Reproduction tier: faithful-subset / not original
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: P-LLM/Q-LLM-style value data-flow policy for untrusted data reaching authority-bearing or egress arguments.
- Fairness note: No claim of beating original CaMeL. Results are only a faithful-subset smoke test until calibrated against a CaMeL benchmark subset.
- Assumptions:
  - Value provenance is available for arguments and data egress.
  - This harness does not reproduce the original CaMeL interpreter or policy engine.
  - Cross-agent authority transfer and one-shot approval spend state are outside this subset.
- Required Stage 12 limitation: original CaMeL is not reproduced here; this is a faithful-subset value-flow baseline and cannot support claims of beating original CaMeL.

### promptarmor: PromptArmor-style

- Reproduction tier: auxiliary representative implementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Prompt/payload pattern filtering before action construction.
- Fairness note: Auxiliary baseline only; not used for primary claims.
- Assumptions:
  - Obvious attack strings may be stripped.
  - Dormant memory and approval replay are not modeled.

### task_shield: Task Shield-style

- Reproduction tier: auxiliary representative implementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Task/action alignment checks over the proposed action type and target.
- Fairness note: Auxiliary baseline only; alignment is not authorization.
- Assumptions:
  - On-task but unauthorized actions may pass.

### pfi: PFI-style

- Reproduction tier: auxiliary representative implementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Trusted/untrusted agent-flow policy for privilege escalation.
- Fairness note: Closest auxiliary comparator for delegation; representative until calibrated.
- Assumptions:
  - Agent boundaries are labeled.
  - Fine-grained per-argument capability consumption is not modeled.

### drift: DRIFT-style

- Reproduction tier: auxiliary representative implementation
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Memory isolation preventing memory entries from becoming authority roots.
- Fairness note: Strong memory specialist baseline; not expected to cover delegation/endorsement.
- Assumptions:
  - Memory reads preserve isolation labels.
  - Non-memory laundering channels are out of scope.

### agentarmor_subset: AgentArmor-related subset

- Reproduction tier: auxiliary representative subset
- Has original code in this harness: False
- Calibrated on original benchmark subset: False
- Implementation basis: Trace-dependency checks for authority-bearing arguments.
- Fairness note: Related-work subset only; not a full AgentArmor reproduction.
- Assumptions:
  - Relevant dependencies are visible in the trace.
  - Approval consumption is not modeled.
