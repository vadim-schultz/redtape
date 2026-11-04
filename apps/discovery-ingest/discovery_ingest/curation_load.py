"""Read a curation file and turn every way it can be wrong into a list of lines naming the entry and field."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from discovery_ingest.curation import CurationFile


class CurationError(Exception):
    """The file cannot be used; ``problems`` is one line per fault."""

    def __init__(self, problems: list[str]) -> None:
        """Keep every fault line so callers can report all of them, not only the first."""
        self.problems = problems
        super().__init__("; ".join(problems))


def _lines(err: ValidationError) -> list[str]:
    return [f"{'.'.join(str(part) for part in e['loc']) or 'file'}: {e['msg']}" for e in err.errors()]


def load_curation_file(path: Path) -> CurationFile:
    """Return the validated file at ``path``; raise :class:`CurationError` for unreadable, invalid or oversized input."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise CurationError([f"{path}: {err}"]) from err
    try:
        return CurationFile.model_validate(raw)
    except ValidationError as err:
        raise CurationError(_lines(err)) from err
