"""اختبارات الطبقة المحلية: بطاقة صفر التكلفة، وفحصٌ لا يخذل."""

from __future__ import annotations

import unittest

from maestro.doctor.check import run_doctor
from maestro.routing.local import DEFAULT_LOCAL_BASE_URL, local_profile, ollama_profile


class TestLocalProfiles(unittest.TestCase):
    """بطاقات النموذج المحلي."""

    def test_local_profile_is_free(self) -> None:
        profile = local_profile()
        self.assertEqual(profile.cost_in_per_mtok, 0.0)
        self.assertEqual(profile.cost_out_per_mtok, 0.0)
        self.assertEqual(profile.tier, "local")

    def test_local_profile_needs_no_key(self) -> None:
        self.assertIsNone(local_profile().api_key_env)
        self.assertIsNone(ollama_profile().api_key_env)

    def test_ollama_profile_points_to_the_local_endpoint(self) -> None:
        profile = ollama_profile()
        self.assertEqual(profile.base_url, DEFAULT_LOCAL_BASE_URL)
        self.assertEqual(profile.tier, "local")

    def test_local_cost_is_zero_for_any_volume(self) -> None:
        profile = local_profile()
        self.assertEqual(profile.estimate_cost(1_000_000, 1_000_000), 0.0)


class TestDoctorLocalCheck(unittest.TestCase):
    """فحص الخادم المحلي."""

    def test_local_check_is_optional_and_never_crashes(self) -> None:
        report = run_doctor()
        checks = [check for check in report.checks if check.name == "النموذج المحلي"]
        self.assertEqual(len(checks), 1)
        self.assertFalse(checks[0].required)
        self.assertTrue(checks[0].detail_ar.strip())

    def test_absent_local_server_is_reported_explicitly(self) -> None:
        report = run_doctor()
        check = next(check for check in report.checks if check.name == "النموذج المحلي")
        if check.ok:
            self.skipTest("يوجد خادم محلي في هذه البيئة")
        self.assertIn("غير متاحة", check.detail_ar)


if __name__ == "__main__":
    unittest.main()
