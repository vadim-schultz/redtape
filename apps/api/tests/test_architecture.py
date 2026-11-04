"""AST-based layering guards (T3).

``schema/`` must not reach ``app.features`` or import an ORM class from
``app.models``; services, repositories and models must not reach ``litestar``
either directly or transitively through their own ``app.*`` imports, except
through a short, named list of hub modules. Pure stdlib: no database fixture,
no import of ``app`` (every check is a static AST walk).
"""

from __future__ import annotations

import ast
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = API_ROOT / "app"

# A-1 allow-list: (path relative to apps/api, fully-qualified import) pairs that
# still reach app.features from schema/. Delete a line when its chapter fixes it.
SCHEMA_FEATURE_ALLOW: frozenset[tuple[str, str]] = frozenset()

# A-2 allow-list: ORM-class imports from schema/. Enums and constants are not here.
SCHEMA_ORM_ALLOW: frozenset[tuple[str, str]] = frozenset(
    {
        ("app/schema/suggestion/read.py", "app.models.suggestion.Suggestion"),  # unassigned; G2 or B2/B3
    }
)

# A-4 allow-list: the only modules through which the A-3 set may reach litestar
# transitively via app.* imports. Delete a line when its chapter removes the import.
LITESTAR_HUBS: frozenset[str] = frozenset(
    {
        "app.shared.list_query.errors",  # unassigned: closest is B5 (domain error mapped in the controller)
        "app.shared.locale",  # B1
        "app.schema.discovery.artifacts",  # B3
        # Found while implementing T3, not in the audit's count: every repository that imports
        # anything from the app.shared.list_query package (not just .errors) pulls in provider.py's
        # litestar import as a side effect of the package __init__ re-exporting provide_list_query.
        "app.shared.list_query.provider",  # unassigned: closest is B5, same as the .errors hub above
    }
)


def module_name_of(path: Path) -> str:
    """Return the dotted module name `path` would have when imported, e.g. app.schema.discovery.read."""
    rel = path.relative_to(APP_ROOT.parent)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_relative(own_dotted: str, is_init: bool, level: int, module: str | None) -> str:
    """Resolve a relative ``from`` import to its absolute dotted path given the importing module's own name."""
    parts = own_dotted.split(".")
    package_parts = parts if is_init else parts[:-1]
    extra_drop = level - 1
    if extra_drop:
        package_parts = package_parts[: len(package_parts) - extra_drop] if extra_drop <= len(package_parts) else []
    prefix = ".".join(package_parts)
    if module:
        return f"{prefix}.{module}" if prefix else module
    return prefix


def module_imports(path: Path, source: str | None = None) -> list[tuple[int, str]]:
    """Return (line, dotted_name) for every import anywhere in `path`'s tree.

    Walks the whole function body, so a function-level import and one guarded by
    ``if TYPE_CHECKING:`` both count. One entry per imported name; relative
    imports are resolved to their absolute dotted path using `path`'s position
    under the API package root. `source` lets a test supply in-memory source
    for a `path` that need not exist on disk; real callers pass only `path`.
    """
    text = path.read_text(encoding="utf8") if source is None else source
    tree = ast.parse(text, filename=str(path))
    own = module_name_of(path)
    is_init = path.name == "__init__.py"
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_relative(own, is_init, node.level, node.module) if node.level else (node.module or "")
            imports.extend((node.lineno, f"{base}.{alias.name}" if base else alias.name) for alias in node.names)
    return imports


def is_low_layer(path: Path) -> bool:
    """True when `path` is a service, repository or model module the litestar-free rules (A-3, A-4) cover."""
    rel = path.relative_to(APP_ROOT)
    parts = rel.parts
    if parts[0] in ("services", "models"):
        return True
    if path.stem == "repository" or "repository" in parts[:-1]:
        return True
    return path.stem == "service" or path.stem.endswith("_service")


def low_layer_files() -> list[Path]:
    """Every module under app/ that A-3 and A-4 cover: services, models, repositories and service modules."""
    return sorted(p for p in APP_ROOT.rglob("*.py") if is_low_layer(p))


def schema_files() -> list[Path]:
    """Every module under app/schema."""
    return sorted((APP_ROOT / "schema").rglob("*.py"))


