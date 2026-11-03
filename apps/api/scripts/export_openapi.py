"""Write the API's OpenAPI component schemas to the web contract snapshot.

Run from ``apps/api``::

    uv run python scripts/export_openapi.py

The web contract test (``apps/web/src/test/contract``) compares the web enums
and field sets with the file this script writes. ``tests/test_openapi_snapshot.py``
fails when the committed file is stale.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app

REGENERATE_COMMAND = "uv run python scripts/export_openapi.py"
SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "web" / "src" / "test" / "contract" / "openapi.schemas.json"


def render_schemas() -> str:
    """Return the component schemas as sorted, indented JSON with a trailing newline."""
    schema = create_app().openapi_schema.to_schema()
    return json.dumps(schema["components"]["schemas"], indent=2, sort_keys=True) + "\n"


def snapshot_problem(path: Path) -> str | None:
    """Return why the snapshot at ``path`` is not current, or ``None`` when it is."""
    if not path.exists():
        return f"missing {path}; run: {REGENERATE_COMMAND}"
    if path.read_text(encoding="utf-8") != render_schemas():
        return f"stale {path}; run: {REGENERATE_COMMAND}"
    return None


def main() -> None:
    """Write the snapshot file and print its path."""
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(render_schemas(), encoding="utf-8")
    print(f"wrote {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
