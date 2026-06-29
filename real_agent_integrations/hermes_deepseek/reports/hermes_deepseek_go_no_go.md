# Hermes DeepSeek Go / No-Go

- Hermes + DeepSeek no-tools model call: conditional go after manual config verification
- Hermes + DeepSeek tool execution: no-go until a later CapProof guard integration stage.
- Enforcement wrapper: no-go.
- Claim that CapProof protects Hermes + DeepSeek: no-go.
- DeepSeek smoke test: skipped unless explicitly authorized.
- Current smoke status: smoke_test_skipped

## Security Boundary

- DeepSeek not in CapProof TCB: true
- DeepSeek can mint capability: false
- DeepSeek can allow tool call: false
- Reference Monitor final authority: true
