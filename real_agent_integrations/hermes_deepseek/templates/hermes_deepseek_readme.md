# Hermes DeepSeek Configuration Template

This directory contains templates only. Do not commit a real `DEEPSEEK_API_KEY`.
The key must be read from the `DEEPSEEK_API_KEY` environment variable.

If a key is exposed in a prompt, log, report, config file, shell history, or
commit, rotate it immediately.

DeepSeek is only the Hermes model backend. It is not part of the CapProof
security TCB. DeepSeek output cannot mint a capability and cannot allow a tool
call. Any Hermes tool call produced while using DeepSeek must still go through
CapProof capture, guard, and the Reference Monitor.

The local Hermes checkout contains a built-in `deepseek` provider profile.
Use `real_agent_integrations/hermes_deepseek/configs/hermes_config.deepseek.example.yaml`
as the `~/.hermes/config.yaml` snippet, with `DEEPSEEK_API_KEY` supplied from
the environment.
