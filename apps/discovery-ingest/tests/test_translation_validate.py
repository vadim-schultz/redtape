"""Translation validators: each check is a small pure function; the unit validator runs them over title and description."""

from __future__ import annotations

from dataclasses import replace

import pytest
from discovery_ingest.translation.glossary import Glossary, GlossaryEntry
from discovery_ingest.translation.repair import Checked
from discovery_ingest.translation.validate import validate_text, validate_unit

from translation_fakes import GLOSSARY, unit

SOURCE = "Antrag auf Kindergeld nach § 62 EStG: 12,50 Euro bis 01.03.2025, siehe https://familienkasse.example/antrag."
FAITHFUL = "Application for child benefit under § 62 EStG: 12.50 euros until 01.03.2025, see https://familienkasse.example/antrag."
GLOSSARY_KINDERGELD = Glossary(
    terms=(GlossaryEntry("Antrag", "application"), GlossaryEntry("Kindergeld", "child benefit")), keep=("EStG",)
)


def _checks(source: str, translated: str, glossary: Glossary = GLOSSARY_KINDERGELD) -> set[str]:
    return {finding.check for finding in validate_text(source, translated, glossary)}


def test_a_faithful_translation_passes_every_check() -> None:
    """validate · accepts a faithful translation: numbers, a § citation, a date, a URL and glossary terms preserved."""
    assert validate_text(SOURCE, FAITHFUL, GLOSSARY_KINDERGELD) == []


@pytest.mark.parametrize(
    ("translated", "check"),
    [
        (FAITHFUL.replace("12.50", "15.50"), "numbers"),
        (FAITHFUL.replace("§ 62", "section"), "citations"),
        (FAITHFUL.replace("01.03.2025", "03/01/2025"), "dates"),
        (FAITHFUL.replace("/antrag", "/form"), "urls"),
        (FAITHFUL + " <b>bold</b>", "markup"),
        (FAITHFUL.replace("Application", "Request"), "glossary"),
        (FAITHFUL.replace("EStG", "income tax act"), "glossary"),
        (FAITHFUL + " Extra {name}", "placeholders"),
        ("   ", "non_empty"),
        ("Ja", "length_ratio"),
        (FAITHFUL * 6, "length_ratio"),
        (SOURCE, "unchanged_copy"),
    ],
)
def test_each_broken_promise_is_reported_by_its_own_check(translated: str, check: str) -> None:
    """validate · rejects changed numbers, dropped citations, changed dates and URLs, markup, a glossary violation, an extreme ratio, an empty text and an unchanged copy."""
    assert check in _checks(SOURCE, translated)


def test_a_dropped_placeholder_is_reported() -> None:
    """validate · a placeholder of the source that is missing in the translation is a finding."""
    assert "placeholders" in _checks("Aktenzeichen {case_id} angeben", "Enter the case number")


def test_a_very_short_text_may_come_back_unchanged() -> None:
    """validate · a short title or proper noun that is the same in both languages is not an unchanged-copy finding."""
    assert _checks("Bürgeramt", "Bürgeramt") == set()
    assert _checks("Jobcenter Berlin", "Jobcenter Berlin") == set()
    assert "unchanged_copy" in _checks("Anmeldung einer Wohnung beim Amt", "Anmeldung einer Wohnung beim Amt")


def test_markup_that_the_source_already_has_is_not_an_added_one() -> None:
    """validate · markup only counts as added when the source did not contain it."""
    assert "markup" not in _checks("Frist <b>wichtig</b>", "Deadline <b>important</b>")


def test_text_invented_for_an_empty_source_is_rejected_and_an_empty_pair_is_fine() -> None:
    """validate · an empty source stays empty; invented text is a finding."""
    assert _checks("", "") == set()
    assert "non_empty" in _checks("", "Something the model made up")


def test_a_glossary_rendering_is_matched_through_inflection() -> None:
    """validate · an inflected rendering (a case ending in Russian) still satisfies the glossary."""
    ru = Glossary(terms=(GlossaryEntry("Kindergeld", "детское пособие"),))

    assert _checks("Kindergeld beantragen", "Оформить детского пособия", ru) == set()
    assert "glossary" in _checks("Kindergeld beantragen", "Оформить пенсию", ru)


def test_a_glossary_term_inside_a_compound_is_not_required() -> None:
    """validate · the term must be a whole word of the source; a compound that merely contains it is left to the model."""
    assert _checks("Kindergeldantrag stellen", "Submit a child benefit claim", GLOSSARY_KINDERGELD) == set()


def test_the_unit_validator_reports_which_field_failed() -> None:
    """validate · validate_unit checks title and description separately and names the field."""
    source = unit("k", "Antrag nach § 35", "Gebühr 12,50 Euro")
    bad = unit("k", "Application under section", "Fee 12.50 euros")

    findings = validate_unit(source, bad, GLOSSARY)

    assert {(finding.check, finding.field) for finding in findings} == {("numbers", "title"), ("citations", "title")}


def test_an_empty_description_on_both_sides_is_not_a_finding() -> None:
    """validate · a unit without a description validates on its title alone."""
    assert validate_unit(unit("k", "Wohngeld"), unit("k", "Housing benefit"), GLOSSARY) == []


def test_advisory_mode_records_a_glossary_finding_without_failing_the_unit() -> None:
    """Validator · advisory mode records a glossary finding without failing the unit; the unit stays valid."""
    advisory = replace(GLOSSARY_KINDERGELD, mode="advisory")
    translated = FAITHFUL.replace("Application", "Request")

    findings = validate_text(SOURCE, translated, advisory)
    checked = Checked(unit("k", SOURCE, ""), unit("k", translated, ""), tuple(findings))

    assert [(finding.check, finding.advisory) for finding in findings] == [("glossary", True)]
    assert checked.valid is True


def test_strict_mode_fails_the_unit_on_the_same_glossary_finding() -> None:
    """Validator · strict mode, the default, makes the same glossary finding a failure of the unit."""
    translated = FAITHFUL.replace("Application", "Request")

    findings = validate_text(SOURCE, translated, GLOSSARY_KINDERGELD)
    checked = Checked(unit("k", SOURCE, ""), unit("k", translated, ""), tuple(findings))

    assert [(finding.check, finding.advisory) for finding in findings] == [("glossary", False)]
    assert checked.valid is False
