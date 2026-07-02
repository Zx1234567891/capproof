# Reproduce Hermes + CapProof MCP Artifact

This guide gives reviewer-safe commands for the local artifact. Default checks
do not call DeepSeek, do not run real Hermes, do not send email, do not use
external MCP, and do not run raw shell.

## No-Secret Default Checks

```bash
python run_artifact_reproduction_check.py --no-secret --local-only --report
make capproof-doctor
make capproof-trace
make capproof-auth-queue
make capproof-smoke-local
```

These commands check local MCP tools, doctor output, trace viewer, auth queue
health, compatibility matrix generation, secret scan, and local smoke paths.

## Local Smoke Checks

```bash
python run_capproof_mcp_server.py --list-tools
python run_capproof_mcp_server.py --self-test
python run_capproof_sandbox_smoke.py --local-client --scenario all
python run_capproof_trace_viewer.py --latest --last 5
python run_capproof_auth_queue.py doctor
```

## Gated Real Hermes Checks

Real Hermes + DeepSeek checks require explicit gates:

```bash
ALLOW_HERMES_DEEPSEEK_RUN=1 \
ALLOW_CAPROOF_MCP_REAL_HERMES=1 \
ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO=1 \
ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1 \
ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1 \
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
python run_real_hermes_foreground_ask_flow.py --all --foreground
```

Do not write `DEEPSEEK_API_KEY` into any file. Keep it in the environment only.

## Report and Trace Paths

- Foreground UX report:
  `real_agent_integrations/hermes_mcp_server/reports/foreground_ux_report.md`
- Foreground ASK report:
  `real_agent_integrations/hermes_mcp_server/reports/foreground_ask_flow_report.md`
- Foreground ASK trace:
  `real_agent_integrations/hermes_mcp_server/traces/foreground_ask_flow_trace.jsonl`
- Compatibility matrix:
  `artifact_reports/mcp_compatibility_matrix.md`
- Artifact reproduction report:
  `artifact_reports/artifact_reproduction_report.md`

## Inspect Trace Viewer

```bash
python run_capproof_trace_viewer.py --latest --last 20
python run_capproof_trace_viewer.py --latest --format json --last 5
python run_capproof_trace_viewer.py --latest --filter-verdict DENY
```

## Inspect ASK Queue

```bash
python run_capproof_auth_queue.py doctor
python run_capproof_auth_queue.py list
python run_capproof_auth_queue.py show AUTHREQ_ID
python run_capproof_auth_queue.py audit AUTHREQ_ID
```

## What These Results Prove

- Standard local stdio MCP `tools/list` and `tools/call` work for the CapProof
  tool set.
- CapProof guard gates authority-bearing tool calls.
- DENY and ASK do not execute.
- Trusted local CLI approval can mint exact scoped capability for ASK flows.
- Trace viewer and doctor expose reviewer-visible evidence.

## What These Results Do Not Prove

- Production-level Hermes protection.
- All Hermes tool paths covered.
- All MCP clients covered.
- Real email protection.
- External MCP protection.
- Raw shell support.
- Arbitrary filesystem access.
- OS-level network denial.
- OpenCode/OpenClaw real integration.
