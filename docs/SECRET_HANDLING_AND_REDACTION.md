# Secret Handling and Redaction

## Rule

`DEEPSEEK_API_KEY` is environment-only. Do not write the key to source, config, reports, traces, logs, handoff files, Makefiles, shell scripts, commits, isolated runtime homes, or auth queues.

## Redaction Strategy

Scripts redact:

- the exact current `DEEPSEEK_API_KEY` value when present in the process environment;
- key-like strings matching `sk-*` secret patterns.

The only allowed key-like fixture is the literal test dummy value `sk-test-secret-do-not-write`. It is not a real credential and exists only in unit tests that verify redaction behavior. Any other key-like value is treated as a leak.

Reports may record:

- `deepseek_key_present: true/false`
- `deepseek_key_source: DEEPSEEK_API_KEY`
- `deepseek_key_written: false`

Reports must not record the key value.

## Secret Scan

Reviewer-safe scans:

```bash
python run_real_agent_parity_evaluator.py --preflight
git ls-files external external/.agent-runtimes .venv-hermes node_modules
```

The evaluator also scans tracked files and report/trace directories for the current key and key-like patterns. A hit makes the evaluator fail.

## Accidental Leak Handling

If a real key is found:

1. Stop and do not commit.
2. Remove the leaked file content or discard the generated artifact.
3. Rotate the exposed key.
4. Rerun the secret scan.

Do not preserve leaked key material in bug reports, handoff files, or commit history.
