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

## Running the Agent Profile Adapter Tests

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_agent_profile_adapters.py -q`: runs the Stage 17 mock profile adapter tests for OpenCode-like, OpenClaw-like, Hermes-agent-like, harness-native, and registry fail-closed event handling.
- These tests use mock event profiles only. They do not connect to real OpenCode, OpenClaw, Hermes, gateways, skills, MCP servers, email, network services, or shell execution.
- The profile adapter tests validate that workflow, skill, watcher, MCP, gateway, memory, delegation, and scheduled-action metadata cannot mint capabilities and that high-impact actions still enter Reference Monitor verification.

## Running the Agent Coverage Audit

- `python run_agent_coverage_audit.py`: runs the Stage 18 static, read-only adapter coverage audit and writes `agent_coverage_audit/` reports. Missing third-party repos are reported as `repo_missing`.
- `python run_agent_coverage_audit.py --opencode-repo external/opencode`: audits a local OpenCode checkout if present; it does not clone, install, build, or run OpenCode.
- `python run_agent_coverage_audit.py --openclaw-repo external/openclaw`: audits a local OpenClaw checkout if present; it does not clone, install, build, or run OpenClaw.
- `python run_agent_coverage_audit.py --hermes-repo external/hermes-agent`: audits a local Hermes Agent checkout if present; it does not clone, install, build, or run Hermes.
- `python run_agent_coverage_audit.py --hermes-repo external/external/hermes-agent`: audits the nested local Hermes checkout shape used in this workspace. Use whichever path matches the local checkout.
- Stage 19 local Hermes audit: the commands above perform static source reads only and regenerate `agent_coverage_audit/hermes_audit.md`, `coverage_matrix.json`, `coverage_matrix.md`, and `audit_summary.md`. In this workspace, the provided checkout unpacked at `external/external/hermes-agent`; the audit script resolves that local nested checkout when `external/hermes-agent` is absent. If neither path exists, Hermes remains `repo_missing`.
- The audit does not run Hermes, install dependencies, execute third-party commands, execute tools, connect to gateways/MCP servers, call network services, send email, or execute shell actions.
- Do not add `external/hermes-agent` or `external/external/hermes-agent` third-party source to the CapProof git repository; pass `--hermes-repo` to point at a local checkout.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_hermes_adapter_coverage.py -q`: runs the Stage 20 Hermes observed-shape mock coverage tests derived from the local static Hermes audit. These tests cover terminal, send_message, dynamic MCP, memory/provider-memory, delegate_task, cronjob, edit_file, and dispatcher effective-args shapes. They do not run Hermes, install dependencies, execute tools, connect to gateways/MCP servers, or perform network/shell/email side effects.
- `python run_hermes_dry_run.py`: runs the Stage 21 supported-subset Hermes dry-run over mock/replay JSON events and regenerates `hermes_dry_run_report.md` plus `hermes_dry_run/reports/summary.json`.
- `python run_hermes_dry_run.py --category supported`: runs only supported-subset dry-run cases.
- `python run_hermes_dry_run.py --category deny`: runs only explicit-deny dry-run cases.
- `python run_hermes_dry_run.py --category sanitized`: runs only sanitized / stripped allow memory cases.
- `python run_hermes_dry_run.py --category unknown`: runs only unknown/runtime-capture-needed fail-closed cases.
- `python run_hermes_dry_run.py --json`: prints the dry-run summary JSON to stdout in addition to writing reports.
- Stage 21 dry-run commands do not run Hermes, install dependencies, execute third-party project commands, execute real tools, connect to gateways/MCP servers, call network services, send email, or execute shell actions. They only replay mock JSON events through `HermesAgentLikeAdapter`, `CapProofMiddleware`, and `MockExecutor`.
- `python run_hermes_capture_validation.py`: runs the Stage 22 Hermes runtime capture schema replay validation over synthetic captured events and regenerates `hermes_capture_validation_report.md` plus `hermes_capture_examples/summary.json`.
- `pytest tests/test_hermes_capture_validation.py -q`: runs the Stage 22 capture validation unit tests.
- Stage 22 capture validation does not run Hermes, install dependencies, execute third-party project commands, execute real tools, connect to gateways/MCP servers, call network services, send email, or execute shell actions. It validates `pre_execution_gate` / `observer_only` / `unsupported` capture semantics over synthetic JSON only.
- `python run_hermes_capture_prototype.py --input hermes_capture_examples`: runs the Stage 23 capture prototype over Stage 22 wrapped synthetic examples.
- `python run_hermes_capture_prototype.py --input hermes_capture_prototype/input_examples`: runs the Stage 23 capture prototype over raw Hermes-like JSON captured-event examples.
- `python run_hermes_capture_prototype.py --jsonl hermes_capture_prototype/input_examples/events.jsonl`: runs the prototype over JSONL captured events.
- `python run_hermes_capture_prototype.py --report`: prints the latest prototype report, summary, and trace paths.
- `pytest tests/test_hermes_capture_prototype.py -q`: runs the Stage 23 capture prototype tests.
- Stage 23 capture prototype commands process only JSON / JSONL captured-event examples. They do not run Hermes, install dependencies, execute third-party project commands, execute real tools, connect to gateways/MCP servers, call network services, send email, or execute shell actions.

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

