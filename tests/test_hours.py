"""Hours normalization must not turn missing or unsupported evidence into certainty."""

import unittest

from spoonmaster.hours import parse_weekly_hours


class HoursTests(unittest.TestCase):
    def test_all_day_and_split_shifts(self):
        result = parse_weekly_hours("Mo-Fr 11:30-14:00,17:00-22:00; Sa-Su 12:00-23:00")
        self.assertEqual(result["status"], "parsed_weekly")
        self.assertEqual(result["weekly"]["Mo"], [[690, 840], [1020, 1320]])
        self.assertEqual(result["weekly"]["Su"], [[720, 1380]])
        self.assertEqual(parse_weekly_hours("24/7")["weekly"]["Fr"], [[0, 1440]])

    def test_overnight_and_closed_days(self):
        result = parse_weekly_hours("Fr-Mo 18:00-02:00; Tu-Th off")
        self.assertEqual(result["weekly"]["Su"], [[1080, 1560]])
        self.assertEqual(result["weekly"]["Tu"], [])
        self.assertEqual(parse_weekly_hours("12:00-24:00")["weekly"]["Mo"], [[720, 1440]])

    def test_unsupported_expressions_are_wholly_unknown(self):
        expressions = [
            None,
            "",
            "Mo-Su 11:00-22:00; PH off",
            "Mo-Su,PH 11:30-23:30",
            "sunrise-sunset",
            "2026 Nov 01-30 11:00-22:00",
            "Mo 12:00+",
            "Mo-Fr 11:00-22:00; Mo off",
            "Mo 25:00-26:00",
            "Mo 11:60-23:00",
            "Mo 12:00-24:01",
            "Mo 24:00-02:00",
            "Mo 11:00-11:00",
            "Mo 11:00-20:00; nonsense",
            "Mo,Mo 11:00-20:00",
            'Mo 11:00-22:00 "call us"',
            "x" * 513,
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                result = parse_weekly_hours(expression)
                self.assertEqual(result["status"], "unknown")
                self.assertIsNone(result["weekly"])

    def test_unspecified_days_are_not_reported_as_closed(self):
        self.assertNotIn("Tu", parse_weekly_hours("Mo 11:00-22:00")["weekly"])
