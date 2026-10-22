"""Tests for the code-size measuring script."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from scripts.measure_code_rules import MeasureError, measure_file, summarise

SAMPLE = textwrap.dedent(
    '''
    class Big:
        def short(self, a, b):
            return a

        def long(self, a, b, c, d):
            x = 1
            y = 2
            z = 3
            w = 4
            return x + y + z + w + a


    def helper(a):
        return a
    '''
)


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(text)
    return path


def test_measure_file_reports_class_method_and_parameter_sizes(tmp_path: Path) -> None:
    report = measure_file(_write(tmp_path, SAMPLE))

    assert [(c.name, c.lines) for c in report.classes] == [("Big", 10)]
    methods = {m.name: m for m in report.methods}
    assert methods["short"].lines == 2
    assert methods["long"].lines == 6
    assert methods["long"].parameters == 4  # self excluded
    assert methods["short"].parameters == 2
    assert methods["helper"].parameters == 1


def test_summarise_counts_units_over_the_limits(tmp_path: Path) -> None:
    summary = summarise([measure_file(_write(tmp_path, SAMPLE))], class_limit=5, method_limit=5, param_limit=3)

    assert (summary.classes_over, summary.methods_over, summary.params_over) == (1, 1, 1)


def test_measure_file_rejects_unparsable_input(tmp_path: Path) -> None:
    with pytest.raises(MeasureError, match="sample.py"):
        measure_file(_write(tmp_path, "def broken(:\n"))