## Stage 33R - Real Hermes Sandboxed Standard MCP Smoke

Stage 33R validates real Hermes + DeepSeek against the standard CapProof MCP server with `--sandboxed-real-execution`. This is still a controlled local smoke, not production-level Hermes protection and not an OS-level network-denial claim.

Default safe commands:

```bash
python run_real_hermes_sandbox_mcp_smoke.py --preflight
python run_real_hermes_sandbox_mcp_smoke.py --list-scenarios
python run_real_hermes_sandbox_mcp_smoke.py --dry-run
```

Authorized real Hermes + DeepSeek command:

```bash
ALLOW_HERMES_DEEPSEEK_RUN=1 \
ALLOW_CAPROOF_MCP_REAL_HERMES=1 \
ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 \
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
python run_real_hermes_sandbox_mcp_smoke.py --all
```

Stage 33R validation commands:

```bash
pytest tests/test_real_hermes_sandbox_mcp_smoke.py -q
pytest tests/test_capproof_mcp_sandbox_policy.py -q
pytest tests/test_capproof_mcp_sandbox_paths.py -q
pytest tests/test_capproof_mcp_sandbox_file_read.py -q
pytest tests/test_capproof_mcp_sandbox_file_write.py -q
pytest tests/test_capproof_mcp_sandbox_commands.py -q
pytest tests/test_capproof_mcp_sandbox_env.py -q
pytest tests/test_real_hermes_standard_mcp_smoke.py -q
pytest tests/test_hermes_mcp_coverage.py -q
pytest tests/test_capproof_mcp_protocol.py -q
pytest tests/test_capproof_mcp_guard_path.py -q
pytest tests/test_capproof_mcp_trace.py -q
pytest tests/test_capproof_mcp_ask_flow.py -q
pytest tests/test_capproof_mcp_metadata_injection.py -q
python run_kill_tests.py --mode all --baselines
python run_adapter_bypass_gate.py
python run_authspec_faithfulness.py --mode auto
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
python -m compileall src tests run_real_hermes_sandbox_mcp_smoke.py run_capproof_sandbox_smoke.py
```

Stage 33R claims and boundaries:

- Real Hermes and DeepSeek were used only in the explicitly authorized `--all` run.
- The MCP server was the standard CapProof MCP server with `--sandboxed-real-execution`, not the old proxy.
- ALLOWed sandbox effects are limited to workspace file read/write and allowlisted command templates.
- DENY/ASK do not execute an executor.
- Raw shell remains unsupported and denied.
- No real email, external MCP, arbitrary filesystem access, or production wrapper is claimed.
- No API key is written to files, reports, traces, logs, or commits.

## Stage 34O - OpenCode/OpenClaw CapProof MCP Reuse Audit and Dry-Run Config

Stage 34O validates CapProof MCP reuse for OpenCode/OpenClaw through static repo/runtime audit, config templates, command documentation, and a local JSON-RPC dry-run against the same standard CapProof MCP server. It does not run real OpenCode/OpenClaw and does not claim real OpenCode/OpenClaw integration.

Commands:

```bash
python run_agent_mcp_client_audit.py --all
python run_agent_mcp_client_audit.py --report
python run_capproof_mcp_server.py --list-tools
python run_capproof_mcp_server.py --self-test
python run_capproof_sandbox_smoke.py --local-client --scenario all
pytest tests/test_agent_mcp_client_audit.py -q
pytest tests/test_opencode_mcp_config.py -q
pytest tests/test_openclaw_mcp_config.py -q
pytest tests/test_real_hermes_sandbox_mcp_smoke.py -q
pytest tests/test_capproof_mcp_sandbox_policy.py -q
pytest tests/test_capproof_mcp_sandbox_paths.py -q
pytest tests/test_capproof_mcp_sandbox_file_read.py -q
pytest tests/test_capproof_mcp_sandbox_file_write.py -q
pytest tests/test_capproof_mcp_sandbox_commands.py -q
pytest tests/test_capproof_mcp_sandbox_env.py -q
python run_kill_tests.py --mode all --baselines
python run_adapter_bypass_gate.py
python run_authspec_faithfulness.py --mode auto
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
python -m compileall src tests run_agent_mcp_client_audit.py
```

Stage 34O boundaries:

- OpenCode/OpenClaw were not run.
- No real OpenCode/OpenClaw `tools/list` or `tools/call` observation is claimed.
- The generated configs reuse `run_capproof_mcp_server.py --stdio --sandboxed-real-execution`.
- CapProof guard / Reference Monitor logic is not forked.
- MCP metadata, OpenCode/OpenClaw tool metadata, plugin/skill metadata, and LLM output cannot mint capability.
- DENY/ASK executor_called remains false in the local JSON-RPC dry-run.
- No API key, token, or secret is written.
- No production-level protection claim is made.
