"""The Azure probe's report builder: per-locale rows from the cases, and the glossary mode the results recommend.

The mode is strict only when every target locale reaches the threshold of valid card units (decision D8); a locale the
probe did not reach counts as not reaching it, so an interrupted run recommends advisory.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from discovery_ingest.translation.findings import Finding
from discovery_ingest.translation.glossary import GlossaryMode
from discovery_ingest.translation.probe_azure_model import (
    AzureProbeReport,
    LocaleRow,
    MarkupRow,
    RequestRow,
    ThrottleRow,
)
from discovery_ingest.translation.probe_azure_types import (
    ANSWERED,
    AzureProbePlan,
    AzureProbeResult,
    Exchange,
    LocaleRun,
    MarkupRun,
    ThrottleRun,
)
from discovery_ingest.translation.repair import Checked
from discovery_ingest.translation.validate_glossary import GLOSSARY_CHECK

STRICT_THRESHOLD: Final = 0.9
PLACEHOLDER_CHECKS: Final = frozenset({"placeholders", "urls"})
THROTTLED: Final = "HTTP 429"


def _share(valid: int, units: int) -> float:
    return round(valid / units, 4) if units else 0.0


def _valid(checked: list[Checked]) -> int:
    return sum(item.valid for item in checked)


def _units_with(checked: list[Checked], wanted: Callable[[Finding], bool]) -> int:
    return sum(any(wanted(finding) for finding in item.findings) for item in checked)


def _locale_row(locale: str, run: LocaleRun | None, units: int) -> LocaleRow:
    checked = run.checked if run is not None else {}
    cards, tokens, plural = checked.get("cards", []), checked.get("tokens", []), checked.get("plural", [])
    exchanges: tuple[Exchange, ...] = run.exchanges if run is not None else ()
    return LocaleRow(
        locale=locale,
        measured=run is not None,
        units=units,
        valid_units=_valid(cards),
        valid_share=_share(_valid(cards), units),
        glossary_findings=_units_with(cards, lambda finding: finding.check == GLOSSARY_CHECK),
        placeholder_failures=_units_with(cards, lambda finding: finding.check in PLACEHOLDER_CHECKS),
        token_units=len(tokens),
        token_valid=_valid(tokens),
        plural_units=len(plural),
        plural_valid=_valid(plural),
        billed_characters=_billed(exchanges),
        estimated_characters=sum(exchange.sent for exchange in exchanges),
        unmetered_requests=sum(exchange.metered is None for exchange in exchanges),
        requests=[RequestRow(sent=exchange.sent, metered=exchange.metered) for exchange in exchanges],
    )


def _billed(exchanges: tuple[Exchange, ...]) -> float:
    """Return the characters the service reported; a request without the header bills nothing here (see unmetered)."""
    return sum(exchange.metered for exchange in exchanges if exchange.metered is not None)


def tags_billed(sent: int, visible: int, metered: float | None) -> bool | None:
    """Return whether the tags of an HTML input are billed: yes when the header counts them, no when it counts the text only."""
    if metered is None:
        return None
    if metered == sent:
        return True
    return False if metered == visible else None


def _markup_row(run: MarkupRun | None) -> MarkupRow | None:
    if run is None:
        return None
    return MarkupRow(
        sent=run.sent,
        visible=run.visible,
        metered=run.metered,
        tags_billed=tags_billed(run.sent, run.visible, run.metered),
    )


def _throttle_row(run: ThrottleRun | None) -> ThrottleRow | None:
    if run is None:
        return None
    answered = sum(answer == ANSWERED for answer in run.answers)
    throttled = sum(THROTTLED in answer for answer in run.answers)
    return ThrottleRow(attempts=run.attempts, answered=answered, throttled=throttled, answers=list(run.answers))


def recommend(rows: list[LocaleRow]) -> GlossaryMode:
    """Return ``strict`` only when every locale reaches the threshold of valid units, else ``advisory``."""
    return "strict" if rows and all(row.valid_share >= STRICT_THRESHOLD for row in rows) else "advisory"


def build_report(plan: AzureProbePlan, result: AzureProbeResult) -> AzureProbeReport:
    """Return the report of one run: a row per planned locale (unmeasured ones included), the answers and the totals."""
    units = len(plan.units)
    rows = [_locale_row(locale, result.locales.get(locale), units) for locale in plan.locales]
    return AzureProbeReport(
        api_version=plan.connection.api_version,
        units=units,
        max_characters=plan.max_characters,
        locales=rows,
        markup=_markup_row(result.markup),
        throttle=_throttle_row(result.throttle),
        billed_characters=_billed(result.exchanges),
        estimated_characters=sum(exchange.sent for exchange in result.exchanges),
        recommended_glossary_mode=recommend(rows),
        stopped=result.stopped,
    )
