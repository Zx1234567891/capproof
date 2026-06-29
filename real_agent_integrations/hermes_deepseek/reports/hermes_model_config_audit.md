# Hermes Model Config Static Audit

This audit only reads local Hermes source and docs. It does not run Hermes,
install dependencies, execute third-party commands, or call DeepSeek.

- repo_status: available
- repo_path: `/home/xiaowu/Desktop/CapProof_USENIX_Revised_v7/external/external/hermes-agent`
- files_scanned: 5000
- provider_config_found: True
- provider_dir_found: True
- OpenAI-compatible path found: True
- DeepSeek support found: True
- base_url/api_base/endpoint field found: True
- model field found: True
- api_key/env field found: True
- mapping recommendation: Set Hermes `model.provider: deepseek` and `model.default: deepseek-v4-pro`; keep API key in `DEEPSEEK_API_KEY`.

## Observed In Source

- Provider directory or provider-like path exists in local Hermes checkout.
- OpenAI-related provider/config references observed in source or docs.
- OpenRouter-related provider/config references observed in source or docs.
- DeepSeek-related references observed in local checkout.
- Built-in `plugins/model-providers/deepseek` provider profile observed.
- base_url / api_base / endpoint-like configuration fields observed.
- API key / token / environment variable references observed.

## Inferred From Docs

- Docs mention model/provider switching; exact runtime mapping still needs manual verification.

## Unknown

- Exact Hermes local config write path and command remain unverified without running Hermes.

## Needs Manual Verification

- Confirm exact Hermes provider config schema before writing any real local config.
- Keep DEEPSEEK_API_KEY in environment only; never commit real keys.

## Sample Files

- `.env.example`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/ISSUE_TEMPLATE/setup_help.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/actions/detect-changes/action.yml`
- `.github/actions/nix-setup/action.yml`
- `.github/actions/retry/action.yml`
- `.github/dependabot.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-site.yml`
- `.github/workflows/docker-lint.yml`
- `.github/workflows/docker.yml`
- `.github/workflows/skills-index-freshness.yml`
- `.github/workflows/skills-index.yml`
- `.github/workflows/supply-chain-audit.yml`
- `.github/workflows/tests.yml`
- `.github/workflows/upload_to_pypi.yml`
- `.hadolint.yaml`
- `.plans/openai-api-server.md`
- `.plans/streaming-support.md`
- `AGENTS.md`
- `CONTRIBUTING.es.md`
- `CONTRIBUTING.md`
- `README.es.md`
