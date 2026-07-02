# Artifact Reproduction Report

## Summary

- passed: True
- default no secret: True
- default local only: True
- real Hermes run: False
- DeepSeek called: False
- real email: False
- real shell: False
- external MCP: False
- secret scan ok: True
- tracked forbidden paths: 0

## Commands

| command | returncode |
| --- | --- |
| `bin/hermes --doctor` | 0 |
| `bin/hermes --where-trace` | 0 |
| `python run_capproof_mcp_server.py --list-tools` | 0 |
| `python run_capproof_mcp_doctor.py --all` | 0 |
| `python run_capproof_trace_viewer.py --latest --last 5` | 0 |
| `python run_capproof_auth_queue.py doctor` | 0 |
| `python run_mcp_compatibility_matrix.py --report` | 0 |
| `pytest tests/test_mcp_compatibility_profile.py tests/test_claims_and_non_claims.py tests/test_install_local_hermes_wrapper_docs.py tests/test_artifact_reproduction_check.py -q` | 0 |

## Non-Claims

- No production-level Hermes protection.
- No all-Hermes-tool-paths-covered claim.
- No real email.
- No external MCP.
- No raw shell.
- No arbitrary filesystem access.
- No OS-level network-denial claim.
