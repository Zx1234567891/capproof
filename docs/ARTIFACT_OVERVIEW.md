# Artifact Overview

The CapProof Hermes MCP artifact packages a local standard MCP server, Hermes
foreground wrapper UX, trace viewer, doctor, trusted ASK queue, and reproduction
checks.

## Main Entry Points

- `bin/hermes`
- `run_capproof_mcp_server.py`
- `run_capproof_mcp_doctor.py`
- `run_capproof_trace_viewer.py`
- `run_capproof_auth_queue.py`
- `run_mcp_compatibility_matrix.py`
- `run_artifact_reproduction_check.py`

## Core Documents

- `MCP_COMPATIBILITY.md`
- `CLAIMS_AND_NON_CLAIMS.md`
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
