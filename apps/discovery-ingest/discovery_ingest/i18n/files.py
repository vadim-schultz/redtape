"""Where a locale lives: the API seed file, its web mirror and the generated taxonomy module."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from discovery_ingest.i18n import taxonomy_module
from discovery_ingest.i18n.flat import dump_json, flatten, unflatten
from discovery_ingest.i18n.strings import TAXONOMY_FIELDS, parse_taxonomy_key, taxonomy_key


@dataclass(frozen=True, slots=True)
class Layout:
    """The three places a locale is written: the API seed directory, an optional web mirror and the taxonomy module."""

    seed_dir: Path
    mirror_dir: Path | None
    taxonomy_module: Path

    @classmethod
    def under(cls, repo_root: Path) -> Layout:
        """Return the layout of a repository checkout rooted at ``repo_root``."""
        seed = repo_root / "apps" / "api" / "scripts" / "seed_data"
        return cls(
            seed / "translations",
            repo_root / "apps" / "web" / "src" / "i18n" / "fallback",
            seed / "taxonomy_translations.py",
        )


def read_flat(path: Path) -> dict[str, str]:
    """Return the nested JSON file at ``path`` as dotted keys."""
    return flatten(json.loads(path.read_text(encoding="utf-8")))


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` through a sibling file, so an interrupted run never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_name(f".{path.name}.tmp")
    scratch.write_text(text, encoding="utf-8")
    os.replace(scratch, path)


class TranslationFiles:
    """Read and write one locale's strings: interface keys in the seed file and its mirror, labels in the module."""

    def __init__(self, layout: Layout) -> None:
        """Keep the layout."""
        self._layout = layout

    def read(self, locale: str) -> dict[str, str]:
        """Return the locale's strings by key (category labels under their ``taxonomy:`` keys); empty when none exist."""
        path = self._layout.seed_dir / f"{locale}.json"
        flat = read_flat(path) if path.is_file() else {}
        for code, locales in taxonomy_module.read(self._layout.taxonomy_module).items():
            if locale in locales:
                flat |= {
                    taxonomy_key(code, field): text
                    for field, text in zip(TAXONOMY_FIELDS, locales[locale], strict=True)
                }
        return flat

    def write(self, locale: str, flat: Mapping[str, str]) -> None:
        """Write the locale's strings whole: the seed file and its mirror, and the locale's labels in the module.

        A category with only one of its two texts is left out, so the module never holds half a label.
        """
        interface = {key: text for key, text in flat.items() if parse_taxonomy_key(key) is None}
        text = dump_json(unflatten(interface))
        for folder in (self._layout.seed_dir, self._layout.mirror_dir):
            if folder is not None:
                _atomic_write(folder / f"{locale}.json", text)
        self._write_labels(locale, flat)

    def _write_labels(self, locale: str, flat: Mapping[str, str]) -> None:
        kept = _without_locale(taxonomy_module.read(self._layout.taxonomy_module), locale)
        merged = _with_locale(kept, locale, _complete_labels(flat))
        _atomic_write(self._layout.taxonomy_module, taxonomy_module.render(merged))


def _without_locale(labels: taxonomy_module.Labels, locale: str) -> taxonomy_module.Labels:
    """Return ``labels`` without ``locale``'s texts; a category left with no locale disappears."""
    stripped = {
        code: {loc: texts for loc, texts in locales.items() if loc != locale} for code, locales in labels.items()
    }
    return {code: locales for code, locales in stripped.items() if locales}


def _with_locale(
    labels: taxonomy_module.Labels, locale: str, texts: Mapping[str, tuple[str, str]]
) -> taxonomy_module.Labels:
    """Return ``labels`` plus ``locale``'s ``(name, description)`` for each category code in ``texts``."""
    codes = sorted({*labels, *texts})
    return {code: {**labels.get(code, {}), **({locale: texts[code]} if code in texts else {})} for code in codes}


def _complete_labels(flat: Mapping[str, str]) -> dict[str, tuple[str, str]]:
    """Return ``code -> (name, description)`` for every category of ``flat`` that has both texts."""
    codes = {parsed[0] for key in flat if (parsed := parse_taxonomy_key(key))}
    return {
        code: (flat[taxonomy_key(code, "name")], flat[taxonomy_key(code, "description")])
        for code in sorted(codes)
        if taxonomy_key(code, "name") in flat and taxonomy_key(code, "description") in flat
    }
