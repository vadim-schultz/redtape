"""The promotion split: reads stay on DocumentService, writes and their lookups sit behind PromotionPort (B3, L6)."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

from app.features.documents.promotion import DocumentPromotion, PromotionPort
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from sqlalchemy.orm import Session

APP_ROOT = Path(__file__).resolve().parent.parent / "app"
PROMOTION_NAMES = {
    "create_from_suggestion",
    "create_requirement_from_suggestion",
    "find_conflicts",
    "get_document_jurisdiction",
    "requirement_exists",
    "requires_directly",
    "resolve_jurisdiction_id",
}


def _documents_attributes_used_by(path: Path) -> set[str]:
    """Attribute names called on ``self._documents`` in one module (an AST scan, no import)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "_documents"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "self"
        ):
            names.add(node.attr)
    return names


def test_document_service_has_no_promotion_methods() -> None:
    public = {name for name in vars(DocumentService) if not name.startswith("_")}

    assert public & PROMOTION_NAMES == set()


def test_promotion_port_covers_every_call_the_suggestion_feature_makes() -> None:
    suggestions = APP_ROOT / "features" / "suggestions"
    used = _documents_attributes_used_by(suggestions / "handlers.py") | _documents_attributes_used_by(
        suggestions / "service.py"
    )
    port_methods = {name for name in vars(PromotionPort) if not name.startswith("_")}

    assert used <= port_methods
    assert used == {
        "create_document",
        "create_requirement",
        "existing_requirement",
        "find_conflicts",
        "jurisdiction_of_document",
        "requires_directly",
        "resolve_jurisdiction_id",
    }


def test_document_promotion_satisfies_the_port_at_runtime(db_session: Session) -> None:
    promotion = DocumentPromotion(DocumentRepository(db_session))

    assert isinstance(promotion, PromotionPort)


def test_resolve_jurisdiction_id_by_municipality_code_by_id_and_unknown(db_session: Session) -> None:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    code = f"M{uuid.uuid4().hex[:8]}"
    municipality = Jurisdiction(kind=JurisdictionKind.MUNICIPALITY, name_i18n={"en": "Town"}, code=code)
    db_session.add_all([country, municipality])
    db_session.flush()
    promotion = DocumentPromotion(DocumentRepository(db_session))

    by_code = promotion.resolve_jurisdiction_id(jurisdiction_id=None, municipality_code=code)
    by_id = promotion.resolve_jurisdiction_id(jurisdiction_id=country.id, municipality_code=None)
    unknown = promotion.resolve_jurisdiction_id(jurisdiction_id=uuid.uuid4(), municipality_code=None)

    assert by_code == municipality.id
    assert by_id == country.id
    assert unknown is None
