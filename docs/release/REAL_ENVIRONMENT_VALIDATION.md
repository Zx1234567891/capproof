# Real Environment Validation Policy

Stage 38REAL makes real-environment validation the completion standard for
future CapProof Hermes MCP stages. Dry-run and preflight are safety readiness
steps only. They are not completion evidence.

## Real Environment Definition

A real environment validation must use:

- The real local repository.
- The real `bin/hermes` wrapper.
- A real Hermes foreground agent process.
- A real DeepSeek backend call through `DEEPSEEK_API_KEY` from the environment.
- The real standard CapProof MCP stdio server.
- Real MCP `tools/list`.
- Real MCP `tools/call`.
- Real sandbox workspace file read/write.
- Real allowlisted command-template subprocess execution.
- The real trusted ASK approval CLI.
- Real trace, live log, and report artifacts.

## Completion Rule

Preflight, dry-run, local JSON-RPC clients, and local-only smoke tests are
safety readiness checks. They cannot mark a stage complete when the stage
requires real environment validation.

If a required gate is missing, the result must be
`blocked_missing_real_env_gate`. It must not be reported as passed.

Future features that touch Hermes, MCP, sandbox execution, trace semantics, or
ASK authorization must add a real-environment scenario before that stage can be
completed.

## Required Real Run Gates

All real environment validation runs require:

```text
ALLOW_HERMES_DEEPSEEK_RUN=1
ALLOW_CAPROOF_MCP_REAL_HERMES=1
ALLOW_CAPROOF_HERMES_FOREGROUND_DEMO=1
ALLOW_CAPROOF_SANDBOX_REAL_EXECUTION=1
ALLOW_CAPROOF_ASK_APPROVAL_DEMO=1
ALLOW_CAPROOF_REAL_ENV_VALIDATION=1
DEEPSEEK_API_KEY from environment
```

## Prohibited Real Effects

Real environment validation must not use or claim:

- Real email.
- Raw shell.
- External MCP.
- Arbitrary filesystem access.
- Non-DeepSeek external network.
- Production wrapper protection.
- OS-level network denial unless implemented and tested with an isolation
  mechanism such as a network namespace or equivalent.

## Safety Boundary

The sandbox is not an authorization root. Authorization remains with
CapProof guard and the Reference Monitor. ASK does not automatically mint
capability. Only trusted local CLI approval can mint exact scoped capability.
DeepSeek remains outside the CapProof safety TCB.