def _relpath(path: Path) -> str:
    """Return `path` relative to apps/api, posix-style, for allow-list keys and failure messages."""
    return path.relative_to(API_ROOT).as_posix()


def _class_def_has_tablename(node: ast.ClassDef) -> bool:
    """True when `node`'s own body (not an inherited member) assigns ``__tablename__``."""
    return any(
        isinstance(stmt, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__tablename__" for target in stmt.targets)
        for stmt in node.body
    )


def class_assigns_tablename(source: str) -> bool:
    """True when the first class found in `source` assigns ``__tablename__`` directly in its body."""
    tree = ast.parse(source)
    class_def = next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    return _class_def_has_tablename(class_def)


def orm_class_names() -> set[str]:
    """Names of every class under app/models whose body assigns ``__tablename__`` (a SQLAlchemy ORM class)."""
    names: set[str] = set()
    for path in (APP_ROOT / "models").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf8"), filename=str(path))
        names.update(
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and _class_def_has_tablename(node)
        )
    return names


def _feature_hits(path: Path) -> list[tuple[int, str]]:
    """Every import in `path` that reaches app.features.*."""
    return [(lineno, dotted) for lineno, dotted in module_imports(path) if dotted.startswith("app.features.")]


def _orm_hits(path: Path, orm_names: set[str], source: str | None = None) -> list[tuple[int, str]]:
    """Every import in `path` of a name in `orm_names` sourced from somewhere under app.models."""
    hits = []
    for lineno, dotted in module_imports(path, source=source):
        if not dotted.startswith("app.models."):
            continue
        if dotted.rsplit(".", 1)[-1] in orm_names:
            hits.append((lineno, dotted))
    return hits


def _litestar_hits(path: Path, source: str | None = None) -> list[tuple[int, str]]:
    """Every import in `path` that reaches litestar directly."""
    return [
        (lineno, dotted)
        for lineno, dotted in module_imports(path, source=source)
        if dotted == "litestar" or dotted.startswith("litestar.")
    ]


def _app_module_index() -> dict[str, Path]:
    """Map every dotted module name under app/ to its file path."""
    return {module_name_of(path): path for path in APP_ROOT.rglob("*.py")}


def _module_portion(dotted: str, index: dict[str, Path]) -> str | None:
    """The longest prefix of `dotted` that is a known app module, or None when `dotted` is not under app."""
    parts = dotted.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in index:
            return candidate
        parts.pop()
    return None


def _reaches_litestar_outside_hubs(start: Path, index: dict[str, Path]) -> set[str]:
    """BFS over app.* imports from `start`; return non-hub modules reached that import litestar directly.

    The walk does not expand past a hub module: once litestar is reached
    through an allow-listed hub, anything the hub imports beyond that is
    irrelevant to this rule.
    """
    start_name = module_name_of(start)
    visited = {start_name}
    frontier = [start_name]
    offenders: set[str] = set()
    while frontier:
        current = frontier.pop()
        current_path = index[current]
        imports = module_imports(current_path)
        if current != start_name and _litestar_hits(current_path) and current not in LITESTAR_HUBS:
            offenders.add(current)
        if current in LITESTAR_HUBS:
            continue
        for _lineno, dotted in imports:
            if not dotted.startswith("app."):
                continue
            target = _module_portion(dotted, index)
            if target is not None and target not in visited:
                visited.add(target)
                frontier.append(target)
    return offenders


def test_schema_imports_no_feature_module() -> None:
    """schema/ reaches app.features only through the measured, shrinking SCHEMA_FEATURE_ALLOW list."""
    offenders = {(_relpath(path), dotted) for path in schema_files() for _lineno, dotted in _feature_hits(path)}
    unexpected = offenders - SCHEMA_FEATURE_ALLOW
    assert not unexpected, sorted(unexpected)


def test_schema_feature_allow_list_entries_still_violate() -> None:
    """Every SCHEMA_FEATURE_ALLOW entry still imports a feature module; delete it once its chapter fixes it."""
    offenders = {(_relpath(path), dotted) for path in schema_files() for _lineno, dotted in _feature_hits(path)}
    stale = SCHEMA_FEATURE_ALLOW - offenders
    assert not stale, sorted(stale)


def test_schema_imports_no_orm_class() -> None:
    """schema/ imports an ORM class from app.models only through the measured, shrinking SCHEMA_ORM_ALLOW list."""
    orm_names = orm_class_names()
    offenders = {(_relpath(path), dotted) for path in schema_files() for _lineno, dotted in _orm_hits(path, orm_names)}
    unexpected = offenders - SCHEMA_ORM_ALLOW
    assert not unexpected, sorted(unexpected)


def test_schema_orm_allow_list_entries_still_violate() -> None:
    """Every SCHEMA_ORM_ALLOW entry still imports that ORM class; delete it once its chapter fixes it."""
    orm_names = orm_class_names()
    offenders = {(_relpath(path), dotted) for path in schema_files() for _lineno, dotted in _orm_hits(path, orm_names)}
    stale = SCHEMA_ORM_ALLOW - offenders
    assert not stale, sorted(stale)


def test_services_and_repositories_import_no_litestar() -> None:
    """Services, repositories and models never import litestar directly (A-3; the allow-list is empty, a lock)."""
    offenders = [
        (_relpath(path), lineno, dotted) for path in low_layer_files() for lineno, dotted in _litestar_hits(path)
    ]
    assert not offenders, offenders


def test_services_and_repositories_reach_no_litestar_except_through_hubs() -> None:
    """Services, repositories and models reach litestar transitively only through the three allow-listed hubs (A-4)."""
    index = _app_module_index()
    offenders = {
        _relpath(path): reached
        for path in low_layer_files()
        if (reached := _reaches_litestar_outside_hubs(path, index))
    }
    assert not offenders, offenders


def test_litestar_hub_allow_list_entries_still_import_litestar() -> None:
    """Every LITESTAR_HUBS entry still imports litestar directly; delete it once its chapter removes the import."""
    index = _app_module_index()
    stale = [hub for hub in LITESTAR_HUBS if not _litestar_hits(index[hub])]
    assert not stale, stale


def test_import_walker_sees_function_level_and_type_checking_imports() -> None:
    """module_imports walks the whole tree, so an `if TYPE_CHECKING:` import and a function-level import both count."""
    source = (
        "from typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n"
        "    import litestar\n\n"
        "def handler() -> None:\n"
        "    import litestar\n"
    )
    path = APP_ROOT / "services" / "_synthetic.py"
    dotted_names = [dotted for _lineno, dotted in module_imports(path, source=source)]
    assert dotted_names == ["typing.TYPE_CHECKING", "litestar", "litestar"]


def test_import_walker_resolves_relative_imports() -> None:
    """A relative `from` import resolves to its absolute dotted path using the importing module's position."""
    path = APP_ROOT / "schema" / "discovery" / "read.py"
    assert module_imports(path, source="from .artifacts import ArtifactSummaryRead\n") == [
        (1, "app.schema.discovery.artifacts.ArtifactSummaryRead")
    ]
    assert module_imports(path, source="from ..candidate import CandidateFlags\n") == [
        (1, "app.schema.candidate.CandidateFlags")
    ]


def test_orm_class_detection_requires_a_tablename() -> None:
    """A class only counts as an ORM class when its own body assigns `__tablename__`."""
    assert class_assigns_tablename("class Foo(Base):\n    __tablename__ = 'foo'\n") is True
    assert class_assigns_tablename("import enum\n\nclass Bar(enum.StrEnum):\n    A = 'a'\n") is False


def test_a_synthetic_service_importing_litestar_is_flagged() -> None:
    """A made-up service.py importing litestar is both recognised as low-layer and flagged by the walker."""
    path = APP_ROOT / "features" / "voting" / "service.py"
    assert is_low_layer(path) is True
    assert _litestar_hits(path, source="from litestar import Request\n") == [(1, "litestar.Request")]


def test_a_synthetic_schema_importing_an_enum_is_allowed() -> None:
    """Importing a StrEnum from app.models is not an ORM-class import, even though it is under app.models."""
    orm_names = orm_class_names()
    path = APP_ROOT / "schema" / "discovery" / "_synthetic.py"
    source = "from app.models.discovery import DiscoveryTaskKind\n"
    assert "DiscoveryTaskKind" not in orm_names
    assert _orm_hits(path, orm_names, source=source) == []
