"""Probe items 1 and 2: the envelope of each endpoint and the usage it carries."""

from __future__ import annotations

from pydantic import JsonValue

from discovery_ingest.extract.llm.probe_calls import RawCall
from discovery_ingest.extract.llm.probe_report import ProbeRow
from discovery_ingest.extract.llm.probe_shape import failure_text, fields, flatten, kind, reasoning_notes


def envelope_row(model: str, call: RawCall) -> ProbeRow:
    """Describe the native ``/ai/run`` envelope: its keys and whether ``result.response`` is an object or a string."""
    payload = call.payload
    if not call.ok or payload is None:
        return ProbeRow(model, "envelope", f"no usable envelope: {failure_text(call)}")
    result = fields(payload.get("result"))
    shape = f"result keys={','.join(result)}; result.response={kind(result.get('response'))}"
    return ProbeRow(model, "envelope", f"{shape}; envelope keys={','.join(payload)}")


def chat_envelope_row(model: str, call: RawCall | None) -> ProbeRow:
    """Describe the OpenAI-compatible envelope: ``choices[0].message.content`` and whether usage is in the body."""
    payload = call.payload if call is not None and call.ok else None
    if call is None or payload is None:
        return ProbeRow(model, "chat-envelope", f"no usable envelope: {failure_text(call) if call else 'not called'}")
    choices = payload.get("choices")
    first = fields(choices[0]) if isinstance(choices, list) and choices else {}
    message = fields(first.get("message"))
    shape = f"message keys={','.join(message)}; message.content={kind(message.get('content'))}"
    return ProbeRow(model, "chat-envelope", f"{shape}; usage in body={'usage' in payload}")


def _usage(label: str, container: JsonValue) -> str:
    usage = fields(fields(container).get("usage"))
    return f"{label} usage: {' '.join(flatten('', usage)) if usage else 'absent'}"


def usage_row(model: str, native: RawCall, chat: RawCall | None) -> ProbeRow:
    """Report the token counts each endpoint returned (the native one sits in ``result.usage``) and reasoning fields."""
    native_result = fields(native.payload).get("result") if native.ok else None
    chat_payload = chat.payload if chat is not None and chat.ok else None
    notes = [*reasoning_notes(native_result), *reasoning_notes(chat_payload)]
    reasoning = ", ".join(notes) if notes else "no reasoning fields seen"
    return ProbeRow(
        model, "usage", f"{_usage('run', native_result)}; {_usage('chat', chat_payload)}; reasoning: {reasoning}"
    )
