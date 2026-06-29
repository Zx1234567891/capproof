"""JSON-RPC and MCP product-layer errors."""

from __future__ import annotations

from dataclasses import dataclass


PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
TOOL_NOT_FOUND = -32001


@dataclass(frozen=True)
class MCPError(Exception):
    code: int
    message: str
    data: dict[str, object] | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"code": self.code, "message": self.message}
        if self.data is not None:
            payload["data"] = self.data
        return payload


def invalid_request(message: str = "invalid JSON-RPC request") -> MCPError:
    return MCPError(INVALID_REQUEST, message)


def invalid_params(message: str = "invalid params") -> MCPError:
    return MCPError(INVALID_PARAMS, message)


def method_not_found(method: str) -> MCPError:
    return MCPError(METHOD_NOT_FOUND, f"method not found: {method}")


def tool_not_found(name: str) -> MCPError:
    return MCPError(TOOL_NOT_FOUND, f"tool not found: {name}")
