# CapProof Implementation Status

## Checkpoint 0 - Repository Review and Implementation Plan

Status: completed, awaiting user confirmation before implementation.

Scope:
- Read the current repository structure and project documents.
- No implementation code was added.
- Established the proposed staged MVP plan, TCB boundary, and first files to modify.

Repository state observed:
- Current repository is documentation-only at the top level.
- No source package, tests, or build configuration are present yet.

Next checkpoint, pending confirmation:
- Scaffold the minimal Python package, pytest configuration, and deterministic Tier-0 core skeleton.

## Stage 1 - Project Scaffold and Core Schemas

Status: completed, self-check passed, awaiting user confirmation before Stage 2.

Scope:
- Create the Python package scaffold under `src/capproof/`.
- Create the stage-1 schema tests under `tests/`.
- Define passive typed schema objects only.
- Add stable canonical JSON serialization and stable hashing helpers.

Completed:
- Added `pyproject.toml` with `src` package layout and pytest configuration.
- Added `src/capproof/` package.
- Added passive schema dataclasses for AuthSpec, Capability, Receipt, ValueRef, ToolContract, Proof, Action, VerificationDecision, and DenyReason.
- Added canonical JSON serialization using sorted keys and stable SHA-256 hashes.
- Added tests for schema round-trip serialization, deterministic canonical JSON, stable action/proof hashes, opaque capability handles, and authority-bearing ToolContract fields.

Self-check commands:
- `python -m compileall src tests` -> passed.
- `pytest -q` -> failed before collecting project tests because an external auto-loaded ROS pytest plugin imports missing dependency `lark`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q` -> 5 passed, 0 failed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_schema.py -q` -> 5 passed, 0 failed.

Known risks:
- No Reference Monitor, minting service, capability store, receipt verification, proof synthesis, tool execution, memory stripping, endorsement, or delegation logic exists yet.
- `Capability.mac` is only a schema field in Stage 1; unforgeability is not implemented until later stages.
- `Proof` is only a passive witness schema and is not trusted or verified in Stage 1.

Next stage recommendation:
- Implement Capability Store, minting schema validation, and Receipt Store primitives without adding tool execution.

Out of scope for this stage:
- Reference Monitor verification logic.
- Capability store or minting logic.
- Receipt signing or verification logic.
- Tool execution, mock execution, sandboxing, or tool adapters.
- Proof synthesis.

## Stage 2 - Capability Store

Status: completed, self-check passed, awaiting user confirmation before Stage 3.

Scope:
- Implement the CapabilityStore interface and InMemoryCapabilityStore.
- Implement mint, lookup, validate, reserve, consume, and revoke lifecycle operations.
- Enforce task_id, agent_id, nonce, expiry, revocation, max_uses, uses, and linearity checks at the store layer.
- Add tests for one-use linear capabilities, replay denial, expired/revoked caps, task/agent mismatch, reusable caps, and fake cap handles.

Completed:
- Added `CapabilityStore` protocol and `InMemoryCapabilityStore`.
- Added store-level `mint_capability`, `lookup_capability`, `validate_capability`, `reserve_capability`, `consume_capability`, and `revoke_capability` wrappers.
- Added deterministic `CapabilityCheck` results with `VerificationDecision` and `DenyReason`.
- Enforced lifecycle failures for `NoCap`, `ConsumedCap`, `ExpiredCap`, `RevokedCap`, `TaskMismatch`, `AgentMismatch`, `ReservedCap`, and nonce mismatch via `CapInvalid`.
- Added replay protection through reserved nonce matching and consumed status.

Self-check commands:
- `python -m compileall src tests` -> passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_capability_store.py -q` -> 11 passed, 0 failed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q` -> 16 passed, 0 failed.

Known risks:
- Capability unforgeability is limited to opaque handle lookup in this stage; cryptographic MAC verification is not implemented yet.
- This store does not decide whether a capability predicate authorizes an action argument; Reference Monitor predicate binding is a later stage.
- This store is in-memory only and not crash-durable.

Next stage recommendation:
- Implement receipt store/signature primitives or canonicalizer/contract registry, depending on the approved stage plan, without adding tool execution.

Out of scope for this stage:
- Reference Monitor authorization logic.
- Predicate matching against action arguments.
- Receipt Store, signing, or verification.
- Tool execution or adapters.
- Memory stripping, delegation certificates, endorsement manager, and Proof Synthesizer.
