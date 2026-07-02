# Install Local Hermes Wrapper

This wrapper makes `hermes` launch the local foreground Hermes + CapProof MCP
workflow from this repository. It does not store secrets.

## Prerequisites

- Python 3.11 or newer.
- This repository checked out locally.
- Hermes local repository and `.venv-hermes` already prepared by prior gated
  Hermes stages if you intend to run real Hermes.
- `DEEPSEEK_API_KEY` must be provided from the environment for real DeepSeek
  runs. Do not write the key into files.

## Install

```bash
make install-local-hermes-wrapper
```

Installed command path:

```text
~/.local/bin/hermes
```

Wrapper target:

```text
bin/hermes
```

## Use

```bash
hermes
hermes --classic
hermes --doctor
hermes --where-trace
hermes --trace-follow
hermes --capproof-status
```

`hermes` starts the Hermes TUI through the local wrapper. Doctor, trace, and
status commands are local-only and do not call DeepSeek by default.

## Environment

```bash
export DEEPSEEK_API_KEY="..."
```

The key is read only from the environment. Do not put it in a config file,
report, trace, README, shell history snippet, or commit.

## Uninstall

```bash
make uninstall-local-hermes-wrapper
```
