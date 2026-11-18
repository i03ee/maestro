"""اختبارات الحرّاس: ميزانية صارمة وصلاحيات معلنة."""

from __future__ import annotations

import unittest

from maestro.guards.budget import BudgetExceeded, BudgetGuard
from maestro.guards.permission import PermissionGuard


class TestBudgetGuard(unittest.TestCase):
    """سقف صلب: لا تسامح، ولا «استمرّ ولو غلا»."""

    def test_authorize_accepts_within_remaining(self) -> None:
        guard = BudgetGuard(max_cost_usd=1.0, max_tokens=1000)
        guard.authorize(0.5, 500)

    def test_authorize_rejects_cost_over_ceiling(self) -> None:
        guard = BudgetGuard(max_cost_usd=1.0, max_tokens=1000)
        with self.assertRaises(BudgetExceeded):
            guard.authorize(1.5, 10)

    def test_authorize_rejects_tokens_over_ceiling(self) -> None:
        guard = BudgetGuard(max_cost_usd=1.0, max_tokens=1000)
        with self.assertRaises(BudgetExceeded):
            guard.authorize(0.1, 5000)

    def test_consume_updates_remaining(self) -> None:
        guard = BudgetGuard(max_cost_usd=1.0, max_tokens=1000)
        guard.consume(0.25, 250)
        self.assertEqual(guard.remaining_cost_usd, 0.75)
        self.assertEqual(guard.remaining_tokens, 750)

    def test_second_request_is_blocked_after_consumption(self) -> None:
        guard = BudgetGuard(max_cost_usd=1.0, max_tokens=1000)
        guard.consume(0.9, 900)
        with self.assertRaises(BudgetExceeded):
            guard.authorize(0.5, 10)

    def test_remaining_never_negative(self) -> None:
        guard = BudgetGuard(max_cost_usd=1.0, max_tokens=1000)
        guard.consume(5.0, 5000)
        self.assertEqual(guard.remaining_cost_usd, 0.0)
        self.assertEqual(guard.remaining_tokens, 0)


class TestPermissionGuard(unittest.TestCase):
    """الصلاحية قرار ثنائي: مسموح أو مرفوض، بسبب مكتوب."""

    def setUp(self) -> None:
        self.guard = PermissionGuard(
            allowed_capabilities=frozenset({"media.render", "catalog.ingest"}),
            max_authority=2,
        )

    def test_allowed_capability_passes(self) -> None:
        decision = self.guard.authorize("media.render", 1)
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.reason_ar)

    def test_unknown_capability_is_denied(self) -> None:
        decision = self.guard.authorize("payment.capture", 1)
        self.assertFalse(decision.allowed)
        self.assertIn("payment.capture", decision.reason_ar)

    def test_authority_above_ceiling_is_denied(self) -> None:
        decision = self.guard.authorize("media.render", 3)
        self.assertFalse(decision.allowed)

    def test_authority_three_needs_human_approval(self) -> None:
        guard = PermissionGuard(
            allowed_capabilities=frozenset({"release.publish"}), max_authority=3
        )
        self.assertFalse(guard.authorize("release.publish", 3).allowed)
        self.assertTrue(guard.authorize("release.publish", 3, human_approved=True).allowed)

    def test_recorded_approval_also_passes(self) -> None:
        guard = PermissionGuard(
            allowed_capabilities=frozenset({"release.publish"}),
            max_authority=3,
            approved_capabilities=frozenset({"release.publish"}),
        )
        self.assertTrue(guard.authorize("release.publish", 3).allowed)

    def test_decision_is_serialisable(self) -> None:
        payload = self.guard.authorize("media.render", 1).as_dict()
        self.assertEqual(payload["capability"], "media.render")
        self.assertIs(payload["allowed"], True)


if __name__ == "__main__":
    unittest.main()
