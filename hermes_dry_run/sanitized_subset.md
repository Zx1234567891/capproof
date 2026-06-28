# Hermes Sanitized / Stripped Allow Subset

These cases contain authority-like claims in memory inputs, but CapProof strips
the authority and treats the operation as a content-only mock memory write.

Requirements:

- Verdict may be `ALLOW` for the sanitized content write.
- `MockExecutor` may be called only for `memory_write`.
- No capability may be minted from stripped memory.
- `authority_claims` must be `{}` in the mock write.
- `stripped_authority` must be `true`.
- This does not mean the requested authority was accepted.
