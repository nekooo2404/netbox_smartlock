from datetime import date

from django.test import SimpleTestCase

from netbox_smartlock.mapping import (
    WARRANTY_STATE_EXPIRED,
    WARRANTY_STATE_EXPIRING,
    WARRANTY_STATE_MISSING,
    WARRANTY_STATE_VALID,
    get_warranty_state,
    normalize_text,
)


class SmartLockMappingTest(SimpleTestCase):
    def test_normalize_text_strips_whitespace_and_handles_empty_values(self):
        self.assertEqual(normalize_text("  SL-001  "), "SL-001")
        self.assertEqual(normalize_text(None), "")

    def test_warranty_state_contract(self):
        today = date(2026, 5, 24)

        self.assertEqual(get_warranty_state(None, today=today), WARRANTY_STATE_MISSING)
        self.assertEqual(get_warranty_state(date(2026, 5, 23), today=today), WARRANTY_STATE_EXPIRED)
        self.assertEqual(get_warranty_state(date(2026, 6, 10), today=today), WARRANTY_STATE_EXPIRING)
        self.assertEqual(get_warranty_state(date(2026, 7, 1), today=today), WARRANTY_STATE_VALID)

