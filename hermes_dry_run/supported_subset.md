# Hermes Supported Subset

This subset is a mock dry-run contract only. It is based on static Hermes source
audit findings and Stage 20 observed-shape adapter coverage. It is not a real
Hermes integration and does not run Hermes.

Supported shapes:

- Terminal commands that map exactly to allowlisted templates, currently
  `pytest <target>` and `python -m pytest <target>`.
- `send_message` with an exact authorized target such as
  `telegram:alice_chat`.
- Content-only memory writes where authority-like claims are stripped and no
  capability is minted.
- `delegate_task` when the child action has a valid Delegation Certificate and
  the child capability is attenuated by the parent scope.
- Dynamic MCP `http_post` when both the action URL and transport endpoint have
  matching endpoint capabilities.
- `edit_file` inside an authorized workspace path where `path` and
  `resolved_path` agree and `cross_profile` is false.
- `cronjob` send actions with explicit schedule capability and recipient
  capability bound to the current task.

All ALLOW decisions use `MockExecutor` only.
