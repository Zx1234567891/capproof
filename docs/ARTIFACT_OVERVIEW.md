# Artifact Overview

The CapProof Hermes MCP artifact packages a local standard MCP server, Hermes
foreground wrapper UX, trace viewer, doctor, trusted ASK queue, and reproduction
checks.

## Main Entry Points

- `bin/hermes`
- `tools/run_capproof_mcp_server.py`
- `tools/run_capproof_mcp_doctor.py`
- `tools/run_capproof_trace_viewer.py`
- `tools/run_capproof_auth_queue.py`
- `tools/run_mcp_compatibility_matrix.py`
- `tools/run_artifact_reproduction_check.py`

## Core Documents

- `docs/release/MCP_COMPATIBILITY.md`
- `docs/release/CLAIMS_AND_NON_CLAIMS.md`
- `docs/INSTALL_LOCAL_HERMES_WRAPPER.md`
- `docs/REPRODUCE_HERMES_CAPROOF_MCP.md`
- `docs/HERMES_CAPROOF_MCP_QUICKSTART.md`

## Reports

- `artifact_reports/mcp_compatibility_matrix.md`
- `artifact_reports/artifact_reproduction_report.md`
- `real_agent_integrations/hermes_mcp_server/reports/`

## Safety Boundary

The artifact is local, stdio MCP oriented, and evidence-driven. It does not
claim production-level Hermes protection, all tool path coverage, external MCP
protection, raw shell support, arbitrary filesystem access, or OS-level network
denial.
