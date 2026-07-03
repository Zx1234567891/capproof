# Project Layout

The repository root is intentionally minimal. It keeps `README.md`, project
metadata, and build/test entry points; detailed Markdown artifacts live under
`docs/` or `artifact_reports/`. Executable maintenance and reproduction scripts
live under `tools/`.

## Main Directories

- `src/`: CapProof implementation code.
- `tests/`: pytest suites and regression checks.
- `tools/`: repository-level commands and staged reproduction harnesses.
- `bin/`: user-facing local command wrappers, including `hermes`.
- `docs/`: reviewer guides, release docs, status handoffs, quickstarts, and supporting documentation.
- `docs/release/`: final release manifest, claims, compatibility, evaluator, and reproduction documentation.
- `docs/status/`: implementation status, project layout, and handoff archives.
- `docs/design/`: design notes that are not part of the primary paper-planning sequence.
- `artifact_reports/`: generated release, evaluator, matrix, and reproduction reports.
- `real_agent_integrations/`: Hermes, OpenCode, and OpenClaw local MCP integration artifacts.
- `agent_coverage_audit/`, `adapter_bypass_gate/`, `authspec_faithfulness/`, `kill_tests/`: evaluation inputs and reports.
- `external/`, `artifact_cleanroom/`, `.venv-hermes/`, `node_modules/`: ignored local runtime or third-party state; these are not committed.

## Command Convention

Run repository tools from the root with an explicit `tools/` path:

```bash
python tools/run_capproof_mcp_server.py --list-tools
python tools/run_real_agent_parity_evaluator.py --preflight
python tools/run_final_release_check.py --preflight
```

Do not add new `run_*.py` files to the repository root. New executable
scripts should go in `tools/`, and user-facing wrappers should go in `bin/`.

## Claim Boundary

This layout change is organizational only. It does not expand CapProof's
claims, sandbox capabilities, MCP protocol support, or production protection
status.
