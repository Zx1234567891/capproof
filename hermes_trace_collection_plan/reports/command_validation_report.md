# Hermes Capture Command Validation Report

- Verdict: DENY_CAPTURE_RUN
- Reason: missing required capture-run environment variables
- Missing env: ALLOW_HERMES_CAPTURE_RUN, HERMES_CAPTURE_COMMAND, HERMES_CAPTURE_TRACE_PATH, CAPPROOF_CAPTURE_ONLY, CAPPROOF_NO_REAL_TOOLS, NO_NETWORK, HERMES_TEST_WORKSPACE
- Denied patterns: none
- Command preview: `none`

## Required Checks

- allow_env: False
- command_present: False
- trace_path_env: False
- capture_only_env: False
- no_real_tools_env: False
- no_network_env: False
- test_workspace_env: False
- timeout_present: False
- trace_output_present: False
- mock_tool_mode: False
- no_real_shell_flag: False
