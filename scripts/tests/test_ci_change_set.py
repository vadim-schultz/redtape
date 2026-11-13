"""Tests for the change-set decision that gates the migration round trip."""

import io

import ci_change_set as cs


def test_ci_change_set_reports_migrations_when_alembic_changes():
    assert cs.migrations_changed(["apps/api/alembic/versions/0042_add_column.py"]) is True


def test_ci_change_set_reports_migrations_when_the_check_script_changes():
    assert cs.migrations_changed(["apps/api/scripts/check_migrations.sh"]) is True


def test_ci_change_set_ignores_api_changes_outside_the_migration_paths():
    paths = ["apps/api/app/routers/candidates.py", "apps/api/tests/test_candidates.py"]
    assert cs.migrations_changed(paths) is False


def test_ci_change_set_ignores_an_empty_change_set():
    assert cs.migrations_changed([]) is False


def test_ci_change_set_does_not_match_a_sibling_name_of_the_alembic_folder():
    assert cs.migrations_changed(["apps/api/alembic_notes.md"]) is False


def test_ci_change_set_writes_the_output_line_to_github_output(tmp_path, monkeypatch):
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr("sys.stdin", io.StringIO("apps/api/alembic/env.py\n"))
    assert cs.main() == 0
    assert output.read_text() == "migrations=true\n"


def test_ci_change_set_writes_false_when_no_migration_path_changed(tmp_path, monkeypatch):
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr("sys.stdin", io.StringIO("apps/web/src/App.tsx\n\n"))
    cs.main()
    assert output.read_text() == "migrations=false\n"
