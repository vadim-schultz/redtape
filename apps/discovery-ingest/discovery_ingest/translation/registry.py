"""The engine registry: adapters register a factory under a name; the drain and the probe get engines only from here."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES, require_coverage

BUILTIN_ADAPTERS = "discovery_ingest.translation.adapters"
"""Importing this package registers the adapters that ship with the repository."""


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """What a factory may use: a model override, the locales it must cover, a shared HTTP client and call pacing."""

    model: str | None = None
    target_locales: tuple[str, ...] = DEFAULT_TARGET_LOCALES
    http: httpx.Client | None = None
    min_interval_seconds: float | None = None


EngineFactory = Callable[[EngineConfig], TranslationEngine]


class UnknownEngineError(LookupError):
    """The name is not a registered engine; the message lists the registered ones."""


_FACTORIES: dict[str, EngineFactory] = {}


def register_engine(name: str, factory: EngineFactory) -> None:
    """Register ``factory`` under ``name``; a second registration of one name is a programming error."""
    if name in _FACTORIES:
        raise ValueError(f"translation engine {name!r} is already registered")
    _FACTORIES[name] = factory


def unregister_engine(name: str) -> None:
    """Remove ``name`` (tests that register a throwaway engine)."""
    _FACTORIES.pop(name, None)


def registered_engines() -> tuple[str, ...]:
    """Return the registered engine names, built-in adapters included, in registration order."""
    importlib.import_module(BUILTIN_ADAPTERS)
    return tuple(_FACTORIES)


def require_registered(name: str) -> str:
    """Return ``name`` or raise :class:`UnknownEngineError` listing the registered engines."""
    if name not in registered_engines():
        raise UnknownEngineError(f"unknown translation engine {name!r}; registered: {', '.join(registered_engines())}")
    return name


def build_engine(name: str, config: EngineConfig) -> TranslationEngine:
    """Build the engine registered as ``name``; its locale map must cover ``config.target_locales``."""
    require_registered(name)
    require_coverage(name, config.target_locales)
    return _FACTORIES[name](config)
