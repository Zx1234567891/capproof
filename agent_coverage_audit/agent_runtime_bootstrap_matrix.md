# Agent Runtime Bootstrap Matrix

| item | passed | evidence |
| --- | --- | --- |
| real_environment_policy_active | True | REAL_ENVIRONMENT_VALIDATION.md active |
| preflight_not_completion | True | preflight cannot mark runtime_bootstrap_passed |
| opencode_bootstrap | True | ok |
| openclaw_bootstrap | True | ok |
| no_integration_claim | True | Stage 40RB does not run agent smoke |
| no_system_install | True | local ignored prefix only |
| secret_hygiene | True | no API key stored in bootstrap artifacts |
