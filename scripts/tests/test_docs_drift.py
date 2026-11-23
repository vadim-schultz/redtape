"""Drift checks for the operator docs and the pipeline activation walkthrough (pipeline-optimisation chapter 15).

One table holds every grep check. A check passes when its pattern matches no line in its files, except a line that
begins with ``History:``, which records what was true before. The link and anchor check covers ``docs/operations/``
and ``.plans/pipeline-optimisation/``. Run it with ``python3 scripts/tests/test_docs_drift.py`` or with pytest.
"""

from __future__ import annotations

import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPERATIONS = REPO_ROOT / "docs" / "operations"
SUITE = REPO_ROOT / ".plans" / "pipeline-optimisation"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ACTIVATION = OPERATIONS / "pipeline-activation.md"
RETIRED_WORKFLOW = WORKFLOWS / "discovery-extract.yml"
HISTORY_PREFIX = "History:"
MAX_WALKTHROUGH_LINES = 150
REQUIRED_STEPS = (1, 2, 3, 4, 5, 6)
STAGE_WORKFLOWS = (
    "discovery-drain.yml",
    "discovery-render.yml",
    "discovery-llm.yml",
    "discovery-screenshot.yml",
    "discovery-translate.yml",
)


@dataclass(frozen=True)
class DriftCheck:
    """One grep check: ``pattern`` must match no line in the files that ``files`` globs from the repository root."""

    name: str
    files: str
    pattern: str


DRIFT_CHECKS: tuple[DriftCheck, ...] = (
    DriftCheck(
        "old drain and render cron times",
        "docs/operations/**/*.md",
        r"(?i)(drain|render)[^\n]*\b0[45]:00\b|\b0[45]:00\b[^\n]*(drain|render)",
    ),
    DriftCheck("old drain group name", "docs/operations/**/*.md", r"group `discovery-drain`"),
    DriftCheck("45-minute skip threshold", "docs/operations/**/*.md", r"\b45 (ledger )?minutes\b"),
    DriftCheck(
        "1,000-minute repository cap",
        "docs/operations/**/*.md",
        r"1,?000 minutes a month|1,?000 minute drain|\(1,?000 minus|1,?000 \(2,?000 minus|capped at 1,?000"
        r"|cap is 1,?000|600 minute CI reserve|600 minute reserve|\(1000\)|\b1,?000 minutes\b",
    ),
    DriftCheck(
        "Actions minutes as a binding limit (D17)",
        "docs/operations/**/*.md",
        r"(?i)minutes (bind|binds)|minute pool|drain allowance|pool runs out|minutes are exhausted",
    ),
    DriftCheck(
        "crawlers S13 and S20 minute figures",
        "docs/operations/crawlers-operator-checklist.md",
        r"(?i)minute[^\n]*\b(1,?000|600)\b|\b(1,?000|600)\b[^\n]*minute",
    ),
    DriftCheck("LLM time 06:00 (is 04:30)", "docs/operations/extraction-operator-checklist.md", r"\b06:00\b"),
    DriftCheck(
        "LLM_ENQUEUE rollback by repository variable",
        "docs/operations/extraction-operator-checklist.md",
        r"LLM_ENQUEUE` back to false",
    ),
    DriftCheck("candidate view: no default drain", "docs/operations/candidate-view.md", r"no default drain handles"),
    DriftCheck(
        "translation engines: hourly quota",
        "docs/operations/translation-engines.md",
        r"hourly quota does not bind",
    ),
    DriftCheck(
        "search-first chapter 6: 6-hour cadence",
        ".plans/search-first/chapters/06-embedding-drain-worker.md",
        r"every 6 hours|6-hour cadence",
    ),
    DriftCheck("retired extract workflow and variables", "docs/operations/**/*.md", r"discovery-extract|DISCOVERY_EXTRACT_"),
)


def _is_history(line: str) -> bool:
    """Return whether ``line`` is a dated record of an earlier state, which the checks allow."""
    return line.lstrip("> -*").startswith(HISTORY_PREFIX)


def _findings_in_text(check: DriftCheck, text: str, label: str) -> list[str]:
    """Return one ``label:line: text`` finding for each line of ``text`` that the check's pattern names."""
    pattern = re.compile(check.pattern)
    return [
        f"{label}:{number}: {line.strip()}"
        for number, line in enumerate(text.splitlines(), 1)
        if pattern.search(line) and not _is_history(line)
    ]


def _findings(check: DriftCheck) -> list[str]:
    """Return every finding of ``check`` across the files it names."""
    found: list[str] = []
    for path in sorted(REPO_ROOT.glob(check.files)):
        if path.is_file():
            label = path.relative_to(REPO_ROOT).as_posix()
            found += _findings_in_text(check, path.read_text(encoding="utf-8"), label)
    return found


