# Hermes Runtime Event Capture Design

Stage 22 defines a runtime capture schema and replay validation layer for future
Hermes integration. It is not a real Hermes integration. This stage does not run
Hermes, install dependencies, execute third-party commands, modify Hermes
source, execute tools, call network services, send messages, or run shell
commands.

The capture layer is outside the core verifier API. It translates captured
runtime events into existing Hermes-like mock adapter events, then
`CapProofMiddleware` and the Reference Monitor remain the final allow / deny
boundary.

## Capture Modes

| Mode | Meaning | Enforcement claim |
| --- | --- | --- |
| `pre_execution_gate` | Event is captured before the tool/backend side effect. CapProof can block before execution. | Eligible for future enforcement claim if all authority-bearing fields are present. |
| `observer_only` | Event is observed after or outside the execution path. | Audit only. It cannot support an ALLOW enforcement claim. |
| `unsupported` | Hook or fields are incomplete or not modeled. | Must fail closed or stay out of the supported subset. |

## Hook Point Taxonomy

| Hook point | Required fields | Capture mode | Authority-bearing fields | Can CapProof enforce? |
| --- | --- | --- | --- | --- |
| Tool dispatcher pre-call | `tool_name`, `original_args`, `effective_args`, session metadata | `pre_execution_gate` | effective tool args, rewritten fields, session metadata that changes routing | Yes, only when effective args are complete and captured before dispatch. |
| Terminal backend pre-exec | `command`, `args` if available, `cwd`, `env`, `stdin`, terminal backend | `pre_execution_gate` | command/template, args, cwd, env, stdin | Yes for allowlisted templates. Arbitrary shell is unsupported/denied. |
| MCP pre-transport | `server`, `tool_name`, `arguments`, transport endpoint, headers, body | `pre_execution_gate` | server, tool, URL, transport endpoint, headers, body ref | Yes when endpoint and transport fields are complete. MCP metadata cannot mint capability. |
| Memory pre-write | `content`, `origin`, `persistence`, authority claims if present | `pre_execution_gate` | content, origin, persistence, authority-like claims | Yes for content-only writes after Memory Authority Stripping. Authority is not accepted. |
| Gateway / messaging pre-send | `platform`, `channel`, `recipient`, body, attachments, headers | `pre_execution_gate` | recipient/channel/platform, attachments, headers | Yes when recipient and routing fields are complete. |
| Subagent / delegation pre-dispatch | `parent_agent`, `child_agent`, delegated scope or cert ref, goal, toolsets | `pre_execution_gate` | parent, child, delegated scope, requested action | Yes only with Delegation Certificate and attenuation. |
| Scheduler / cron pre-register | `schedule_id`, recurrence, action target, recipient/endpoint/command, workdir | `pre_execution_gate` | schedule id, recurrence, recipient/endpoint/command, workdir | Yes when registration is capability-scoped. |
| Scheduler / cron pre-fire | `schedule_id`, action target, recipient/endpoint/command, workdir | `pre_execution_gate` | schedule id, recipient/endpoint/command, workdir | Yes when execution remains bound to schedule and task scope. |
| Skill / plugin middleware rewrite | `original_args`, `effective_args`, middleware source | `pre_execution_gate` | effective args, rewritten recipient/endpoint/path/command | Yes using effective args only. Metadata cannot mint capability. |

## Validation Rules

- Terminal events must include `command`, `cwd`, `env`, and `stdin`. `stdin`
  may be null, but the field must be present.
- Gateway events must include `platform`, `recipient`, and `body`.
- MCP events must include `server`, `tool_name`, `arguments`, and
  `transport.endpoint`.
- Memory events must include `content`, `origin`, and `persistent`.
- Delegation events must include `parent_agent`, `child_agent`, and either
  delegated scope or certificate reference.
- Cron events must include `schedule_id` and a concrete action target such as
  recipient, endpoint, command, or script.
- Middleware rewrite events must include both `original_args` and
  `effective_args`; authorization uses `effective_args`.

If required fields are missing, a `pre_execution_gate` event is denied with
`AdapterCoverageGap`. `observer_only` events are blocked from enforcement ALLOW.
`unsupported` shapes fail closed.

## Remaining Runtime Requirements

Before real Hermes integration, Hermes runtime must provide pre-execution hooks
for terminal, MCP, memory, gateway, delegation, scheduler, and middleware
rewrite surfaces. Runtime samples must confirm exact field names, whether hooks
are pre-side-effect, and whether all authority-bearing fields are visible before
execution. Until then, CapProof can only claim capture schema and replay
validation for synthetic events.

## Stage 24 Capture-only Instrumentation Prototype

Stage 24 adds capture-only hook wrappers and a fixture/trace runner. This is
still not a real Hermes integration and not an enforcement wrapper. Hermes is
not run, dependencies are not installed, third-party project commands are not
executed, real tools are not called, network is not used, and shell commands are
not executed.

The wrappers only construct `HermesRuntimeEvent` values:

- `ToolDispatcherCapture` records tool dispatcher pre-call arguments.
- `TerminalCapture` records terminal command, cwd, env, stdin, and backend
  without executing the command.
- `MCPCapture` records MCP server/tool/arguments/transport endpoint/headers
  without opening a transport.
- `MemoryCapture` records memory content/origin/persistence/authority-like
  claims before Memory Authority Stripping.
- `GatewayCapture` records platform, recipient/target/channel, body,
  attachments, and headers before sending.
- `DelegationCapture` records parent/child agent, goal, scope/cert, and
  toolsets before subagent dispatch.
- `SchedulerCapture` records schedule id, recurrence, and action targets before
  scheduler registration or fire.
- `MiddlewareRewriteCapture` records original/effective args and middleware
  source. Authorization must use effective args.

`tools/run_hermes_capture_instrumentation.py` reads fixture or trace JSON/JSONL,
writes a JSONL trace, and then replays the captured events offline through the
existing capture validation bridge and CapProof guard dry-run. Capture and
replay are intentionally separate. `pre_execution_gate` events are eligible for
offline guard dry-run when complete; `observer_only` events remain audit-only;
unsupported or missing-field events fail closed with `AdapterCoverageGap`.

The Stage 24 fixture set validates hook shape readiness only. A future real
Hermes runtime capture experiment must still confirm that these hook points
exist in the runtime, fire before side effects, and expose the required
authority-bearing fields.
