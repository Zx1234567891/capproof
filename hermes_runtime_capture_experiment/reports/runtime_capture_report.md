# Hermes Runtime Capture Experiment Report

## Stage Position

Stage 25 is a capture-only runtime experiment. It is not an enforcement wrapper,
not a real integration claim, and not a claim that CapProof protects real Hermes.
Default preflight does not run Hermes, install dependencies, execute third-party commands,
execute real tools, use network, send messages/email, or modify Hermes source.

Capture-run remains denied unless `ALLOW_HERMES_CAPTURE_RUN=1`, `HERMES_CAPTURE_COMMAND`,
`HERMES_CAPTURE_TRACE_PATH`, `CAPPROOF_CAPTURE_ONLY=1`, `CAPPROOF_NO_REAL_TOOLS=1`,
`NO_NETWORK=1`, and `HERMES_TEST_WORKSPACE` are all set and the command passes
capture-only safety checks. Only captured JSONL traces are
trusted for validation; natural-language logs are not authorization evidence.

## Preflight Summary

- Repo path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/external/hermes-agent`
- Repo status: available
- Files scanned: 2000
- No command executed: True
- Existing trace: none
- Capture-run allowed: False
- Reason: default no-run preflight: explicit capture-run authorization not provided

## Potential Hook Points

| Hook | Candidate hits | Sample files |
| --- | ---: | --- |
| tool_dispatcher | 450 | AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, SECURITY.md, batch_runner.py |
| terminal | 1173 | .hadolint.yaml, AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, README.es.md |
| mcp | 855 | AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, README.es.md, README.md |
| memory | 552 | AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, README.es.md, README.md |
| gateway | 1151 | AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, README.es.md, README.md |
| delegation | 286 | AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, README.es.md, README.md |
| scheduler | 448 | AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, README.es.md, README.md |
| middleware_rewrite | 953 | .hadolint.yaml, AGENTS.md, CONTRIBUTING.es.md, CONTRIBUTING.md, README.es.md |

## Capture Run Summary

- Run attempted: False
- State: not_run
- Reason: capture run not requested
- Command hash: n/a
- Timeout seconds: 20
- Trace path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/hermes_capture_run/traces/captured_events.jsonl`
- Events captured: 0
- No real tool assertion: False

## Trace Validation Summary

- Total events: 0
- Schema-valid events: 0
- Pre-execution-gate events: 0
- Observer-only events: 0
- Unsupported events: 0
- Missing-field events: 0
- Allowed: 0
- Denied: 0
- Ask: 0
- AdapterCoverageGap count: 0
- Observer-only blocked count: 0
- Executor called on deny: 0
- Executor called on ask: 0

## Hook Completeness

| Hook | Observed | Complete fields | Enforcement-ready | Missing fields |
| --- | --- | --- | --- | --- |
| tool_dispatcher | unknown | unknown | no | none |
| terminal | unknown | unknown | no | none |
| mcp | unknown | unknown | no | none |
| memory | unknown | unknown | no | none |
| gateway | unknown | unknown | no | none |
| delegation | unknown | unknown | no | none |
| scheduler | unknown | unknown | no | none |
| middleware_rewrite | unknown | unknown | no | none |

## Go / No-Go

- Enforcement wrapper: no-go.
- Real Hermes integration claim: no.
- Runtime capture experiment completed: yes, limited to no-run preflight and any supplied offline trace validation.
- Next step: obtain or generate safe capture-only runtime traces, then verify pre-execution hook placement and field completeness.
