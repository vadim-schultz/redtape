"""Print the situation-axis coverage delta across threshold variants, over an exported mention file.

Run from `apps/api`:
  python -m scripts.measure_situation_tag_coverage --input <export.json>

The export file is a flat JSON list of records, one per mention:
  {"candidate_id": "<uuid>", "catalogue_service_id": "<uuid>", "situation_codes": [...] | null}

Producing that file is a one-off query against ``discovery_candidate_mention``, run by hand (chapter 4,
situation-tag-coverage, LR4) — this module only reads it, it never touches the database.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from uuid import UUID

from app.features.discovery.tags import TaggedMention

from scripts.situation_tag_coverage_variants import VariantCoverage, situation_coverage_by_variant


def load_candidates(path: Path) -> dict[UUID, list[TaggedMention]]:
    """Read an export file and group its mention records by candidate id."""
    records = json.loads(path.read_text())
    by_candidate: dict[UUID, list[TaggedMention]] = defaultdict(list)
    for record in records:
        mention: TaggedMention = (UUID(record["catalogue_service_id"]), record["situation_codes"])
        by_candidate[UUID(record["candidate_id"])].append(mention)
    return dict(by_candidate)


def format_table(results: Sequence[VariantCoverage]) -> str:
    """Return one row per variant: its name, accepted count and newly-covered delta over baseline."""
    rows = [
        f"{row.variant:<40} accepted={row.accepted_candidates:<6} newly_covered={row.newly_covered_candidates}"
        for row in results
    ]
    return "\n".join(rows)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Path to the exported mentions JSON file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Load the export file named by ``--input``, measure coverage per variant and print the table."""
    args = _parse_args(argv)
    candidates: Mapping[UUID, list[TaggedMention]] = load_candidates(args.input)
    print(format_table(situation_coverage_by_variant(candidates)))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
