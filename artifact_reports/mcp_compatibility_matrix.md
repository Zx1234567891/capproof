# MCP Compatibility Matrix

## Summary

- profile: CapProof local stdio MCP compatibility profile
- tools count: 7
- supported: 12
- partial: 1
- not claimed: 9
- production-level protection claim: false

## Matrix

| feature | status | evidence | test command | notes |
| --- | --- | --- | --- | --- |
| local stdio MCP server | supported | tools/run_capproof_mcp_server.py --stdio | `python tools/run_capproof_mcp_server.py --list-tools` | Local process stdio only. |
| initialize | supported | stdio server handles JSON-RPC initialize | `tests/test_capproof_mcp_protocol.py -q` | Used by Hermes standard MCP smoke. |
| tools/list | supported | 7 CapProof tools observed | `python tools/run_capproof_mcp_server.py --list-tools` | Also observed in real Hermes smoke. |
| tools/call | supported | standard CapProof MCP call path | `python tools/run_capproof_mcp_server.py --self-test` | Authority-bearing tools enter guard path. |
| structuredContent | supported | tool responses include structuredContent | `tests/test_capproof_mcp_protocol.py -q` | Includes verdict, proof, trace, executor_called. |
| JSON-RPC stdio cleanliness | supported | stdout reserved for JSON-RPC | `tests/test_capproof_mcp_doctor.py -q` | Human logs go to stderr/live log/report/trace. |
| capproof.echo_summary | supported | tools/list exposes tool | `python tools/run_capproof_mcp_server.py --list-tools` | No authority-bearing side effect. |
| capproof.send_message_mock | supported | ALLOW/DENY paths tested | `python tools/run_capproof_mcp_server.py --self-test` | Mock only, no real email. |
| capproof.read_workspace_file | supported | workspace sandbox tests | `tests/test_capproof_mcp_sandbox_file_read.py -q` | Workspace-only subset. |
| capproof.write_workspace_file | supported | atomic write sandbox tests | `tests/test_capproof_mcp_sandbox_file_write.py -q` | Workspace-only subset. |
| capproof.run_command_template | partial | allowlisted command templates | `tests/test_capproof_mcp_sandbox_commands.py -q` | No raw shell support. |
| capproof.get_trace | supported | trace viewer and MCP trace tool | `tests/test_capproof_mcp_trace.py -q` | Local trace only. |
| capproof.request_authorization | supported | trusted ASK queue | `tests/test_capproof_mcp_ask_approval_flow.py -q` | ASK does not auto-mint capability. |
| resources | not_claimed | not implemented | `none` | No MCP resources claim. |
| prompts | not_claimed | not implemented | `none` | No MCP prompts claim. |
| sampling | not_claimed | not implemented | `none` | No MCP sampling claim. |
| elicitation | not_claimed | not implemented | `none` | No MCP elicitation claim. |
| Streamable HTTP | not_claimed | not implemented | `none` | Only local stdio is claimed. |
| OAuth / remote MCP authorization | not_claimed | not implemented | `none` | Trusted local CLI approval only. |
| external MCP server protection | not_claimed | not implemented | `none` | No external MCP claim. |
| all MCP transports | not_claimed | not implemented | `none` | Only local stdio subset. |
| all future/draft MCP versions | not_claimed | not implemented | `none` | Evidence is tied to current local profile. |

## Non-Claims

- resources
- prompts
- sampling
- elicitation
- Streamable HTTP
- OAuth / remote MCP authorization
- external MCP server protection
- all MCP transports
- all future/draft MCP versions
