import unittest

from scripts.import_openplz_locations import _municipality_roles, _stable_uuid


class TestImportTransforms(unittest.TestCase):
    def test_stable_uuid_is_deterministic(self) -> None:
        u1 = _stable_uuid("jurisdiction:MUNICIPALITY:14612")
        u2 = _stable_uuid("jurisdiction:MUNICIPALITY:14612")
        self.assertEqual(u1, u2)

    def test_municipality_roles_kreisfreie_stadt(self) -> None:
        roles = _municipality_roles("Kreisfreie Stadt")
        self.assertIn("MUNICIPALITY", roles)
        self.assertIn("DISTRICT", roles)

    def test_municipality_roles_default(self) -> None:
        roles = _municipality_roles("Landkreis")
        self.assertEqual(roles, ["MUNICIPALITY"])


if __name__ == "__main__":
    unittest.main()

