# Hermes DeepSeek Setup Report

## Stage Positioning

- This stage prepares Hermes to use DeepSeek as a model backend only.
- This stage is not a Hermes enforcement wrapper.
- Hermes is not run by default.
- DeepSeek is not called by default.
- No real tools, shell tools, email, or gateway messages are executed.
- API key values are never printed or written to reports.

## DeepSeek Config Status

- key_present: True
- key_value_printed: False
- base_url: https://api.deepseek.com
- model: deepseek-v4-pro
- reasoning_effort: high
- smoke_test_allowed: False
- smoke_test_attempted: False
- smoke_test_status: smoke_test_skipped
- hermes_run_allowed: False
- hermes_run_reason: missing explicit Hermes DeepSeek no-tools run authorization or safe environment

## Hermes Config Audit

- repo_status: available
- repo_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/external/hermes-agent`
- files_scanned: 5000
- provider_config_found: True
- OpenAI-compatible path found: True
- DeepSeek support found: True
- mapping recommendation: Set Hermes `model.provider: deepseek` and `model.default: deepseek-v4-pro`; keep API key in `DEEPSEEK_API_KEY`.
- Hermes direct mapping: `model.provider: deepseek`, `model.default: deepseek-v4-pro`, key from `DEEPSEEK_API_KEY`.
- Observed built-in DeepSeek provider base URL: `https://api.deepseek.com/v1`.

## Security Boundary

- DeepSeek is not in the CapProof TCB.
- DeepSeek output cannot mint capability.
- DeepSeek output cannot allow tool call.
- Hermes tool calls still require CapProof guard.
- Reference Monitor remains final authority.
