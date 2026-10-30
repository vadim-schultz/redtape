"""``candidates page`` and ``candidates curate`` against a recording stand-in for the machine API (chapter 11)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from discovery_ingest.cli import main
from discovery_ingest.curation import CurationFile
from discovery_ingest.curation_plan import plan_curation
from discovery_ingest.curation_staged import StagedIndex
from discovery_ingest.emit_models import CandidateSummary
from discovery_ingest.extract.clean import clean_page
from discovery_ingest.extract.llm.normalise import name_slug

from curate_fakes import (
    ANMELDUNG,
    AUSWEIS,
    EXCERPT_REQUIRES,
    HOST,
    HTML,
    JURISDICTION,
    MELDE,
    PAGE_URL,
    SERVICE,
    Api,
    edge,
    entry,
    install,
    write_file,
)

TOTALS_FIRST_RUN = "mentions_created=1 mentions_updated=0 edges_created=2 edges_updated=0 edges_skipped=0 unknown_codes=0 dry_run=false"


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Api:
    """An API holding three staged candidates and one snapshot for the procedure of Meldebescheinigung."""
    return install(monkeypatch)


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(["candidates", *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _staged() -> StagedIndex:
    rows = [
        (MELDE, "Meldebescheinigung", ["issued"]),
        (AUSWEIS, "Personalausweis", ["required"]),
        (ANMELDUNG, "Anmeldung einer Wohnung", ["form"]),
    ]
    items = [
        CandidateSummary.model_validate(
            {
                "id": str(cid), "jurisdiction_id": str(JURISDICTION), "key": name_slug(title), "title_i18n": {"de": title},
                "mention_count": 3, "roles": roles,
            }
        )
        for cid, title, roles in rows
    ]  # fmt: skip
    return StagedIndex(items)


def test_page_prints_the_procedures_of_a_candidate(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """page · one line with id, url, host and screenshot flag; the sources call carries candidate_id; no write call."""
    code, out, _ = _run(capsys, "page", "--candidate-id", str(MELDE))

    assert code == 0 and out.split() == [str(SERVICE), PAGE_URL, HOST, "has_screenshot=false"]
    assert api.requests[0].url.params["candidate_id"] == str(MELDE) and api.posts == []


def test_page_writes_the_cleaned_text(api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """page · with --out the file holds exactly the cleaner's output for the stored snapshot."""
    code, _, _ = _run(capsys, "page", "--candidate-id", str(MELDE), "--out", str(tmp_path))

    assert code == 0
    assert (tmp_path / f"{SERVICE}.txt").read_text(encoding="utf-8") == clean_page(HTML, PAGE_URL).text


