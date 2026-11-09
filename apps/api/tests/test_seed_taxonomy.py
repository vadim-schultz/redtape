from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
import sqlalchemy as sa
from app.models import Category
from app.shared.taxonomy import contract_loader
from app.shared.taxonomy.contract_loader import load_contract
from scripts.seed_data.category_contract import (
    CATEGORY_INVENTORY,
    LEGACY_CROSSWALK,
    TaxonomyContractError,
    validate_category_inventory,
    validate_legacy_crosswalk,
)
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
API_ROOT = Path(__file__).resolve().parents[1]
APP_ARTIFACT = API_ROOT / "app" / "shared" / "taxonomy" / "category_contract_v1.json"
ACTIVE_CODE_COUNT = 34
SCRIPTS_IMPORT_BLOCKER = """
import importlib.abc
import json
import sys


class _BlockScripts(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "scripts" or fullname.startswith("scripts."):
            raise ImportError(f"scripts import blocked: {fullname}")
        return None


sys.meta_path.insert(0, _BlockScripts())
from app.shared.category_codes import ACTIVE_CATEGORY_CODES

print(json.dumps(sorted(ACTIVE_CATEGORY_CODES)))
"""


def _count(session: Session, table: sa.Table | type) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def test_every_category_has_non_empty_de_and_en_text() -> None:
    for category in CATEGORY_INVENTORY:
        for texts in (category.name_i18n, category.description_i18n):
            assert all(texts.get(locale, "").strip() for locale in ("de", "en"))


def test_category_codes_are_stable_ascii_kebab_case() -> None:
    codes = [category.code for category in CATEGORY_INVENTORY]

    assert all(re.fullmatch(CODE_PATTERN, code) for code in codes)
    assert len(set(codes)) == len(codes)


def test_seed_creates_categories_and_is_idempotent(db_session: Session) -> None:
    seed_canonical_taxonomy(db_session)
    db_session.flush()
    first_count = _count(db_session, Category)

    seed_canonical_taxonomy(db_session)
    db_session.flush()

    assert first_count == len(CATEGORY_INVENTORY)
    assert _count(db_session, Category) == first_count


def test_seed_leaves_an_existing_document_untagged(db_session: Session) -> None:
    from app.models.document import Document
    from app.models.jurisdiction import Jurisdiction, JurisdictionKind
    from app.models.taxonomy import document_category

    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    db_session.add(country)
    db_session.flush()
    db_session.add(Document(slug="some-real-document", title_i18n={"en": "Real"}, jurisdiction_id=country.id))
    db_session.flush()

    seed_canonical_taxonomy(db_session)

    assert _count(db_session, document_category) == 0


def test_taxonomy_every_active_subcategory_has_one_active_root() -> None:
    validate_category_inventory(CATEGORY_INVENTORY)

    active = {category.code: category for category in CATEGORY_INVENTORY if category.is_active}
    for category in active.values():
        if category.parent_code is None:
            continue
        assert active[category.parent_code].parent_code is None


def test_taxonomy_duplicate_or_cyclic_category_inventory_is_rejected() -> None:
    root = next(category for category in CATEGORY_INVENTORY if category.parent_code is None)
    child = next(category for category in CATEGORY_INVENTORY if category.parent_code == root.code)
    duplicate = (*CATEGORY_INVENTORY, root)
    cyclic = (
        replace(root, parent_code=child.code),
        replace(child, parent_code=root.code),
        *(category for category in CATEGORY_INVENTORY if category.code not in {root.code, child.code}),
    )

    with pytest.raises(TaxonomyContractError, match="duplicate"):
        validate_category_inventory(duplicate)
    with pytest.raises(TaxonomyContractError, match="cycle"):
        validate_category_inventory(cyclic)


def test_frozen_crosswalk_has_a_disposition_for_each_legacy_source() -> None:
    """Keep the retired mapping artifact valid even though runtime taxonomy is category-only."""
    validate_legacy_crosswalk(LEGACY_CROSSWALK, CATEGORY_INVENTORY)


def test_category_codes_import_without_scripts_yields_the_active_codes() -> None:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPTS_IMPORT_BLOCKER],
        cwd=API_ROOT,
        env={**os.environ, "PYTHONPATH": str(API_ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    codes = json.loads(result.stdout)
    expected = sorted(category.code for category in CATEGORY_INVENTORY if category.is_active)
    assert len(codes) == ACTIVE_CODE_COUNT
    assert codes == expected


@pytest.mark.parametrize(
    "artifact_bytes",
    [None, b"{not json", b'{"artifact_version": "v1"}'],
    ids=["missing", "not-json", "wrong-shape"],
)
def test_unusable_contract_artifact_raises_on_first_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, artifact_bytes: bytes | None
) -> None:
    from app.shared.category_codes import active_category_codes
    from app.shared.taxonomy import contract_loader
    from app.shared.taxonomy.category_types import TaxonomyContractError

    artifact = tmp_path / "category_contract_v1.json"
    if artifact_bytes is not None:
        artifact.write_bytes(artifact_bytes)
    monkeypatch.setattr(contract_loader, "ARTIFACT_PATH", artifact)
    contract_loader.load_contract.cache_clear()
    try:
        for _ in range(2):
            with pytest.raises(TaxonomyContractError, match="category contract artifact"):
                active_category_codes()
    finally:
        contract_loader.load_contract.cache_clear()


def _load_contract_with_leaf_edited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, leaf_code: str, edit: Callable[[dict[str, object]], None]
) -> None:
    """Point the loader at a copy of the artifact in which one PVOG leaf entry is edited."""
    payload = json.loads(APP_ARTIFACT.read_text(encoding="utf-8"))
    leaf = next(entry for entry in payload["pvog_leaf_mappings"] if entry["leaf_code"] == leaf_code)
    edit(leaf)
    artifact = tmp_path / "category_contract_v1.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(contract_loader, "ARTIFACT_PATH", artifact)
    contract_loader.load_contract.cache_clear()


def test_every_pvog_leaf_is_mapped_with_a_reason_and_an_acceptance_date() -> None:
    """Happy path (D-R9): each PVOG leaf is mapped, with a non-empty reason and an accepted_on date."""
    for mapping in load_contract().pvog_leaf_mappings:
        assert mapping.state == "mapped", mapping.leaf_code
        assert mapping.reason.strip(), mapping.leaf_code
        assert mapping.accepted_on is not None, mapping.leaf_code


def test_pvog_leaf_without_accepted_on_fails_validation_naming_the_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative path (D-R9): a leaf with no acceptance date fails artifact validation and names the leaf."""
    _load_contract_with_leaf_edited(tmp_path, monkeypatch, "1020100", lambda leaf: leaf.pop("accepted_on", None))
    try:
        with pytest.raises(TaxonomyContractError, match="1020100"):
            load_contract()
    finally:
        contract_loader.load_contract.cache_clear()


def test_pvog_review_leaf_without_reason_fails_validation_naming_the_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative path (D-R9): a leaf left in review without a reason fails artifact validation and names the leaf."""
    _load_contract_with_leaf_edited(tmp_path, monkeypatch, "1020100", lambda leaf: leaf.update(reason=""))
    try:
        with pytest.raises(TaxonomyContractError, match="1020100"):
            load_contract()
    finally:
        contract_loader.load_contract.cache_clear()
