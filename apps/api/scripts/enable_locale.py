"""Enable a locale: only with a recorded native-speaker review and 100% coverage of the German keys.

Run from `apps/api`:
  python -m scripts.enable_locale <code>

Seeds never flip ``supported_locale.enabled``; this script is the one guarded way to turn a locale on.
"""

from __future__ import annotations

import sys

import sqlalchemy as sa
from app.db import SessionLocal
from app.features.locales.repository import LocalesRepository
from app.features.locales.service import completeness_pct
from app.models.locale import SupportedLocale
from app.shared.locale import DEFAULT_LOCALE, SUPPORTED_LOCALE_CODES
from sqlalchemy.orm import Session

from scripts.seed_data.review_manifest import MANIFEST_FILE, ReviewManifest, load_review_manifest

FULL = 100.0


class EnableRefusedError(Exception):
    """The locale must not be enabled; the message is the reason, in words an operator can act on."""


def _review_problem(code: str, manifest: ReviewManifest) -> str | None:
    entry = manifest.locales.get(code)
    if entry is None:
        return f"{MANIFEST_FILE} has no entry for {code}; generate and review its strings first"
    if entry.status != "reviewed":
        return f"its review status is {entry.status}; record a native-speaker review in {MANIFEST_FILE} first"
    return None


def _completeness(session: Session, code: str) -> float:
    return completeness_pct(LocalesRepository(session).key_counts_by_locale(DEFAULT_LOCALE), code)


def enable_locale(session: Session, code: str, manifest: ReviewManifest) -> float:
    """Set ``supported_locale.enabled`` for ``code`` and return its completeness; raise :class:`EnableRefusedError` otherwise.

    The locale must be supported, have a ``reviewed`` entry in ``manifest`` and be 100% complete in
    ``ui_translation``. The caller commits.
    """
    if code not in SUPPORTED_LOCALE_CODES:
        raise EnableRefusedError(f"{code} is not a supported locale")
    problem = _review_problem(code, manifest)
    if problem:
        raise EnableRefusedError(f"locale {code} is not enabled: {problem}")
    completeness = _completeness(session, code)
    if completeness < FULL:
        raise EnableRefusedError(
            f"locale {code} is not enabled: completeness {completeness} is below {FULL}; seed its strings first"
        )
    session.execute(sa.update(SupportedLocale).where(SupportedLocale.code == code).values(enabled=True))
    return completeness


def main(argv: list[str] | None = None) -> int:
    """Enable the locale named on the command line; print the result and return the exit code (1 when refused)."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m scripts.enable_locale <code>", file=sys.stderr)
        return 2
    with SessionLocal() as session:
        try:
            completeness = enable_locale(session, args[0], load_review_manifest())
        except EnableRefusedError as err:
            print(str(err), file=sys.stderr)
            return 1
        session.commit()
    print(f"locale {args[0]} enabled (completeness {completeness}%).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
