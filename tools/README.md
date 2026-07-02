# Project Tools

This directory contains repository-level executable scripts that were
previously kept in the project root.

Use them from the repository root:

```bash
python tools/run_capproof_mcp_server.py --list-tools
python tools/run_final_release_check.py --preflight
python tools/run_kill_tests.py --mode all --baselines
```

The scripts intentionally keep their outputs in the existing artifact,
report, trace, and integration directories. Moving them under `tools/` is an
organizational change only; it does not change CapProof verifier semantics,
Reference Monitor behavior, sandbox scope, or release claims.
