# Hermes Hook Readiness Report

Hook readiness is derived from imported or captured JSONL events only. Unknown hooks are
not enforcement-ready. Observer-only or post-effect captures cannot support enforcement claims.

| Hook | Observed | Complete fields | Pre-execution observed | Side effect already happened | Enforcement-ready | Missing fields |
| --- | --- | --- | --- | --- | --- | --- |
| tool_dispatcher | no | unknown | unknown | unknown | no | none |
| terminal | no | unknown | unknown | unknown | no | none |
| MCP | no | unknown | unknown | unknown | no | none |
| memory | no | unknown | unknown | unknown | no | none |
| gateway | no | unknown | unknown | unknown | no | none |
| delegation | no | unknown | unknown | unknown | no | none |
| scheduler | no | unknown | unknown | unknown | no | none |
| middleware_rewrite | no | unknown | unknown | unknown | no | none |