def _named(name: str) -> DriftCheck:
    """Return the row of :data:`DRIFT_CHECKS` called ``name``."""
    return next(check for check in DRIFT_CHECKS if check.name == name)


def _expect_none(problems: list[str]) -> None:
    """Fail with every problem in the message when the list is not empty."""
    assert not problems, "\n".join(problems)


# --- the drift table ---------------------------------------------------------------------------------------------------


def test_no_operator_doc_names_the_old_cron_times_for_drain_or_render() -> None:
    """Negative grep: no operator doc gives 04:00 or 05:00 for the drain or the render."""
    _expect_none(_findings(_named("old drain and render cron times")))


def test_no_operator_doc_names_the_1000_cap_as_the_repository_cap() -> None:
    """Negative grep: the 1,000-minute cap is named only on a line that starts with History:."""
    _expect_none(_findings(_named("1,000-minute repository cap")))


def test_the_drift_table_has_no_findings_in_the_operator_docs_or_the_search_first_chapter() -> None:
    """Negative grep for every row of the table, each with its own allowed history lines."""
    _expect_none([finding for check in DRIFT_CHECKS for finding in _findings(check)])


def test_a_drift_check_flags_the_line_it_names_and_skips_history_lines() -> None:
    """Negative path: a planted line is reported with its number; a History: line and a clean line are not."""
    check = _named("old drain group name")
    text = "clean line\nshares the concurrency group `discovery-drain`\nHistory: group `discovery-drain` before 11-23\n"
    assert _findings_in_text(check, text, "doc.md") == ["doc.md:2: shares the concurrency group `discovery-drain`"]


def test_a_clean_text_has_no_drift_findings() -> None:
    """Happy path: text without any named drift passes every row."""
    text = "Daily 02:00 UTC drain; render at 03:00 UTC in group `discovery-pipeline`.\n"
    for check in DRIFT_CHECKS:
        assert _findings_in_text(check, text, "doc.md") == [], check.name


def test_the_stage_cron_times_in_the_docs_match_the_workflows() -> None:
    """Happy path: every stage workflow's cron time appears in the scheduled-jobs runbook."""
    scheduled = (OPERATIONS / "scheduled-jobs.md").read_text(encoding="utf-8")
    for name in STAGE_WORKFLOWS:
        expected = _cron_time(WORKFLOWS / name)
        assert expected in scheduled, f"{name} runs at {expected} but scheduled-jobs.md does not print it"


def _cron_time(path: Path) -> str:
    """Return the single daily ``HH:MM`` cron time of a stage workflow."""
    match = re.search(r'cron: "(\d+) (\d+) \* \* \*"', path.read_text(encoding="utf-8"))
    assert match, f"{path.name} has no single daily cron"
    return f"{int(match.group(2)):02d}:{int(match.group(1)):02d}"


def test_discovery_extract_yml_is_absent() -> None:
    """Happy path: the retired extract workflow is gone."""
    assert not RETIRED_WORKFLOW.exists(), "discovery-extract.yml is still in .github/workflows"


# --- the activation walkthrough ----------------------------------------------------------------------------------------

_HEADING = re.compile(r"^## ", re.MULTILINE)
_STEP = re.compile(r"Step (\d)\b")
REQUIRED_SECTIONS = ("Before anything", "Before enabling any stage")


def _sections(text: str) -> list[tuple[str, str]]:
    """Return ``(title, body)`` for each level-two section of ``text``."""
    parts = _HEADING.split(text)[1:]
    return [(part.split("\n", 1)[0].strip(), part) for part in parts]


def activation_problems(text: str) -> list[str]:
    """Return why ``text`` is not a walkthrough with the required sections, six steps in order, and a no-go per step."""
    sections = _sections(text)
    titles = [title for title, _body in sections]
    problems = [f"missing section '{name}'" for name in REQUIRED_SECTIONS if not any(t.startswith(name) for t in titles)]
    steps = [(int(match.group(1)), body) for title, body in sections if (match := _STEP.match(title))]
    numbers = [number for number, _body in steps]
    if numbers != list(REQUIRED_STEPS):
        problems.append(f"steps are {numbers}, expected {list(REQUIRED_STEPS)} in order")
    problems += [f"Step {number} has no no-go check" for number, body in steps if "No-go" not in body]
    if len(text.splitlines()) > MAX_WALKTHROUGH_LINES:
        problems.append(f"{len(text.splitlines())} lines, more than {MAX_WALKTHROUGH_LINES}")
    return problems


def test_the_activation_walkthrough_has_one_section_per_step_in_order() -> None:
    """Happy path: the six steps are present in order, each with a no-go check, on one page."""
    assert ACTIVATION.exists(), "docs/operations/pipeline-activation.md is missing"
    _expect_none(activation_problems(ACTIVATION.read_text(encoding="utf-8")))


