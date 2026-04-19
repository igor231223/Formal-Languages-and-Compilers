import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import Scanner
from parser import analyze_syntax


def parse_text(text):
    s = Scanner(text)
    return analyze_syntax(s.scan_tokens())


VALID = """repeat {
    number += 1
} while number < 5;
"""


class TestParserMalformed(unittest.TestCase):
    def test_valid_ok(self):
        r = parse_text(VALID)
        self.assertTrue(r.ok, r.errors)

    def test_missing_open_brace(self):
        r = parse_text("repeat\n    number += 1\n} while number < 5;")
        self.assertFalse(r.ok)
        self.assertTrue(any("{" in e.message for e in r.errors))

    def test_missing_close_brace(self):
        r = parse_text("repeat {\n    number += 1\n while number < 5;")
        self.assertFalse(r.ok)
        msgs = [e.message for e in r.errors]
        self.assertTrue(any("}" in m for m in msgs))

    def test_rep_hash_typo_lexer_and_parser(self):
        r = parse_text("rep#eat {\n    number += 1\n} while number < 5;")
        self.assertFalse(r.ok)
        self.assertTrue(any("rep#eat" in e.fragment for e in r.errors))

    def test_rep_hash_typo_missing_open_brace_like_repeat(self):
        r = parse_text("rep#eat \n    number += 1\n} while number < 5;")
        self.assertFalse(r.ok)
        self.assertTrue(any("{" in e.message for e in r.errors))

    def test_rep_hash_typo_missing_close_brace_three_errors_no_dup_brace(self):
        r = parse_text("rep#eat {\n    number += 1\n while number < 5;")
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 3)
        brace_msgs = [e.message for e in r.errors if "}" in e.message]
        self.assertEqual(len(brace_msgs), 1)

    def test_while_typo_single_clear_error(self):
        r = parse_text("repeat {\n    number += 1\n} whil number < 5;")
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("while", r.errors[0].message.lower())

    def test_no_while_no_spurious_condition_errors(self):
        r = parse_text("repeat {\n    number += 1\n};")
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("while", r.errors[0].message.lower())

    def test_no_trailing_semicolon(self):
        r = parse_text("repeat {\n    number += 1\n} while number < 5")
        self.assertFalse(r.ok)
        self.assertTrue(any(";" in e.message for e in r.errors))

    def test_extra_tokens_rejected(self):
        r = parse_text("repeat {\n    number += 1\n} while number < 5; foo")
        self.assertFalse(r.ok)
        self.assertTrue(any("repeat" in e.message or "Лишн" in e.message for e in r.errors))

    def test_empty_body_still_valid(self):
        r = parse_text("repeat {\n} while number < 5;")
        self.assertTrue(r.ok, r.errors)

    def test_condition_extra_digit_after_rhs_one_error(self):
        r = parse_text(
            "repeat {\n\tnumber += 1\n} while number < 2 5;"
        )
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("5", r.errors[0].fragment)
        self.assertIn(";", r.errors[0].message)
        self.assertFalse(
            any("Лишние символы" in e.message for e in r.errors),
            "не должна дублироваться финальная ошибка про лишние символы",
        )

    def test_condition_digit_left_rejected(self):
        r = parse_text("repeat {\n    number += 1\n} while 1 < 5;")
        self.assertFalse(r.ok)
        self.assertTrue(any("идентификатор" in e.message for e in r.errors))

    def test_missing_brace_condition_fragment_no_false_semicolon_between_stmts(self):
        r = parse_text("repeat \n    number += 1\n  number < 5")
        self.assertFalse(r.ok)
        self.assertFalse(
            any("перед следующим оператором" in e.message for e in r.errors)
        )
        self.assertTrue(any("{" in e.message for e in r.errors))

    def test_rep_hash_condition_fragment_no_false_semicolon_between_stmts(self):
        r = parse_text("rep#eat \n    number += 1\n  number < 5;")
        self.assertFalse(r.ok)
        self.assertFalse(
            any("перед следующим оператором" in e.message for e in r.errors)
        )

    def test_rep_hash_rbrace_instead_of_lbrace_still_needs_closing_rbrace(self):
        r = parse_text("rep#eat }\n    number += 1\n  number < 5\n")
        self.assertFalse(r.ok)
        msgs = [e.message for e in r.errors]
        self.assertTrue(any("Ожидался символ '{'" in m for m in msgs))
        self.assertTrue(any("Ожидался символ '}'" in m for m in msgs))

    def test_rep_hash_body_closed_then_condition_without_while_needs_final_semicolon(self):
        r = parse_text("rep#eat {\n    number += 1\n} number < 5\n")
        self.assertFalse(r.ok)
        msgs = [e.message for e in r.errors]
        self.assertTrue(any("ключевое слово while" in m for m in msgs))
        self.assertTrue(any("конце конструкции" in m and ";" in m for m in msgs))

    def test_rep_hash_condition_in_body_no_mid_statement_semicolon_error(self):
        r = parse_text("rep#eat {\n    number += 1\n number < 5\n")
        self.assertFalse(r.ok)
        self.assertFalse(any("присваивания" in e.message for e in r.errors))
        self.assertFalse(
            any("перед следующим оператором" in e.message for e in r.errors)
        )
        self.assertTrue(any("конце конструкции" in e.message for e in r.errors))

    def test_rep_hash_while_before_open_brace_no_false_brace_or_condition_errors(self):
        r = parse_text("rep#eat while {\n    number += 1\n}  number < 5\n")
        self.assertFalse(r.ok)
        self.assertFalse(
            any("Ожидался символ '{'" in e.message for e in r.errors)
        )
        self.assertFalse(
            any("В условии ожидался идентификатор" in e.message for e in r.errors)
        )
        self.assertTrue(
            any("лишн" in e.message for e in r.errors),
            "ожидается явное сообщение о лишнем while",
        )

    def test_rep_hash_while_before_rbrace_skipped_then_needs_real_while_and_rbrace(self):
        r = parse_text("rep#eat while }\n    number += 1\n number < 5\n")
        self.assertFalse(r.ok)
        msgs = [e.message for e in r.errors]
        self.assertTrue(any("Ожидался символ '{'" in m for m in msgs))
        self.assertTrue(any("Ожидался символ '}'" in m for m in msgs))
        self.assertTrue(any("while" in m.lower() for m in msgs))

    def test_rep_hash_one_stray_rbrace_keeps_following_while_tail(self):
        r = parse_text("rep#eat }\n} while number < 5;")
        self.assertFalse(r.ok)
        parser_msgs = [e.message for e in r.errors if "лексическ" not in e.message]
        self.assertFalse(any("Лишние символы" in m for m in parser_msgs))

    def test_compare_after_incomplete_assign(self):
        r = parse_text("repeat \n    number += \n  number < 5;")
        self.assertFalse(r.ok)
        self.assertTrue(
            any(";" in e.message and "сравнен" in e.message for e in r.errors)
        )

    def test_plus_instead_of_assign_one_error(self):
        r = parse_text("repeat \n    number + 1\n  number < 5;")
        self.assertFalse(r.ok)
        bogus = [e for e in r.errors if "идентификатор или число" in e.message and e.fragment == ""]
        self.assertEqual(len(bogus), 0)

    def test_rep_typo_digit_inside_keyword_one_repeat_error(self):
        r = parse_text(
            "rep3eat {\n\tnumber += 1\n} while number < 5;"
        )
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("repeat", r.errors[0].message.lower())
        self.assertFalse(
            any("идентификатор перед" in e.message for e in r.errors),
            "не должно быть сообщения «лишний идентификатор после repeat», если repeat не было",
        )

    def test_repeat_digit_glued_before_lbrace(self):
        r = parse_text(
            "repeat 23{ \n    number += 1\n} while number < 5;"
        )
        self.assertFalse(r.ok)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("числовой литерал", r.errors[0].message)

    def test_digit_right_after_open_brace_invalid_stmt(self):
        r = parse_text(
            "repeat {2 \n    number += 1\n} while number < 5; "
        )
        self.assertFalse(r.ok)
        blob = " ".join(e.message for e in r.errors)
        self.assertTrue(
            "идентификатор" in blob or "оператор" in blob or "=" in blob,
            blob,
        )

    def test_semicolon_inside_repeat_keyword(self):
        r = parse_text(
            "repe;at {\n    number += 1\n} while number < 5;"
        )
        self.assertFalse(r.ok)
        blob = " ".join(e.message for e in r.errors).lower()
        self.assertIn("repeat", blob)

    def test_body_fragment_without_repeat(self):
        r = parse_text(
            " \n    number + 1\n while < 5"
        )
        self.assertFalse(r.ok)
        blob = " ".join(e.message for e in r.errors).lower()
        self.assertIn("repeat", blob)


if __name__ == "__main__":
    unittest.main()
