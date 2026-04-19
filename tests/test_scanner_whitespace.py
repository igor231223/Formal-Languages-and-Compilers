# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import Scanner, TOKEN_TYPES


class TestScannerWhitespace(unittest.TestCase):
    def test_tab_is_whitespace_token_same_lexeme_label_as_space(self):
        toks = Scanner("x\ty").scan_tokens()
        ws = [t for t in toks if t.code == TOKEN_TYPES["WHITESPACE"][0]]
        self.assertEqual(len(ws), 1)
        self.assertEqual(ws[0].lexeme, "(пробел)")

    def test_tab_no_lexer_error_in_repeat_while(self):
        src = "repeat {\n\tnumber += 1\n} while number < 5;"
        toks = Scanner(src).scan_tokens()
        err_code = TOKEN_TYPES["ERROR"][0]
        self.assertFalse(any(t.code == err_code for t in toks))


if __name__ == "__main__":
    unittest.main()
