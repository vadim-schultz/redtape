from scripts.import_openplz_locations import _municipality_roles, _stable_uuid


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
