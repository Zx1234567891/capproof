# CapProof Mechanism Suite Report

Stage: 10 - Mechanism Suite

Scope: action / proof / state only. No real LLM, no full agent loop, no email send, no shell execution, no network call, and no file write executor.

## Summary

- Mechanism cases: 62
- Expected allow cases: 10
- Expected deny cases: 52
- False allow: 0
- False deny: 0
- Pytest items in `tests/mechanism`: 64

## Channel Coverage

| Channel | Cases |
| --- | ---: |
| agent_mismatch | 1 |
| attachment | 1 |
| attachment_laundering | 3 |
| bcc | 1 |
| bcc_laundering | 3 |
| cap_forgery | 2 |
| cap_replay | 3 |
| delegation | 1 |
| delegation_amplification | 3 |
| endorsement | 1 |
| endorsement_replay | 4 |
| endpoint | 1 |
| endpoint_laundering | 4 |
| fake_proof_injection | 6 |
| file_path | 2 |
| file_path_laundering | 6 |
| memory_authority_laundering | 3 |
| path_traversal | 2 |
| recipient | 1 |
| recipient_laundering | 4 |
| shell | 1 |
| shell_template_bypass | 8 |
| task_mismatch | 1 |

## Failure Reason Distribution

| Deny reason | Count |
| --- | ---: |
| AdapterCoverageGap | 1 |
| AgentMismatch | 1 |
| CanonicalizationMismatch | 4 |
| CapPredicateMismatch | 11 |
| CommandTemplateViolation | 4 |
| ConsumedCap | 2 |
| DataClassMismatch | 1 |
| DelegationAmplification | 2 |
| DelegationMissing | 1 |
| EndorsementScopeError | 2 |
| MemoryAuthorityUse | 3 |
| MissingArgBinding | 2 |
| MissingReceipt | 1 |
| NoCap | 11 |
| ReservedCap | 1 |
| SourceMismatch | 1 |
| TaskMismatch | 1 |
| TemplateArgRejected | 2 |
| UnknownTool | 1 |

## Required Reason Coverage

- NoCap: covered
- ConsumedCap: covered
- MemoryAuthorityUse: covered
- DelegationAmplification: covered
- EndorsementScopeError: covered
- CanonicalizationMismatch: covered

## Safety Boundary

The suite constructs deterministic `Action`, `Proof`, and `MonitorState` objects and calls `ReferenceMonitor.verify`. It does not call tool executors or external model APIs. Shell and endpoint cases are contract/canonicalization checks only; they do not spawn processes or contact endpoints.
