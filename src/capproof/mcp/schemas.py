"""MCP product-layer schemas.

These dataclasses describe the server-facing protocol and trace payloads. They
do not change CapProof's verifier, capability store, or proof model semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from capproof.serialization import JsonObject


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    input_schema: JsonObject
    authority_bearing_fields: tuple[str, ...] = ()
    read_only: bool = False
    destructive: bool = False
    open_world: bool = False

    def to_mcp_tool(self) -> JsonObject:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {
                "readOnlyHint": self.read_only,
                "destructiveHint": self.destructive,
                "openWorldHint": self.open_world,
                "capproofAuthorityBearingFields": list(self.authority_bearing_fields),
                "capproofMetadataCannotMintCapability": True,
            },
        }


@dataclass(frozen=True)
class MCPToolHandler:
    spec: MCPToolSpec
    to_raw_event: Callable[[Mapping[str, Any], "CapProofMCPContext"], JsonObject] | None = None
    admin_handler: Callable[[Mapping[str, Any], "CapProofMCPContext"], JsonObject] | None = None


@dataclass(frozen=True)
class MCPToolResult:
    content: list[JsonObject]
    structured_content: JsonObject
    is_error: bool = False

    def to_mcp_result(self) -> JsonObject:
        return {
            "content": self.content,
            "structuredContent": self.structured_content,
            "isError": self.is_error,
        }


@dataclass(frozen=True)
class MCPJsonRpcRequest:
    request_id: Any
    method: str
    params: JsonObject = field(default_factory=dict)


if False:  # pragma: no cover - import cycle typing hint only.
    from capproof.mcp.context import CapProofMCPContext