def test_page_for_an_unknown_candidate_prints_nothing_and_exits_1(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """page · a candidate without procedures: stdout empty, ``no procedures for <id>`` on stderr, exit 1."""
    unknown = uuid.UUID(int=77)

    code, out, err = _run(capsys, "page", "--candidate-id", str(unknown))

    assert code == 1 and out == "" and f"no procedures for {unknown}" in err


def test_plan_turns_a_curated_candidate_into_one_tag_mention_and_its_edges() -> None:
    """plan · one manual tag mention with the codes; ``requires`` makes the candidate the parent, ``required_by`` the child."""
    plan = plan_curation(CurationFile.model_validate(_file(entry())), _staged())

    (tag,) = plan.mentions
    assert (tag.extractor, tag.extractor_version, tag.source_field, tag.role) == (
        "manual",
        "1",
        "manual:tags",
        "issued",
    )
    assert (tag.domain_codes, tag.situation_codes) == (["identity-civil-status"], ["moving-house"])
    assert tag.title_i18n == {"de": "Meldebescheinigung"} and tag.excerpt == EXCERPT_REQUIRES
    assert [(e.parent_title_i18n["de"], e.required_title_i18n["de"]) for e in plan.edges] == [
        ("Meldebescheinigung", "Personalausweis"),
        ("Anmeldung einer Wohnung", "Meldebescheinigung"),
    ]
    assert {(e.basis, e.extractor, e.extractor_version) for e in plan.edges} == {("explicit", "manual", "1")}


def _file(*candidates: dict[str, object]) -> dict[str, object]:
    return {"version": 1, "curator": "test", "candidates": list(candidates)}


def test_curate_posts_mentions_before_edges_and_prints_the_totals(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · mentions then edges, one batch each; one line per candidate and the final report."""
    code, out, _ = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry())))

    assert code == 0
    assert [r.url.path.rsplit("/", 1)[-1] for r in api.posts] == ["mentions", "edges"]
    assert [len(b["items"]) for b in api.bodies("mentions") + api.bodies("edges")] == [1, 2]
    assert out.splitlines() == ["Meldebescheinigung tags=2 edges=2", TOTALS_FIRST_RUN]


def test_curate_is_idempotent(api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """curate · the second run is answered ``updated``: exit 0 and nothing created."""
    path = str(write_file(tmp_path, entry()))
    _run(capsys, "curate", "--file", path)

    code, out, _ = _run(capsys, "curate", "--file", path)

    assert code == 0 and out.splitlines()[-1] == (
        "mentions_created=0 mentions_updated=1 edges_created=0 edges_updated=2 edges_skipped=0 unknown_codes=0 dry_run=false"
    )


def test_dry_run_makes_no_write_call(api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """curate · --dry-run prints the candidate lines and ``dry_run=true`` and only reads."""
    code, out, _ = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry())), "--dry-run")

    assert code == 0 and api.posts == []
    assert out.splitlines()[0] == "Meldebescheinigung tags=2 edges=2" and out.endswith("dry_run=true\n")


def test_unknown_taxonomy_code_fails_the_whole_file(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · a typo in a code refuses the file (exit 2), posts nothing and names the entry and the code."""
    path = write_file(tmp_path, entry(domain_codes=["identity-civil"]))

    code, out, err = _run(capsys, "curate", "--file", str(path))

    assert code == 2 and out == "" and api.posts == []
    assert "Meldebescheinigung" in err and "identity-civil" in err


def test_title_that_does_not_match_a_staged_candidate_is_refused(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · a typo in the title is refused, never a new candidate; the message names the closest staged title."""
    path = write_file(tmp_path, entry(title_de="Meldebescheinigng"))

    code, _, err = _run(capsys, "curate", "--file", str(path))

    assert code == 2 and api.posts == []
    assert "Meldebescheinigng" in err and "Meldebescheinigung" in err


def test_ungrounded_excerpt_is_refused_unless_pages_are_not_checked(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · an invented quote names its entry and posts nothing; --no-check-pages lets it through with a warning."""
    path = str(write_file(tmp_path, entry(requires=[edge("Personalausweis", "Das steht nirgends auf der Seite.")])))

    refused = _run(capsys, "curate", "--file", path)
    assert refused[0] == 2 and api.posts == [] and "Personalausweis" in refused[2] and "excerpt" in refused[2]

    fetched = len(api.requests)
    code, _, err = _run(capsys, "curate", "--file", path, "--no-check-pages")
    assert code == 0 and "warning" in err and len(api.posts) == 2
    assert not any(r.url.path.endswith("/content") for r in api.requests[fetched:])


@pytest.mark.parametrize(
    "requires",
    [
        [edge("Meldebescheinigung", EXCERPT_REQUIRES)],
        [edge("Personalausweis", EXCERPT_REQUIRES), edge("Personalausweis", EXCERPT_REQUIRES)],
    ],
    ids=["self edge", "duplicate edge"],
)
def test_self_edge_and_duplicate_edge_are_refused(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str], requires: list[dict[str, object]]
) -> None:
    """curate · a self edge and a repeated edge fail validation before any call."""
    code, _, err = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry(requires=requires))))

    assert code == 2 and api.requests == [] and "Meldebescheinigung" in err


def test_more_than_eight_candidates_is_refused(api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """curate · nine entries are refused before any call; the message names the bound."""
    code, _, err = _run(capsys, "curate", "--file", str(write_file(tmp_path, *[entry() for _ in range(9)])))

    assert code == 2 and api.requests == [] and "at most 8" in err


def test_skipped_edges_exit_non_zero(api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """curate · the API skips an edge (unknown_parent): exit 1, the count in the report and the reason on stderr."""
    api.skip_required.add("Personalausweis")

    code, out, err = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry())))

    assert code == 1 and "edges_skipped=1" in out
    assert "unknown_parent" in err and "Personalausweis" in err


def test_curation_file_with_an_unknown_key_is_rejected(
    api: Api, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """curate · ``extra="forbid"``: an unknown key refuses the file before any call and is named."""
    code, _, err = _run(capsys, "curate", "--file", str(write_file(tmp_path, entry(), bogus=1)))

    assert code == 2 and api.requests == [] and "bogus" in err
