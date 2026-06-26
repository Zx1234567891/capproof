"""Stable JSON serialization primitives for CapProof schemas."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any, TypeAlias

JsonValue: TypeAlias = Any
JsonObject: TypeAlias = dict[str, JsonValue]


def to_jsonable(value: Any) -> JsonValue:
    """Convert supported schema values to a JSON-compatible tree."""

    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple | list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        normalized: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"JSON object keys must be strings, got {type(key)!r}")
            normalized[key] = to_jsonable(item)
        return normalized
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported value for canonical JSON: {type(value)!r}")


def canonical_json(value: Any) -> str:
    """Return deterministic JSON with sorted keys and no insignificant spacing."""

    return json.dumps(
        to_jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_hash(value: Any) -> str:
    """Return a SHA-256 digest over the canonical JSON representation."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class CanonicalModel:
    """Mixin for schema objects with stable JSON and hash helpers."""

    def to_dict(self) -> JsonObject:
        value = to_jsonable(self)
        if not isinstance(value, dict):
            raise TypeError("schema object did not serialize to a JSON object")
        return value

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    def stable_hash(self) -> str:
        return stable_hash(self)
