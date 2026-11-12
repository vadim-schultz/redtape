from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from app.config import settings
from app.models import Jurisdiction, JurisdictionKind
from sqlalchemy import select
from sqlalchemy.engine import make_url

API_ROOT = Path(__file__).resolve().parent.parent
REAL_ALEMBIC_DIR = API_ROOT / "alembic"
SCRIPT = API_ROOT / "scripts" / "check_migrations.sh"

CURRENT_HEAD = "20261111_snapshot_translation"

TWO_HEADS_REVISION = '''"""Temp revision that forks the chain (test fixture only)."""

revision = "ci_temp_fork"
down_revision = "20260610_fix_dup_juris"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
'''

BROKEN_DOWNGRADE_REVISION = f'''"""Temp revision with a no-op downgrade (test fixture only)."""

import sqlalchemy as sa
from alembic import op

revision = "ci_temp_broken_downgrade"
down_revision = "{CURRENT_HEAD}"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("ci_temp_table", sa.Column("id", sa.Integer(), primary_key=True))


def downgrade() -> None:
    pass
'''

DRIFT_ENV_PATCH = """
import sqlalchemy as _ci_sa

# Test fixture only: append an untracked column so `alembic check` sees drift.
target_metadata.tables["jurisdiction"].append_column(_ci_sa.Column("ci_temp_untracked", _ci_sa.String(32)))
"""


def _copy_alembic_tree(tmp_path: Path) -> Path:
    """Copy env.py/script.py.mako/versions into tmp_path so a temp chain or a
    patched env.py never touches the real migration files."""

    dest = tmp_path / "alembic"
    shutil.copytree(REAL_ALEMBIC_DIR, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def _write_ini(tmp_path: Path, alembic_dir: Path) -> Path:
    # Base off the real alembic.ini (loggers/handlers/formatters sections are
    # required by env.py's fileConfig call) and repoint script_location only.
    real_ini = (API_ROOT / "alembic.ini").read_text()
    patched = real_ini.replace("script_location = alembic", f"script_location = {alembic_dir}")
    ini_path = tmp_path / "alembic.ini"
    ini_path.write_text(patched)
    return ini_path


def _add_revision(alembic_dir: Path, revision_id: str, content: str) -> None:
    (alembic_dir / "versions" / f"{revision_id}.py").write_text(content)


def _patch_env_py(alembic_dir: Path, patch: str) -> None:
    env_py = alembic_dir / "env.py"
    original = env_py.read_text()
    env_py.write_text(original.replace("target_metadata = Base.metadata", f"target_metadata = Base.metadata\n{patch}"))


def _temp_chain(
    tmp_path: Path,
    *,
    extra_revision: tuple[str, str] | None = None,
    env_patch: str | None = None,
) -> Path:
    """Build an isolated copy of the migration chain, optionally forked with
    an extra revision file and/or a patched env.py, and return its alembic.ini."""

    alembic_dir = _copy_alembic_tree(tmp_path)
    if extra_revision is not None:
        _add_revision(alembic_dir, *extra_revision)
    if env_patch is not None:
        _patch_env_py(alembic_dir, env_patch)
    return _write_ini(tmp_path, alembic_dir)


def _run_check_migrations(ini_path: Path, database_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["ALEMBIC_CONFIG"] = str(ini_path)
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(API_ROOT) + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


@contextmanager
def _fresh_database() -> Iterator[str]:
    """Create a throwaway database on the same server as `settings.database_url`
    and drop it afterwards, so the check never runs against the pytest database."""

    base = make_url(settings.database_url)
    name = f"redtape_ci_migrations_{uuid.uuid4().hex[:8]}"
    admin_dsn = base.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        yield base.set(database=name).render_as_string(hide_password=False)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (name,))
            admin.execute(f'DROP DATABASE IF EXISTS "{name}"')


def test_passes_on_the_current_migration_chain(tmp_path: Path) -> None:
    ini_path = _temp_chain(tmp_path)

    with _fresh_database() as database_url:
        result = _run_check_migrations(ini_path, database_url)

    assert result.returncode == 0, result.stdout + result.stderr


def test_fails_when_two_heads_exist(tmp_path: Path) -> None:
    ini_path = _temp_chain(tmp_path, extra_revision=("ci_temp_fork", TWO_HEADS_REVISION))

    with _fresh_database() as database_url:
        result = _run_check_migrations(ini_path, database_url)

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert CURRENT_HEAD in output
    assert "ci_temp_fork" in output


def test_fails_when_a_downgrade_is_not_implemented(tmp_path: Path) -> None:
    ini_path = _temp_chain(tmp_path, extra_revision=("ci_temp_broken_downgrade", BROKEN_DOWNGRADE_REVISION))

    with _fresh_database() as database_url:
        result = _run_check_migrations(ini_path, database_url)

    assert result.returncode != 0


def test_fails_when_a_model_has_no_migration(tmp_path: Path) -> None:
    ini_path = _temp_chain(tmp_path, env_patch=DRIFT_ENV_PATCH)

    with _fresh_database() as database_url:
        result = _run_check_migrations(ini_path, database_url)

    assert result.returncode != 0
    assert "ci_temp_untracked" in result.stdout + result.stderr


def test_does_not_touch_the_pytest_database(db_session, tmp_path: Path) -> None:
    marker = f"ci-migrations-untouched-{uuid.uuid4().hex[:8]}"
    db_session.add(Jurisdiction(kind=JurisdictionKind.COUNTRY, code=marker))
    db_session.commit()

    ini_path = _temp_chain(tmp_path)
    with _fresh_database() as database_url:
        assert database_url != settings.database_url
        result = _run_check_migrations(ini_path, database_url)

    assert result.returncode == 0, result.stdout + result.stderr
    still_there = db_session.execute(select(Jurisdiction).where(Jurisdiction.code == marker)).scalar_one()
    assert still_there is not None
