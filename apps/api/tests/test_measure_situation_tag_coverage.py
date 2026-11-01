"""The measure_situation_tag_coverage CLI over exported mention data (chapter 4, situation-tag-coverage)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from scripts.measure_situation_tag_coverage import format_table, load_candidates, main
from scripts.situation_tag_coverage_variants import BASELINE, RELAXED_SINGLE_PROCEDURE, VariantCoverage

CANDIDATE_A = uuid.uuid4()
CANDIDATE_B = uuid.uuid4()
PROCEDURE_1 = uuid.uuid4()
PROCEDURE_2 = uuid.uuid4()


def _write_export(path: Path, records: list[dict]) -> Path:
    export_path = path / "export.json"
    export_path.write_text(json.dumps(records))
    return export_path


def test_format_table_renders_one_row_per_variant_with_counts_and_delta() -> None:
    results = [VariantCoverage(BASELINE.name, 6, 0), VariantCoverage(RELAXED_SINGLE_PROCEDURE.name, 41, 35)]

    table = format_table(results)

    assert BASELINE.name in table and "6" in table
    assert RELAXED_SINGLE_PROCEDURE.name in table and "41" in table and "35" in table


def test_load_candidates_groups_export_records_by_candidate_id(tmp_path: Path) -> None:
    records = [
        {"candidate_id": str(CANDIDATE_A), "catalogue_service_id": str(PROCEDURE_1), "situation_codes": ["moving"]},
        {"candidate_id": str(CANDIDATE_A), "catalogue_service_id": str(PROCEDURE_2), "situation_codes": None},
    ]
    export_path = _write_export(tmp_path, records)

    candidates = load_candidates(export_path)

    assert list(candidates.keys()) == [CANDIDATE_A]
    assert len(candidates[CANDIDATE_A]) == 2
    assert candidates[CANDIDATE_A][0] == (PROCEDURE_1, ["moving"])


def test_main_reads_an_export_file_and_prints_the_coverage_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    records = [
        {"candidate_id": str(CANDIDATE_A), "catalogue_service_id": str(PROCEDURE_1), "situation_codes": ["moving"]},
        {"candidate_id": str(CANDIDATE_B), "catalogue_service_id": str(PROCEDURE_1), "situation_codes": None},
    ]
    export_path = _write_export(tmp_path, records)

    exit_code = main(["--input", str(export_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert BASELINE.name in out
    assert RELAXED_SINGLE_PROCEDURE.name in out
