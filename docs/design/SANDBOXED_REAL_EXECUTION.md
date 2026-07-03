# Stage 33S Sandboxed Real Execution

Stage 33S adds a minimal sandboxed real executor for the CapProof MCP product
layer. It does not change CapProof core verifier, Reference Monitor,
Capability Store, or Proof Model semantics.

## Boundary

- CapProof guard / Reference Monitor remains the authorization boundary.
- The sandbox is not an authorization root.
- ALLOW can enter the sandbox executor only after CapProof returns ALLOW.
- DENY and ASK do not execute the sandbox executor.
- The stage does not claim production-level Hermes protection.
- The stage does not claim OS-level network denial. No network namespace or
  equivalent network isolation is implemented here.

## Supported Effects

The first sandbox supports only:

- workspace-only file read;
- workspace-only file write;
- allowlisted command-template execution.

Unsupported:

- real email;
- external MCP;
- raw shell strings;
- arbitrary filesystem access;
- arbitrary network access;
- external endpoints;
- production enforcement wrapper.

## Workspace File Policy

- `workspace_root` is canonicalized.
- Requested paths are resolved under `workspace_root`.
- Path traversal is denied.
- Symlink escape is denied by resolution and workspace containment.
- Absolute paths outside the workspace are denied.
- Secret-like paths are denied by default:
  - `.env`
  - `.git`
  - `.ssh`
  - `.aws`
  - `.config`
  - `*.pem`
  - `*.key`
  - `id_rsa` / similar private key names
- File size and content size are capped.
- Writes are atomic via same-directory temporary file and replace.
- Each real file side effect is reflected in the MCP trace `mock_event`.

## Command Template Policy

- `shell=False`.
- argv list only.
- `template_id` must be allowlisted.
- Arguments are schema/policy validated.
- cwd must resolve inside the workspace.
- Environment is allowlist-only.
- Secret-like env keys are rejected.
- Inherited secrets are not passed to the command.
- Timeout is required.
- stdout/stderr are capped.
- Raw shell strings and unknown templates are denied/refused.

## Current Template

The minimal template is:

- `pytest`: runs `python -m pytest <target>` with optional allowed env
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD`.

## Claims

Allowed claim:

- CapProof MCP can execute a minimal sandboxed real workspace file/template
  subset after CapProof guard ALLOW.

Disallowed claims:

- Production-level Hermes protection.
- All Hermes tool paths covered.
- OS-level network denial.
- Raw shell support.
- Real email or external MCP support.
