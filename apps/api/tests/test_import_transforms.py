from scripts.import_openplz_locations import _municipality_roles, _should_import_state, _stable_uuid


def test_stable_uuid_is_deterministic() -> None:
    u1 = _stable_uuid("jurisdiction:MUNICIPALITY:14612")
    u2 = _stable_uuid("jurisdiction:MUNICIPALITY:14612")
    assert u1 == u2


def test_municipality_roles_kreisfreie_stadt() -> None:
    roles = _municipality_roles("Kreisfreie Stadt")
    assert "MUNICIPALITY" in roles
    assert "DISTRICT" in roles


def test_municipality_roles_default() -> None:
    roles = _municipality_roles("Landkreis")
    assert roles == ["MUNICIPALITY"]


def test_should_import_state_with_no_filter_imports_everything() -> None:
    assert _should_import_state("14", None) is True


def test_should_import_state_with_filter_matches_included_code() -> None:
    assert _should_import_state("14", {"14", "09"}) is True


def test_should_import_state_with_filter_excludes_other_codes() -> None:
    assert _should_import_state("09", {"14"}) is False
