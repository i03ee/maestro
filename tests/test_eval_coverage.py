"""اختبارات تغطية التقييم: لا قدرة بلا حالة ولا سبب تأجيل."""

from __future__ import annotations

import unittest

from maestro.evals.cases import CASES, DEFERRED, coverage_report


class TestCoverage(unittest.TestCase):
    """التغطية."""

    def test_no_capability_is_uncovered(self) -> None:
        report = coverage_report()
        self.assertEqual(report["missing"], [])

    def test_no_deferral_for_unknown_capability(self) -> None:
        report = coverage_report()
        self.assertEqual(report["unknown_deferrals"], [])

    def test_covered_plus_deferred_equals_catalogue(self) -> None:
        from maestro.company.catalogue import CAPABILITIES

        report = coverage_report()
        total = len(report["covered"]) + len(report["deferred"])
        self.assertEqual(total, len(CAPABILITIES))

    def test_every_deferral_has_a_reason(self) -> None:
        for name, reason in DEFERRED.items():
            with self.subTest(capability=name):
                self.assertTrue(reason.strip())

    def test_extra_covered_capabilities_are_outside_the_catalogue(self) -> None:
        from maestro.company.catalogue import CAPABILITIES

        known = {capability.name for capability in CAPABILITIES}
        report = coverage_report()
        for name in report["covered_extra"]:
            with self.subTest(capability=name):
                self.assertNotIn(name, known)


class TestCasesAreUnique(unittest.TestCase):
    """الحالات نفسها."""

    def test_case_ids_are_unique(self) -> None:
        ids = [case.id for case in CASES]
        self.assertEqual(len(set(ids)), len(ids))

    def test_every_case_capability_is_known(self) -> None:
        from maestro.company.catalogue import CAPABILITIES, capability_by_name

        known = {capability.name for capability in CAPABILITIES}
        for case in CASES:
            with self.subTest(case=case.id):
                if case.capability in known:
                    continue
                # تخصّص منتج أو قدرة توضيحية: يُسمح بها إن كانت مسجّلة في السجل
                from maestro.evals.runner import eval_registry

                self.assertIsNotNone(eval_registry().get(case.capability))

    def test_every_case_has_a_description_and_a_reply(self) -> None:
        for case in CASES:
            with self.subTest(case=case.id):
                self.assertTrue(case.description_ar.strip())
                self.assertTrue(case.reply.strip())


if __name__ == "__main__":
    unittest.main()