def test_the_walkthrough_check_flags_a_missing_step_and_a_step_without_a_no_go() -> None:
    """Negative path: a walkthrough without step 3, and one whose step 2 has no no-go, both fail."""
    good = "## Before anything\nGo.\n## Before enabling any stage\nGo.\n"
    steps = "".join(f"## Step {n}: a\nGo. No-go: stop.\n" for n in REQUIRED_STEPS)
    assert activation_problems(good + steps) == []
    without_three = good + "".join(f"## Step {n}: a\nGo. No-go: stop.\n" for n in (1, 2, 4, 5, 6))
    assert "steps are [1, 2, 4, 5, 6]" in " ".join(activation_problems(without_three))
    no_go_two = good + steps.replace("## Step 2: a\nGo. No-go: stop.\n", "## Step 2: a\nGo.\n")
    assert "Step 2 has no no-go check" in activation_problems(no_go_two)


# --- the link and anchor check -----------------------------------------------------------------------------------------

_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_HEADING_LINE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")


def _outside_fences(text: str) -> list[str]:
    """Return the lines of ``text`` that are not inside a fenced code block."""
    lines: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced:
            lines.append(line)
    return lines


def _slug(heading: str) -> str:
    """Return the GitHub anchor of a heading: lower case, punctuation removed, spaces as hyphens."""
    plain = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).replace("`", "")
    return re.sub(r"[^\w\- ]", "", plain.strip().lower()).replace(" ", "-")


def _anchors(path: Path) -> set[str]:
    """Return the anchors that the headings of ``path`` define."""
    headings = (_HEADING_LINE.match(line) for line in _outside_fences(path.read_text(encoding="utf-8")))
    return {_slug(match.group(1)) for match in headings if match}


def _check_target(source: Path, target: str) -> str | None:
    """Return why a relative ``target`` in ``source`` does not resolve, or ``None`` when it does."""
    if target.startswith(("http://", "https://", "mailto:")):
        return None
    file_part, _, anchor = target.partition("#")
    destination = source.parent / file_part if file_part else source
    if not destination.exists():
        return "no such file"
    if not anchor or destination.is_dir() or destination.suffix != ".md":
        return None
    return None if anchor in _anchors(destination) else "no such heading"


def broken_links(path: Path) -> list[str]:
    """Return one message for each relative link in ``path`` whose file or heading anchor does not exist."""
    problems: list[str] = []
    for line in _outside_fences(path.read_text(encoding="utf-8")):
        for target in _LINK.findall(re.sub(r"`[^`]*`", "", line)):
            reason = _check_target(path, target)
            if reason:
                problems.append(f"{path.name}: {target} ({reason})")
    return problems


def _link_scope() -> list[Path]:
    """Return every Markdown file of the operator docs and of the pipeline suite."""
    return sorted(OPERATIONS.rglob("*.md")) + sorted(SUITE.rglob("*.md"))


def test_the_docs_link_check_passes_for_the_suite_and_the_operator_docs() -> None:
    """Happy path: no relative link or heading anchor in the operator docs or the suite is broken."""
    _expect_none([problem for path in _link_scope() for problem in broken_links(path)])


def test_the_link_check_accepts_a_resolving_file_link_and_heading_anchor() -> None:
    """Happy path: a file link, a heading anchor in another file, a same-file anchor and an external link all pass."""
    with tempfile.TemporaryDirectory() as root:
        base = Path(root)
        (base / "target.md").write_text("# Scope\n\n## Drain times\n", encoding="utf-8")
        page = base / "page.md"
        page.write_text(
            "# Page top\n\n[times](target.md#drain-times) [self](#page-top) [out](https://example.com/x#y)\n",
            encoding="utf-8",
        )
        assert broken_links(page) == []


def test_the_link_check_reports_a_missing_file_and_a_missing_heading() -> None:
    """Negative path: a link to a missing file and an anchor that no heading defines are both reported."""
    with tempfile.TemporaryDirectory() as root:
        base = Path(root)
        (base / "target.md").write_text("## Drain times\n", encoding="utf-8")
        page = base / "page.md"
        page.write_text("[gone](nope.md) [anchor](target.md#no-such-heading)\n", encoding="utf-8")
        problems = broken_links(page)
        assert len(problems) == 2, problems
        assert "(no such file)" in problems[0] and "(no such heading)" in problems[1]


# --- direct run --------------------------------------------------------------------------------------------------------


def _run_all() -> int:
    """Run every test function in this module and print one line for each; return the process exit code."""
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as error:
            failed += 1
            print(f"FAIL {test.__name__}\n{error}")
        else:
            print(f"ok   {test.__name__}")
    print(f"{len(tests) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
