# -*- coding: utf-8 -*-
"""Повреждённые варианты repeat-while: парсер не падает, ошибки осмысленные."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import Scanner
from parser import analyze_syntax


def parse_text(text):
    return analyze_syntax(Scanner(text).scan_tokens())


VALID = """repeat {
    number += 1
} while number < 5;
"""

REPEAT_WHILE_THEN_OK_TAIL = """repeat while 
    number += 1
} while number < 5;
"""

REPEAT_WHILE_THEN_BAD_TAIL = """repeat while 
    number += 1
}  number < 5;
"""

REPEAT_WHILE_THEN_BRACE = """repeat while {
    number += 1
} while number < 5;
"""


class TestParserCorruption(unittest.TestCase):
    def test_valid_baseline(self):
        r = parse_text(VALID)
        self.assertTrue(r.ok, r.errors)

    def test_repeat_while_before_body_then_valid_tail_stray_while_and_brace(self):
        r = parse_text(REPEAT_WHILE_THEN_OK_TAIL)
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 2)
        msgs = [e.message for e in r.errors]
        self.assertTrue(any("лишн" in m for m in msgs))
        self.assertTrue(any("{" in m for m in msgs))
        self.assertEqual(sum(1 for m in msgs if "лишн" in m), 1)

    def test_repeat_while_then_open_brace_only_stray_while_message(self):
        r = parse_text(REPEAT_WHILE_THEN_BRACE)
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("лишн", r.errors[0].message)
        self.assertEqual(r.errors[0].fragment, "while")

    def test_repeat_while_before_body_then_bad_tail_errors(self):
        r = parse_text(REPEAT_WHILE_THEN_BAD_TAIL)
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 3)
        msgs = [e.message for e in r.errors]
        self.assertTrue(any("лишн" in m for m in msgs))
        self.assertTrue(any("{" in m for m in msgs))
        self.assertTrue(any("while" in m.lower() for m in msgs))
        self.assertFalse(
            any("сравнения" in e.message and "+=" in e.fragment for e in r.errors)
        )

    def test_stray_while_variants_messages(self):
        """Разные поломки с лишним while — ожидаемые сигналы в сообщениях."""
        blob = lambda r: " ".join(e.message for e in r.errors).lower()

        r = parse_text(REPEAT_WHILE_THEN_BRACE)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("лишн", blob(r))

        r2 = parse_text("repeat while while {\n    number += 1\n} while number < 5;")
        self.assertEqual(len(r2.errors), 2, [e.message for e in r2.errors])
        self.assertEqual(blob(r2).count("лишн"), 2)

        r3 = parse_text("repeat while }\n    number += 1\n} while number < 5;")
        self.assertIn("лишн", blob(r3))
        self.assertFalse(r3.ok)

    def test_many_corruptions_no_crash(self):
        """Грубые поломки — без исключений; заведомо неверные дают ok=False."""
        must_fail = [
            "repeat {\n    number += 1\n} while number < 5",
            "repeat {\n    number += 1\n} whil number < 5;",
            "repeat {\n    number += 1\n};",
            "repeat {\n    number += 1\n} while number < 5; x",
            "rep#eat {\n    number += 1\n} while number < 5;",
            "repeat \n    number += 1\n} while number < 5;",
            "repeat {\n    number += 1\n while number < 5;",
            REPEAT_WHILE_THEN_OK_TAIL,
            REPEAT_WHILE_THEN_BAD_TAIL,
            "repeat {\n    number += 1\n} while 1 < 5;",
        ]
        also_parse_no_crash = [
            VALID,
            REPEAT_WHILE_THEN_BRACE,
            "repeat { number += 1 } while number < 5;",
            "repeat {\n} while number < 5;",
            "repeat while {\n    number += 1\n} while number < 5;",
            "repeat while while {\n    number += 1\n} while number < 5;",
            "repeat {\n    number += 1\n} while number != 5;",
            "repeat {\n    number += 1\n} while not number < 5;",
        ]
        for i, src in enumerate(must_fail + also_parse_no_crash):
            with self.subTest(i=i):
                try:
                    r = parse_text(src)
                except Exception as e:
                    self.fail("crash: %s\n%s" % (e, src[:100]))
        for i, src in enumerate(must_fail):
            with self.subTest(must_fail_i=i):
                r = parse_text(src)
                self.assertFalse(r.ok, src[:60])
                self.assertTrue(r.errors)


if __name__ == "__main__":
    unittest.main()
