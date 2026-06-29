"""Observable CapProof MCP workflow tracing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import time
from typing import Any

from capproof.serialization import JsonObject, stable_hash


@dataclass(frozen=True)
class MCPTraceEntry:
    trace_id: str
    timestamp: float
    mcp_method: str
    tool_name: str
    arguments: JsonObject
    original_arguments: JsonObject
    canonical_action_hash: str | None
    capproof_verdict: str
    proof_id: str | None
    reason: str
    executor_called: bool
    user_task: str = ""
    canonical_tool: str | None = None
    authority_bearing_fields: tuple[str, ...] = ()
    mcp_metadata: JsonObject = field(default_factory=dict)
    raw_mcp_request: JsonObject = field(default_factory=dict)
    canonical_action: JsonObject | None = None
    mock_event: JsonObject | None = None

    def to_dict(self) -> JsonObject:
        payload = asdict(self)
        payload["authority_bearing_fields"] = list(self.authority_bearing_fields)
        return payload


class TraceRecorder:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: MCPTraceEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")

    def read_entries(self) -> list[JsonObject]:
        if not self.path.exists():
            return []
        entries: list[JsonObject] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                entries.append(value)
        return entries

    def tail(self, limit: int = 50) -> list[JsonObject]:
        if limit <= 0:
            return []
        return self.read_entries()[-limit:]


def new_trace_id(*, method: str, tool_name: str, arguments: JsonObject, index: int) -> str:
    digest = stable_hash(
        {
            "method": method,
            "tool_name": tool_name,
            "arguments": arguments,
            "index": index,
            "timestamp_bucket": int(time.time() * 1000),
        }
    )
    return f"mcp_trace_{digest[:16]}"
