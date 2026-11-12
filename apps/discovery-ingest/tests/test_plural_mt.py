"""Machine plural forms and placeholders: a representative number goes out for each category and the count comes back (AZ04)."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest
from discovery_ingest.i18n.files import Layout, TranslationFiles
from discovery_ingest.i18n.machine_text import MachineTextTranslator
from discovery_ingest.i18n.plural import PLURAL_CATEGORIES
from discovery_ingest.i18n.plural_mt import SAMPLES, representative_for, restore_count
from discovery_ingest.i18n.strings import SourceString
from discovery_ingest.i18n.translate_ui import UiJob, UiReport, translate_locale
from discovery_ingest.i18n.validate_ui import indistinct_slavic_families
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome, TranslationUnit, Usage

from ui_fakes import GLOSSARY, source

RUSSIAN_NOUN = {"1": "документ", "2": "документа", "5": "документов", "1,5": "документа"}


class _Machine:
    """A machine translator with no instructions: it answers each title with ``reply`` and keeps the batches sent."""

    repairs = False

    def __init__(self, reply: Callable[[str], str]) -> None:
        self._reply = reply
        self.sent: list[TranslationBatch] = []

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        self.sent.append(batch)
        units = tuple(TranslationUnit(unit.key, self._reply(unit.title), "") for unit in batch.units)
        return TranslationOutcome(units, Usage("characters", 0.0), None)

    @property
    def titles(self) -> list[str]:
        return [unit.title for batch in self.sent for unit in batch.units]


def _inflect(text: str) -> str:
    """A machine that inflects the Russian noun for the number it was sent, as a Russian speaker would."""
    number = text.split(" ", 1)[0]
    return f"{number} {RUSSIAN_NOUN[number]}"


def _same_form(text: str) -> str:
    """A machine that ignores the number: every category comes back in the same form."""
    return f"{text.split(' ', 1)[0]} документа"


def _spaced_braces(text: str) -> str:
    """A machine that spaces out the braces of every placeholder it sees, as a machine may."""
    return "[ru] " + text.replace("{", "{ ").replace("}", " }")


def _files(tmp_path: Path) -> TranslationFiles:
    return TranslationFiles(Layout(tmp_path / "seed", tmp_path / "web", tmp_path / "taxonomy_translations.py"))


def _run(tmp_path: Path, strings: list[SourceString], machine: _Machine) -> tuple[UiReport, TranslationFiles]:
    files = _files(tmp_path)
    job = UiJob("ru", tuple(strings), GLOSSARY, frozenset())
    return translate_locale(job, MachineTextTranslator(machine), files), files


COUNT_STRINGS = [
    source("documents.count_one", "{count} document", "{count} Dokument"),
    source("documents.count_other", "{count} documents", "{count} Dokumente"),
]


def test_a_russian_plural_family_goes_out_as_representative_numbers_and_each_form_comes_back_for_its_number(
    tmp_path: Path,
) -> None:
    """Plural · a Russian one/few/many/other key yields its four forms from four representative numbers."""
    machine = _Machine(_inflect)

    _report, files = _run(tmp_path, COUNT_STRINGS, machine)

    assert machine.titles == ["1 Dokument", "2 Dokumente", "5 Dokumente", "1,5 Dokumente"]
    stored = files.read("ru")
    assert [stored[f"documents.count_{form}"] for form in ("one", "few", "many", "other")] == [
        "{count} документ",
        "{count} документа",
        "{count} документов",
        "{count} документа",
    ]


def test_the_sample_number_is_not_one_already_in_the_source() -> None:
    """Plural · the sample number is not one already present in the source."""
    assert representative_for("ru", "documents.count_one", "{count} Dokument") == "1"
    assert representative_for("ru", "documents.count_one", "{count} Dokument, Stufe 1") == "21"
    assert representative_for("ru", "documents.count_few", "{count} Dokumente, Stufe 2") == "3"


def test_no_free_sample_leaves_the_count_to_the_placeholder_protection() -> None:
    """Plural · when every sample of a category is already in the source, no sample is chosen."""
    assert representative_for("ru", "documents.count_many", "{count} Dokumente, 5 von 11 von 25") is None


def test_a_key_outside_a_plural_family_or_locale_gets_no_sample() -> None:
    """Plural · a plain key, or a text without {count}, is never given a sample number."""
    assert representative_for("ru", "common.save", "{count} Speichern") is None
    assert representative_for("ru", "documents.count_one", "Dokument") is None


def test_restoring_the_count_replaces_only_the_sample_as_a_whole_number() -> None:
    """Plural · the sample digits go back to {count}; 22, 12,2 and a sample inside another number stay."""
    assert restore_count("2 документа; 22 штуки; 12,2", "2") == "{count} документа; 22 штуки; 12,2"
    assert restore_count("1,5 документа", "1,5") == "{count} документа"
    assert restore_count("документов", None) == "документов"


def _paucal(n: int) -> bool:
    return n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14)


def _cldr_category(locale: str, sample: str) -> str:
    """The CLDR plural category of ``sample`` in ``locale``, for the locales with a sample table."""
    value = Decimal(sample.replace(",", "."))
    n, fraction = int(value), value != int(value)
    if locale == "ro":
        return "one" if n == 1 and not fraction else "few" if fraction or n == 0 or 1 <= n % 100 <= 19 else "other"
    if locale == "tr":
        return "other" if fraction or n != 1 else "one"
    if fraction:
        return "other"
    if locale == "pl":
        return "one" if n == 1 else "few" if _paucal(n) else "many"
    return "one" if n % 10 == 1 and n % 100 != 11 else "few" if _paucal(n) else "many"


def test_the_sample_table_covers_the_locales_and_categories_of_the_plural_table() -> None:
    """Plural · every locale with plural categories has a sample for each of them, and no other."""
    assert set(SAMPLES) == set(PLURAL_CATEGORIES)
    assert all(set(SAMPLES[locale]) == set(PLURAL_CATEGORIES[locale]) for locale in PLURAL_CATEGORIES)


@pytest.mark.parametrize("locale", sorted(PLURAL_CATEGORIES))
def test_every_sample_number_is_one_the_cldr_rules_put_in_its_category(locale: str) -> None:
    """Plural · each sample of a category is selected by the CLDR rules of its locale for that category."""
    for category, samples in SAMPLES[locale].items():
        assert all(_cldr_category(locale, sample) == category for sample in samples), (locale, category)


def test_a_german_placeholder_survives_translation_byte_for_byte(tmp_path: Path) -> None:
    """Placeholders · {name} survives translation byte-for-byte."""
    strings = [source("common.greeting", "Hello {name}", "Hallo {name}")]

    report, files = _run(tmp_path, strings, _Machine(_spaced_braces))

    assert report.rejected == ()
    assert files.read("ru")["common.greeting"] == "[ru] Hallo {name}"


def test_a_placeholder_the_machine_drops_is_a_validation_failure(tmp_path: Path) -> None:
    """Placeholders · a missing placeholder in the output is a validation failure, and the key is not written."""
    strings = [source("common.greeting", "Hello {name}", "Hallo {name}")]

    report, files = _run(tmp_path, strings, _Machine(lambda _text: "[ru] Hallo"))

    assert [rejection.key for rejection in report.rejected] == ["common.greeting"]
    assert "placeholders not preserved: {name}" in report.rejected[0].problems[0]
    assert "common.greeting" not in files.read("ru")


def test_identical_few_and_many_forms_in_ru_are_rejected_by_the_family_validator(tmp_path: Path) -> None:
    """Plural · identical forms for few and many in ru are rejected by the existing family validator."""
    _report, files = _run(tmp_path, COUNT_STRINGS, _Machine(_same_form))

    assert indistinct_slavic_families(files.read("ru")) == ["documents.count"]
