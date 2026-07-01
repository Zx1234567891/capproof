# CapProof ASK Authorization Queue Report

This stage implements trusted local approval UX for MCP ASK requests.

- ASK only creates a pending request.
- ASK does not mint capability.
- ASK does not execute an executor.
- Pending requests include requested_action, requested_scope, canonical_action_hash, status, and expiry.
- Only the trusted local CLI can approve, deny, or expire a request.
- Trusted approve can mint only scoped capability matching the pending request.
- Approval creates a redaction-safe approval receipt.
- Deny and expire never mint capability.
- Hermes, DeepSeek, MCP metadata, tool descriptions, annotations, `_meta`, clientInfo, and clientCapabilities cannot approve.
- Approval scope amplification is rejected.
- Replay approval is rejected.
- Receipts and queue records are redaction-safe.
- This does not modify CapProof core verifier or Reference Monitor semantics.

## Summary

- request_count: 1
- receipt_count: 1
- status_counts: `{"approved": 1, "denied": 0, "expired": 0, "pending": 0}`
- pending_path: `/tmp/pytest-of-xiaowu/pytest-439/test_trusted_cli_approval_crea0/auth_queue/pending_authorizations.jsonl`
- receipts_path: `/tmp/pytest-of-xiaowu/pytest-439/test_trusted_cli_approval_crea0/auth_queue/authorization_receipts.jsonl`
- audit_trace_path: `/tmp/pytest-of-xiaowu/pytest-439/test_trusted_cli_approval_crea0/ask_trace.jsonl`

## Non-Claims

- no production-level Hermes protection
- no all Hermes tool paths covered
- no OpenCode/OpenClaw real integration
