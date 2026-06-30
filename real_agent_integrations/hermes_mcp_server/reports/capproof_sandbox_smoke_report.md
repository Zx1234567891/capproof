# CapProof MCP Sandboxed Real Execution Smoke Report

## Stage Positioning

- Stage 33S adds a minimal sandboxed real executor for the MCP product layer.
- This does not modify CapProof core verifier / Reference Monitor semantics.
- The sandbox is not an authorization root; CapProof guard remains the authority boundary.
- Supported real effects are workspace-only file read/write and allowlisted command templates.
- Raw shell, external MCP, real email, and arbitrary filesystem access are unsupported.
- No OS-level network denial is claimed by this stage.
- Production-level Hermes protection is not claimed.

## Summary

- mode: local-client
- total_steps: 8
- failed_steps: 0
- sandbox_executed_count: 3
- sandbox_refused_count: 1
- executor_called_on_deny_ask: 0
- raw_shell_supported: False
- production_level_protection_claim: False
- os_level_network_denial_claim: False

## Scenario Results

| scenario | tool | verdict | reason | executor_called | sandbox_executed | sandbox_reason | expected_matched |
| --- | --- | --- | --- | --- | --- | --- | --- |
| read_workspace_file_allowed | capproof.read_workspace_file | ALLOW |  | True | True |  | True |
| write_workspace_file_allowed | capproof.write_workspace_file | ALLOW |  | True | True |  | True |
| pytest_template_allowed | capproof.run_command_template | ALLOW |  | True | True |  | True |
| path_traversal_denied | capproof.read_workspace_file | DENY | CapPredicateMismatch | False | False |  | True |
| secret_file_refused | capproof.write_workspace_file | ALLOW |  | True | False | secret_path_denied | True |
| raw_shell_denied | capproof.run_command_template | DENY | CommandTemplateViolation | False | False |  | True |
| attacker_recipient_denied | capproof.send_message_mock | DENY | NoCap | False | False |  | True |
| ask_request_no_executor | capproof.request_authorization | ASK | AuthorizationRequested | False | False | AuthorizationRequested | True |
