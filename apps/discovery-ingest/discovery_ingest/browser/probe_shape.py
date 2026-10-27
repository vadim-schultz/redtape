"""Describe a Cloudflare response by shape and size only: bodies are never echoed, only a few named fields."""

from __future__ import annotations

import base64
import binascii
import json

import httpx
from pydantic import JsonValue

from discovery_ingest.browser.images import image_kind

_META_FIELDS = ("status", "finalUrl", "title")


def _size(value: str) -> int:
    return len(value.encode())


def _kind(value: JsonValue) -> str:
    if isinstance(value, str):
        return f"str[{_size(value)} B]"
    if isinstance(value, dict):
        return "obj"
    if isinstance(value, list):
        return f"list[{len(value)}]"
    return type(value).__name__


def _image_detail(path: str, encoded: str) -> str:
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return f"{path}=str[{_size(encoded)} B] (not base64)"
    return f"{path}={image_kind(data)} {len(data)} B"


def _result_details(result: JsonValue) -> list[str]:
    if not isinstance(result, dict):
        return []
    return [
        _image_detail(f"result.{key}", value)
        if key == "screenshot" and isinstance(value, str)
        else f"result.{key}={_kind(value)}"
        for key, value in result.items()
    ]


def _meta_details(meta: JsonValue) -> list[str]:
    if not isinstance(meta, dict):
        return []
    shown = [f"meta.{key}={meta[key]}" for key in _META_FIELDS if key in meta]
    chain = meta.get("redirectChain")
    redirects = [f"meta.redirects={len(chain)}"] if isinstance(chain, list) else []
    return [f"meta.keys={','.join(meta)}", *shown, *redirects]


def _error_details(errors: JsonValue) -> list[str]:
    if not isinstance(errors, list):
        return []
    return [f"error {item.get('code')}: {item.get('message')}" for item in errors if isinstance(item, dict)]


def _echo_detail(expect: str | None, payload: dict[str, JsonValue]) -> list[str]:
    if expect is None:
        return []
    echoed = expect in str(payload.get("result"))
    return ["userAgent echoed" if echoed else "userAgent NOT echoed"]


def _enveloped(payload: dict[str, JsonValue], expect: str | None) -> tuple[str, list[str]]:
    shape = "json{" + ",".join(f"{key}:{_kind(value)}" for key, value in payload.items()) + "}"
    details = [
        *_result_details(payload.get("result")),
        *_meta_details(payload.get("meta")),
        *_error_details(payload.get("errors")),
        *_echo_detail(expect, payload),
    ]
    return shape, details


def _json_payload(response: httpx.Response) -> dict[str, JsonValue] | None:
    try:
        payload = json.loads(response.content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def describe(response: httpx.Response, expect: str | None) -> tuple[str, list[str]]:
    """Return the body shape and the named details of ``response`` (the JSON envelope or a raw body)."""
    payload = _json_payload(response)
    if payload is not None:
        return _enveloped(payload, expect)
    kind = response.headers.get("content-type", "unknown")
    return f"raw {kind.split(';')[0]} {len(response.content)} B", [f"first bytes are {image_kind(response.content)}"]
