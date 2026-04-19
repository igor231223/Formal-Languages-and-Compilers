# -*- coding: utf-8 -*-
"""200 + 100 заведомо искажённых программ: разбор без падения, ok == False, есть ошибки."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import Scanner
from parser import analyze_syntax

BODY = "    number += 1\n"
TAIL = "} while number < 5;"
OPEN = "repeat {\n"
VALID = OPEN + BODY + TAIL


def parse_text(text):
    return analyze_syntax(Scanner(text).scan_tokens())


def _build_200_corrupt_sources():
    """Генерация без случайного совпадения с VALID."""
    xs = []
    xs.append("repeat }{ \n" + BODY + TAIL)

    for i in range(99):
        nb = i % 7
        na = (i % 5) + 1
        if nb == 0 and na == 1:
            na = 2
        xs.append("repeat " + ("}" * nb) + ("{" * na) + "\n" + BODY + TAIL)

    for i in range(50):
        k = 2 + (i % 4)
        xs.append("repeat {\n" + BODY + ("}" * k) + " while number < 5;")

    prefixes = (
        "rep",
        "repea",
        "repeet",
        "repeat repeat",
        "repeat while",
        "repeat }}{",
        "repeat ;;",
        "repeat x",
        "repeat 123",
        "repeat @",
    )
    for i in range(50):
        p = prefixes[i % len(prefixes)]
        xs.append(p + " {\n" + BODY + TAIL)

    assert len(xs) == 200, len(xs)
    return xs


def _build_100_extra_corrupt_sources():
    """Ещё 100 других поломок (цифры у repeat, мусор в теле, обрывки без repeat, опечатки)."""
    b = BODY
    t = TAIL
    xs = []
    for i in range(35):
        xs.append("repeat %d{\n" % (i * 11 + 1) + b + t)
    for i in range(30):
        xs.append("repeat {%d\n" % ((i * 3) % 17) + b + t)
    splits = (
        "repe;at {\n",
        "rep;eat {\n",
        "repea;t {\n",
        "repeat a;t {\n",
        "repeat {;\n",
        "repeat };{\n",
        "repeat {{;\n",
    )
    for i in range(15):
        xs.append(splits[i % len(splits)] + b + t)
    loose = (
        "number + 1\n while number < 5;",
        "    number + 1\n while < 5",
        "repeat {\n    number + 1\n" + t,
        "repeat {\n    number +=\n" + t,
        "repeat {\n    x +=\n} while x < 5;",
        "while number < 5;",
        "repeat {\n} while ;",
        "repeat {\n} while number < ;",
        "repeat {\n    number += 1;\n} while number < 5;;",
        "repeat\n" + b + t,
        "Repeat {\n" + b + t,
        "repeat {\n" + b + "} whil number < 5;",
        "repeat {\n" + b + "} while number < 5\n",
        "repeat {\n" + b + "} while number 5;",
        "repeat {\n" + b + "} while (number < 5);",
        "repeat {\n    number += 1;\n    ;\n" + t,
        "repeat {}}\n" + b + t,
        "repeat {{\n" + b + t,
        "repeat }\n" + b + t,
        "repeat ;;{\n" + b + t,
    )
    for i in range(20):
        xs.append(loose[i % len(loose)])
    assert len(xs) == 100, len(xs)
    return xs


def _build_all_300_corrupt_sources():
    return _build_200_corrupt_sources() + _build_100_extra_corrupt_sources()


class TestParserCorrupt200(unittest.TestCase):
    def test_exactly_three_hundred_variants(self):
        self.assertEqual(len(_build_all_300_corrupt_sources()), 300)

    def test_exactly_two_hundred_base_variants(self):
        self.assertEqual(len(_build_200_corrupt_sources()), 200)

    def test_repeat_rbrace_before_lbrace_reports_error(self):
        r = parse_text("repeat }{ \n" + BODY + TAIL)
        self.assertFalse(r.ok)
        blob = " ".join(e.message for e in r.errors).lower()
        self.assertIn("}", blob)
        self.assertTrue(
            "недопустим" in blob or "ожидался" in blob,
            "expected brace-related wording, got: %r" % r.errors,
        )

    def test_all_three_hundred_parse_and_fail(self):
        for i, src in enumerate(_build_all_300_corrupt_sources()):
            with self.subTest(i=i):
                try:
                    r = parse_text(src)
                except Exception as e:
                    self.fail("crash at %s: %s\n%s" % (i, e, src[:120]))
                self.assertFalse(
                    r.ok,
                    "variant %i should be invalid\n%s" % (i, src[:120]),
                )
                self.assertTrue(r.errors, "variant %i needs diagnostics" % i)


if __name__ == "__main__":
    unittest.main()
