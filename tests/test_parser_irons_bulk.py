# -*- coding: utf-8 -*-
"""Массовая проверка нейтрализации ошибок (метод Айронса): без падений, осмысленные диагностики."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import Scanner
from parser import analyze_syntax


def parse_text(text):
    return analyze_syntax(Scanner(text).scan_tokens())


BODY = "    number += 1\n"
TAIL = "} while number < 5;"
OPEN = "repeat {\n"
VALID = OPEN + BODY + TAIL


def _variants():
    v = []
    v.append(("valid_exact", VALID, True))
    v.append(("dup_open_brace", "repeat { {\n" + BODY + TAIL, False))
    v.append(("dup_open_two", "repeat { { {\n" + BODY + TAIL, False))
    v.append(("dup_close_before_while", "repeat {\n" + BODY + "} } while number < 5;", False))
    v.append(("dup_close_three", "repeat {\n" + BODY + "} } } while number < 5;", False))
    v.append(("repeat_repeat", "repeat repeat {\n" + BODY + TAIL, False))
    v.append(("repeat_repeat_repeat", "repeat repeat repeat {\n" + BODY + TAIL, False))
    v.append(("cyrillic_garbage", "repeat \u0432\u0430\u0443{\n" + BODY + TAIL, False))
    v.append(("while_before_brace", "repeat while {\n" + BODY + TAIL, False))
    v.append(("while_twice_brace", "repeat while while {\n" + BODY + TAIL, False))
    v.append(("while_then_body", "repeat while\n" + BODY + TAIL, False))
    v.append(("missing_semi", "repeat {\n" + BODY + "} while number < 5", False))
    v.append(("missing_while_kw", "repeat {\n" + BODY + "} number < 5;", False))
    v.append(("missing_open", "repeat\n" + BODY + TAIL, False))
    v.append(("missing_close", "repeat {\n" + BODY + " while number < 5;", False))
    v.append(("whil_typo", "repeat {\n" + BODY + "} whil number < 5;", False))
    v.append(("extra_after", "repeat {\n" + BODY + TAIL + " x", False))
    v.append(("empty_body", "repeat {\n} while number < 5;", True))
    v.append(("one_line_body", "repeat { number += 1 } while number < 5;", True))
    v.append(("spaces", "repeat  {  \n" + BODY + "  }  while  number  <  5  ;", True))
    v.append(("not_not", "repeat {\n" + BODY + "} while not not number < 5;", False))
    v.append(("compound", "repeat {\n    n += 1\n} while n < 5;", True))
    v.append(("rbrace_instead_lbrace", "repeat }\n" + BODY + TAIL, False))
    v.append(("semicolon_instead_lbrace", "repeat ;\n" + BODY + TAIL, False))
    v.append(("while_instead_lbrace", "repeat while\n" + BODY + TAIL, False))
    v.append(("double_semi_tail", "repeat {\n" + BODY + "} while number < 5;;", False))
    v.append(("no_space_brace", "repeat {" + BODY + TAIL, True))
    v.append(("newline_only_body_gap", "repeat {\n\n" + BODY + TAIL, True))
    for k in range(2, 7):
        s = "repeat " + ("{" * k) + "\n" + BODY + TAIL
        v.append(("multi_open_%d" % k, s, False))
    for k in range(2, 5):
        closes = "}" * k
        s = "repeat {\n" + BODY + closes + " while number < 5;"
        v.append(("multi_close_%d" % k, s, False))
    v.append(("rep_hash", "rep#eat {\n" + BODY + TAIL, False))
    v.append(("and_in_cond", "repeat {\n" + BODY + "} while number < 5 and number < 6;", True))
    v.append(("or_in_cond", "repeat {\n" + BODY + "} while number < 5 or number < 6;", True))
    v.append(("digit_bad_cond", "repeat {\n" + BODY + "} while 1 < 5;", False))
    v.append(
        (
            "assign_in_body_two_semi",
            "repeat {\n    number += 1;\n    number += 2\n} while number < 5;",
            True,
        )
    )
    v.append(("two_stmts", "repeat {\n    a += 1;\n    b += 2\n} while b < 5;", True))
    v.append(("trailing_nl", "repeat {\n" + BODY + TAIL + "\n", True))
    v.append(("repeat_lower_repeat", "Repeat {\n" + BODY + TAIL, False))
    v.append(("brace_then_while_garbage", "repeat {\n" + BODY + "} foo while number < 5;", False))
    v.append(("missing_compare", "repeat {\n" + BODY + "} while number ;", False))
    v.append(("missing_rhs", "repeat {\n" + BODY + "} while number < ;", False))
    v.append(("triple_while_prefix", "repeat while while while {\n" + BODY + TAIL, False))
    v.append(("brace_newline_repeat", "repeat {\nrepeat {\n" + BODY + TAIL, False))
    v.append(("id_then_brace", "repeat x {\n" + BODY + TAIL, False))
    v.append(("id_chain_then_brace", "repeat xx yy {\n" + BODY + TAIL, False))
    v.append(("while_rbrace_swap", "repeat {\n" + BODY + "while } number < 5;", False))
    v.append(("only_repeat", "repeat", False))
    v.append(("repeat_brace_eof", "repeat {", False))
    v.append(("repeat_while_eof", "repeat {\n" + BODY + "} while", False))
    v.append(("unclosed_string_like", "repeat {\n    number += 1\n} while number < 5", False))
    v.append(("extra_paren_none", "repeat {\n    number += 1\n} while (number < 5);", False))
    v.append(("two_compare", "repeat {\n" + BODY + "} while number < 5 < 6;", False))
    v.append(("not_cond", "repeat {\n" + BODY + "} while not number < 5;", True))
    v.append(("tab_body", "repeat {\n\tnumber += 1\n} while number < 5;", True))
    for i in range(12):
        v.append(
            (
                "pad_repeat_%d" % i,
                "repeat" + (" " * (i % 4)) + "{\n" + BODY + TAIL,
                True,
            )
        )
    assert len(v) >= 50, len(v)
    return v


class TestParserIronsBulk(unittest.TestCase):
    def test_at_least_fifty_variants_registered(self):
        self.assertGreaterEqual(len(_variants()), 50)

    def test_all_variants_parse_without_crash(self):
        for name, src, _ in _variants():
            with self.subTest(name=name):
                try:
                    parse_text(src)
                except Exception as e:
                    self.fail("%s: %s" % (name, e))

    def test_valid_flags_match_ok(self):
        for name, src, want_ok in _variants():
            with self.subTest(name=name):
                r = parse_text(src)
                if want_ok:
                    self.assertTrue(r.ok, (name, [e.message for e in r.errors]))
                else:
                    self.assertFalse(r.ok, name)
                    self.assertTrue(r.errors, name)

    def test_dup_open_brace_has_body_message(self):
        r = parse_text("repeat { {\n" + BODY + TAIL)
        self.assertFalse(r.ok)
        self.assertTrue(any("Лишняя '{'" in e.message for e in r.errors))

    def test_dup_close_has_extra_brace_message(self):
        r = parse_text("repeat {\n" + BODY + "} } while number < 5;")
        self.assertFalse(r.ok)
        self.assertTrue(any("Лишняя '}'" in e.message for e in r.errors))

    def test_repeat_repeat_has_duplicate_repeat_message(self):
        r = parse_text("repeat repeat {\n" + BODY + TAIL)
        self.assertFalse(r.ok)
        self.assertTrue(any("Лишнее ключевое слово repeat" in e.message for e in r.errors))

    def test_cyrillic_prefixed_ids_have_stray_id_messages(self):
        r = parse_text("repeat \u0432\u0430\u0443{\n" + BODY + TAIL)
        self.assertFalse(r.ok)
        blob = " ".join(e.message for e in r.errors)
        self.assertIn("идентификатор", blob)
        self.assertIn("repeat", blob.lower())


if __name__ == "__main__":
    unittest.main()
