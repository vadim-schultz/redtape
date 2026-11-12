"""The review manifest: per locale a status that stays `machine` until a native review or an operator's acceptance (search-first C11, AZ14)."""

from __future__ import annotations

import ast
import json
from datetime import date
from pathlib import Path
from typing import get_args

import pytest
from discovery_ingest.i18n.manifest import (
    COMMAND_VERSION,
    ReviewManifest,
    Status,
    load_manifest,
    record_generation,
    save_manifest,
)
from pydantic import ValidationError

MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"
API_MANIFEST = Path(__file__).resolve().parents[3] / "apps" / "api" / "scripts" / "seed_data" / "review_manifest.py"


def _accepted(accepted_by: str | None, accepted_on: str | None = "2026-12-03") -> dict[str, str | None]:
    """A machine_accepted entry naming ``accepted_by`` and the date."""
    return {
        "status": "machine_accepted",
        "accepted_by": accepted_by,
        "accepted_on": accepted_on,
        "model": MODEL,
        "command_version": COMMAND_VERSION,
    }


def _api_statuses() -> tuple[str, ...]:
    """The statuses the API's LocaleReview declares, read from its source so the two literals cannot drift apart."""
    tree = ast.parse(API_MANIFEST.read_text(encoding="utf-8"))
    review = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "LocaleReview")
    status = next(
        node
        for node in review.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "status"
    )
    assert isinstance(status.annotation, ast.Subscript)
    return tuple(ast.literal_eval(status.annotation.slice))


def test_the_api_and_ingest_manifests_name_the_same_three_statuses_in_order() -> None:
    """manifest · the API review manifest and this module declare the status literal machine, reviewed, machine_accepted."""
    assert get_args(Status) == _api_statuses() == ("machine", "reviewed", "machine_accepted")


def test_machine_accepted_with_accepted_by_and_accepted_on_validates() -> None:
    """manifest · a machine_accepted entry that names the operator and the date validates."""
    ok = ReviewManifest.model_validate({"locales": {"tr": _accepted("I. Petrov")}})

    assert ok.locales["tr"].accepted_on == date(2026, 12, 3)


@pytest.mark.parametrize("missing", ["accepted_by", "accepted_on"])
def test_machine_accepted_without_accepted_by_or_accepted_on_fails_validation(missing: str) -> None:
    """manifest · machine_accepted without the operator's name or the date is rejected when the manifest loads."""
    entry = _accepted("I. Petrov")
    entry[missing] = None

    with pytest.raises(ValidationError, match="accepted_by and accepted_on"):
        ReviewManifest.model_validate({"locales": {"tr": entry}})


@pytest.mark.parametrize("name", ["I. Petrov", "Claudia Nowak", "Llewellyn Price"])
def test_a_person_whose_name_starts_like_a_tool_is_a_valid_accepting_reviewer(name: str) -> None:
    """manifest · only a translation engine or model name is refused as accepted_by; a person's name is not."""
    ok = ReviewManifest.model_validate({"locales": {"tr": _accepted(name)}})

    assert ok.locales["tr"].accepted_by == name


def test_a_generation_records_a_machine_entry_with_the_model_and_the_command_version(tmp_path: Path) -> None:
    """manifest · a locale that was just generated is `machine`, unreviewed, with model and command version."""
    path = tmp_path / "review.json"

    save_manifest(path, record_generation(load_manifest(path), "tr", model=MODEL, generated=12))

    entry = json.loads(path.read_text(encoding="utf-8"))["locales"]["tr"]
    assert entry == {
        "status": "machine",
        "reviewed_by": None,
        "reviewed_on": None,
        "model": MODEL,
        "command_version": COMMAND_VERSION,
    }


def test_new_strings_demote_a_reviewed_locale_but_an_empty_run_keeps_the_review(tmp_path: Path) -> None:
    """manifest · machine text added after a review needs a new review; a run that added nothing changes nothing."""
    path = tmp_path / "review.json"
    path.write_text(
        json.dumps(
            {
                "locales": {
                    "pl": {
                        "status": "reviewed",
                        "reviewed_by": "A. Nowak",
                        "reviewed_on": "2026-12-01",
                        "model": MODEL,
                        "command_version": COMMAND_VERSION,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    reviewed = load_manifest(path)

    assert record_generation(reviewed, "pl", model=None, generated=0).locales["pl"].status == "reviewed"
    demoted = record_generation(reviewed, "pl", model=MODEL, generated=3).locales["pl"]
    assert (demoted.status, demoted.reviewed_by, demoted.reviewed_on) == ("machine", None, None)


def test_a_reviewed_entry_must_name_the_reviewer_and_the_date() -> None:
    """manifest · `reviewed` without `reviewed_by` and `reviewed_on` is rejected when the manifest loads."""
    entry = {"status": "reviewed", "reviewed_by": None, "reviewed_on": None, "model": MODEL, "command_version": "1"}

    with pytest.raises(ValidationError, match="reviewed_by"):
        ReviewManifest.model_validate({"locales": {"ru": entry}})
    ok = ReviewManifest.model_validate(
        {"locales": {"ru": {**entry, "reviewed_by": "I. Petrov", "reviewed_on": "2026-12-02"}}}
    )
    assert ok.locales["ru"].reviewed_on == date(2026, 12, 2)


def test_a_missing_manifest_is_empty_and_the_file_is_written_sorted_with_a_trailing_newline(tmp_path: Path) -> None:
    """manifest · no file means no entries; saving sorts locales and ends with one newline."""
    path = tmp_path / "review.json"
    assert load_manifest(path).locales == {}

    first = record_generation(load_manifest(path), "uk", model=MODEL, generated=1)
    manifest = record_generation(first, "pl", model=MODEL, generated=1)
    save_manifest(path, manifest)

    text = path.read_text(encoding="utf-8")
    assert list(json.loads(text)["locales"]) == ["pl", "uk"] and text.endswith("}\n")
