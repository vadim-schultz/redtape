"""Edge cases of the curation tool: batching, procedures, neighbours, the API's own refusals (chapter 11)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from discovery_ingest.cli import main
from discovery_ingest.curation import MANUAL_EXTRACTOR, CurationFile
from discovery_ingest.curation_plan import plan_curation
from discovery_ingest.curation_run import batches
from discovery_ingest.curation_staged import StagedIndex
from discovery_ingest.emit_models import CandidateSummary
from discovery_ingest.extract.llm.normalise import name_slug

from curate_fakes import (
    ANMELDUNG,
    AUSWEIS,
    EXCERPT_REQUIRES,
    JURISDICTION,
    MELDE,
    SERVICE,
    Api,
    edge,
    entry,
    install,
    write_file,
)


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Api:
    """An API holding three staged candidates and one snapshot for the procedure of Meldebescheinigung."""
    return install(monkeypatch)


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(["candidates", *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _index() -> StagedIndex:
    rows = [(MELDE, "Meldebescheinigung"), (AUSWEIS, "Personalausweis"), (ANMELDUNG, "Anmeldung einer Wohnung")]
    return StagedIndex(
        [
            CandidateSummary.model_validate(
                {
                    "id": str(cid), "jurisdiction_id": str(JURISDICTION), "key": name_slug(title),
                    "title_i18n": {"de": title}, "mention_count": 1, "roles": ["required"],
                }
            )
            for cid, title in rows
        ]
    )  # fmt: skip


def test_the_manual_marker_is_the_value_the_api_overrides_on() -> None:
    """MANUAL_EXTRACTOR · pinned to the literal the API's ``MANUAL_EXTRACTOR`` carries."""
    assert MANUAL_EXTRACTOR == "manual"


def test_batches_split_at_the_bound_and_refuse_a_bound_below_one() -> None:
    """batches · 250 items at 100 make 100, 100, 50; a size of 0 is a ValueError."""
    assert [len(b) for b in batches(list(range(250)), 100)] == [100, 100, 50]
    with pytest.raises(ValueError, match="size"):
        list(batches([1], 0))


def test_a_missing_neighbour_gets_a_manual_mention_only_when_create_is_set() -> None:
    """plan · ``create`` adds one ``manual:neighbour`` mention (role required, the edge's excerpt); a staged one adds none."""
    missing = edge("Geburtsurkunde", EXCERPT_REQUIRES, create=True)
    file = CurationFile.model_validate({"version": 1, "curator": "t", "candidates": [entry(requires=[missing])]})

    plan = plan_curation(file, _index())

    neighbours = [m for m in plan.mentions if m.source_field == "manual:neighbour"]
    assert [(m.title_i18n["de"], m.role, m.excerpt, m.extractor) for m in neighbours] == [
        ("Geburtsurkunde", "required", EXCERPT_REQUIRES, "manual")
    ]
    assert len(plan.mentions) == 2


def test_a_neighbour_typo_without_create_is_refused_naming_the_closest_title(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · ``Personalausweiss`` is not staged and not marked ``create``: refused, the staged title is named."""
    path = write_file(tmp_path, entry(requires=[edge("Personalausweiss", EXCERPT_REQUIRES)]))

    code, _, err = _run(capsys, "curate", "--file", str(path))

    assert code == 2 and api.posts == [] and "Personalausweiss" in err and "Personalausweis" in err


def test_a_procedure_the_candidate_is_not_mentioned_on_is_refused(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · a ``catalogue_service_id`` outside the candidate's procedures is refused and named."""
    other = str(uuid.UUID(int=4242))

    code, _, err = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry(catalogue_service_id=other))))

    assert code == 2 and api.posts == [] and other in err and str(SERVICE) not in err


def test_more_than_sixty_edges_are_refused_before_any_call(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · 61 edges over eight candidates fail the file bound before any call."""
    many = [edge(f"Nachweis {n}", EXCERPT_REQUIRES) for n in range(8)]
    candidates = [entry(requires=many, required_by=many[:1]) for _ in range(7)] + [entry(requires=many[:5])]

    code, _, err = _run(capsys, "curate", "--file", str(write_file(tmp_path, *candidates)))

    assert code == 2 and api.requests == [] and "at most 60" in err


def test_unknown_codes_reported_by_the_api_exit_1(api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """curate · the API dropped a code anyway: the count is in the report and the exit is 1."""
    api.unknown_codes = 1

    code, out, _ = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry())))

    assert code == 1 and "unknown_codes=1" in out


def test_page_reports_a_procedure_without_a_stored_snapshot(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """page · with --out a procedure whose snapshot is missing is named on stderr and the exit is 1."""
    api.sources[MELDE] = [uuid.UUID(int=4242)]

    code, out, err = _run(capsys, "page", "--candidate-id", str(MELDE), "--out", str(tmp_path))

    assert code == 1 and "no html_snapshot" in err and str(uuid.UUID(int=4242)) in err
    assert out.startswith(str(uuid.UUID(int=4242))) and list(tmp_path.iterdir()) == []


def test_a_tag_only_entry_uses_its_note_as_excerpt_and_posts_no_edges(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · codes without edges give one ``manual:tags`` mention whose excerpt is the note, and no edge call."""
    path = write_file(tmp_path, entry(requires=[], required_by=[]))

    code, out, _ = _run(capsys, "curate", "--file", str(path))

    (item,) = api.bodies("mentions")[0]["items"]
    assert code == 0 and item["excerpt"] == "issued when moving" and api.bodies("edges") == []
    assert out.splitlines()[0] == "Meldebescheinigung tags=2 edges=0"


def test_codes_without_a_tag_note_are_refused_before_any_call(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · a curator must say why the codes were chosen: no ``tag_note`` refuses the file."""
    code, _, err = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry(tag_note=None))))

    assert code == 2 and api.requests == [] and "tag_note" in err
