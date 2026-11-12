"""The Azure probe's cases and run: each case measures one promise of the engine, through the production adapter.

Cards go to the engine as the drain sends them. The token and plural units go through the machine path of interface
strings (chapter 04). The locale cases run for every target locale, in the order of :data:`LOCALE_CASES`; the markup and
throttle cases run once, on the first locale. A refusal or the spend cap ends the run, and the result keeps what was
measured.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Final

import httpx

from discovery_ingest.i18n.machine_text import MachineTextTranslator
from discovery_ingest.translation.adapters.azure_translator import NAME
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.locale_codes import provider_code
from discovery_ingest.translation.probe_azure_session import SOURCE_LOCALE, ProbeStop, Session
from discovery_ingest.translation.probe_azure_types import (
    AzureProbePlan,
    AzureProbeResult,
    LocaleRun,
    MarkupRun,
    ThrottleRun,
)
from discovery_ingest.translation.probe_azure_units import PLURAL_UNITS, TOKEN_UNITS
from discovery_ingest.translation.repair import Checked
from discovery_ingest.translation.units import TranslationBatch, TranslationUnit

THROTTLE_CALLS: Final = 5
THROTTLE_TEXT: Final = "Antrag"
MARKUP_HTML: Final = "<p>Antrag auf <b>Wohngeld</b> stellen</p>"
MARKUP_VISIBLE: Final = re.sub(r"<[^>]+>", "", MARKUP_HTML)


def _cards(session: Session, locale: str) -> list[Checked]:
    """Return the cards as the drain sends them: each unit straight to the engine."""
    return session.translate(session.plan.units, locale, session.engine)


def _tokens(session: Session, locale: str) -> list[Checked]:
    """Return the named placeholders and a URL through the machine path: each placeholder must come back as it was."""
    return session.translate(TOKEN_UNITS, locale, MachineTextTranslator(session.engine))


def _plural(session: Session, locale: str) -> list[Checked]:
    """Return the plural forms through the machine path: the sample number must come back to restore ``{count}``."""
    return session.translate(PLURAL_UNITS, locale, MachineTextTranslator(session.engine))


LOCALE_CASES: Final[tuple[tuple[str, Callable[[Session, str], list[Checked]]], ...]] = (
    ("cards", _cards),
    ("tokens", _tokens),
    ("plural", _plural),
)
"""The cases run for every target locale, by name; the report reads them by these names."""


def _markup(session: Session, locale: str) -> MarkupRun:
    """Send one HTML-tagged input, to see whether the service bills the tags (O2)."""
    target = {"language": provider_code(NAME, locale)}
    text = {"text": MARKUP_HTML, "language": SOURCE_LOCALE, "textType": "html", "targets": [target]}
    exchange = session.send({"inputs": [text]}, len(MARKUP_HTML))
    return MarkupRun(len(MARKUP_HTML), len(MARKUP_VISIBLE), exchange.metered)


def _throttle(session: Session, locale: str) -> ThrottleRun:
    """Repeat one short text at the minimum interval; each attempt records its answer, a 429 with its code included."""
    unit = TranslationUnit("probe.throttle", THROTTLE_TEXT, "")
    batch = TranslationBatch(SOURCE_LOCALE, locale, (unit,), load_glossary(locale))
    answers = []
    for _ in range(THROTTLE_CALLS):
        session.reserve(len(THROTTLE_TEXT))
        answers.append(session.attempt(batch))
    return ThrottleRun(THROTTLE_CALLS, tuple(answers))


def _locale(session: Session, locale: str) -> LocaleRun:
    """Run every locale case for ``locale`` and keep the requests it sent."""
    start = len(session.exchanges)
    checked = {name: case(session, locale) for name, case in LOCALE_CASES}
    return LocaleRun(checked, session.exchanges[start:])


def run_azure_probe(plan: AzureProbePlan, http: httpx.Client) -> AzureProbeResult:
    """Run the cases of ``plan`` over ``http`` and return what they measured; nothing is sent past the cap."""
    session = Session(plan, http)
    locales: dict[str, LocaleRun] = {}
    markup: MarkupRun | None = None
    throttle: ThrottleRun | None = None
    stopped: str | None = None
    first = plan.locales[0]
    try:
        for locale in plan.locales:
            locales[locale] = _locale(session, locale)
        markup = _markup(session, first)
        throttle = _throttle(session, first)
    except ProbeStop as stop:
        stopped = str(stop)
    return AzureProbeResult(locales, markup, throttle, session.exchanges, stopped)
