"""The review manifest: per locale a status that stays `machine` until a native speaker's review is recorded (search-first C11)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from discovery_ingest.i18n.manifest import COMMAND_VERSION, ReviewManifest, load_manifest, record_generation, save_manifest
from pydantic import ValidationError

MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"


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
    ok = ReviewManifest.model_validate({"locales": {"ru": {**entry, "reviewed_by": "I. Petrov", "reviewed_on": "2026-12-02"}}})
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

