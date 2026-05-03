from scanner import TOKEN_TYPES


CODE_REPEAT = 1
CODE_WHILE = 2
CODE_IDENTIFIER = 3
CODE_WHITESPACE = 4
CODE_LBRACE = 5
CODE_COMPOUND_ASSIGN = 6
CODE_DIGIT = 7
CODE_RBRACE = 8
CODE_COMPARE = 9
CODE_SEMICOLON = 10
CODE_NEWLINE = 11
CODE_ARITH = 12
CODE_ASSIGN = 13
CODE_AND = 14
CODE_OR = 15
CODE_NOT = 16
CODE_LPAREN = 17
CODE_RPAREN = 18
CODE_ERROR = 100

RECOVERY_INSERT = "insert"
RECOVERY_DELETE = "delete"
RECOVERY_REPLACE = "replace"
RECOVERY_SYNC = "sync"


class ParseError:
    def __init__(self, fragment, line, start_pos, end_pos, message):
        self.fragment = fragment
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.message = message


class ParseResult:
    def __init__(self, ok, errors, ast_spans=None):
        self.ok = ok
        self.errors = errors
        self.ast_spans = ast_spans


def _levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            replace = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, replace))
        prev = cur
    return prev[-1]


def _looks_like_keyword(lexeme, keyword):
    lx = (lexeme or "").lower()
    if not lx:
        return False
    compact = "".join(ch for ch in lx if ch.isalnum())
    if compact == keyword:
        return True
    if compact and compact[0] == keyword[0] and _levenshtein(compact, keyword) <= 2:
        return True
    if lx == keyword:
        return True
    if lx[0] != keyword[0]:
        return False
    return _levenshtein(lx, keyword) <= 2


def _is_keyword_with_affix_noise(lexeme, keyword):
    lx = (lexeme or "").lower()
    if not lx:
        return False
    compact = "".join(ch for ch in lx if ch.isalnum())
    if compact != keyword or lx == keyword:
        return False
    if lx.startswith(keyword):
        tail = lx[len(keyword) :]
        return bool(tail) and all(not ch.isalnum() for ch in tail)
    if lx.endswith(keyword):
        head = lx[: -len(keyword)]
        return bool(head) and all(not ch.isalnum() for ch in head)
    return False


def _lexer_message_for_token(token):
    lx = token.lexeme or ""
    if lx and all(ch in ".,:?#$%^&_`~\\|" for ch in lx):
        return "Недопустимая лексема (лексическая ошибка)"
    if lx and len(lx) > 1 and len(set(lx)) == 1 and lx[0] in "{};()[]":
        ch = lx[0]
        return f"Ожидался символ '{ch}'. Получена последовательность '{lx}'."

    if lx and all(c in "<>=!+-*/%" for c in lx):
        if lx == "!":
            return "Недопустимая лексема (лексическая ошибка)"
        if any(c in "<>!" for c in lx):
            return "Ожидался оператор сравнения (<, >, ==, ...)"
        return "Ожидался оператор '=' или составной оператор (+=, -=, ...)"

    if _looks_like_keyword(lx, "repeat"):
        if _is_keyword_with_affix_noise(lx, "repeat"):
            return "Недопустимая лексема (лексическая ошибка)"
        return "Ожидалось ключевое слово repeat (лексическая ошибка)"
    if _looks_like_keyword(lx, "while"):
        if _is_keyword_with_affix_noise(lx, "while"):
            return "Недопустимая лексема (лексическая ошибка)"
        return "Ожидалось ключевое слово while (лексическая ошибка)"
    if _looks_like_keyword(lx, "and") or _looks_like_keyword(lx, "or") or _looks_like_keyword(lx, "not"):
        return "Ожидался логический оператор (лексическая ошибка)"
    if lx and lx[0].isalpha():
        return "Ожидался идентификатор (лексическая ошибка)"
    return "Недопустимая лексема (лексическая ошибка)"


def _keyword_affix_noise_fragment(token):
    lx = token.lexeme or ""
    if not lx:
        return None

    lower = lx.lower()
    for keyword in ("repeat", "while", "and", "or", "not"):
        if not _is_keyword_with_affix_noise(lower, keyword):
            continue

        if lower.startswith(keyword):
            noise = lx[len(keyword) :]
            if noise:
                return noise, token.start_pos + len(keyword), token.end_pos
            return None

        if lower.endswith(keyword):
            noise = lx[: -len(keyword)]
            if noise:
                return noise, token.start_pos, token.start_pos + len(noise) - 1
            return None

    return None


def _split_keyword_like_error_with_edge_noise(token, message):
    if not token or token.code != CODE_ERROR:
        return None
    if not message:
        return None
    if not (
        message.startswith("Ожидалось ключевое слово")
        or message.startswith("Ожидался логический оператор")
    ):
        return None

    lx = token.lexeme or ""
    if not lx or len(lx) < 2:
        return None

    left = 0
    right = len(lx) - 1
    while left < len(lx) and not lx[left].isalnum():
        left += 1
    while right >= 0 and not lx[right].isalnum():
        right -= 1

    if left > right:
        return None
    if left == 0 and right == len(lx) - 1:
        return None

    core = lx[left : right + 1]
    if message.startswith("Ожидалось ключевое слово repeat"):
        if not _looks_like_keyword(core, "repeat"):
            return None
    elif message.startswith("Ожидалось ключевое слово while"):
        if not _looks_like_keyword(core, "while"):
            return None
    elif not (
        _looks_like_keyword(core, "and")
        or _looks_like_keyword(core, "or")
        or _looks_like_keyword(core, "not")
    ):
        return None

    parts = []
    if left > 0:
        head = lx[:left]
        parts.append(
            ParseError(
                head,
                token.line,
                token.start_pos,
                token.start_pos + len(head) - 1,
                "Недопустимая лексема (лексическая ошибка)",
            )
        )

    parts.append(
        ParseError(
            core,
            token.line,
            token.start_pos + left,
            token.start_pos + right,
            message,
        )
    )

    if right < len(lx) - 1:
        tail = lx[right + 1 :]
        parts.append(
            ParseError(
                tail,
                token.line,
                token.start_pos + right + 1,
                token.end_pos,
                "Недопустимая лексема (лексическая ошибка)",
            )
        )
    return parts


GRAMMAR = {
    "FIRST": {
        "Z": {CODE_REPEAT},
        "STMT_LIST": {CODE_IDENTIFIER, CODE_ERROR},
        "STMT": {CODE_IDENTIFIER, CODE_ERROR},
        "ASSIGN_OP": {CODE_ASSIGN, CODE_COMPOUND_ASSIGN, CODE_ERROR},
        "CONDITION": {CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_NOT, CODE_ERROR},
        "EXPR": {CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_ERROR},
        "REL_OP": {CODE_COMPARE, CODE_ERROR},
        "LOGIC_OP": {CODE_AND, CODE_OR, CODE_ERROR},
    },
    "FOLLOW": {
        "Z": set(),
        "REPEAT": {CODE_LBRACE, CODE_SEMICOLON},
        "BODY": {CODE_RBRACE, CODE_WHILE},
        "STMT": {CODE_SEMICOLON, CODE_RBRACE, CODE_WHILE, CODE_NEWLINE},
        "CONDITION": {CODE_SEMICOLON, CODE_RPAREN},
        "EXPR_IN_CONDITION": {
            CODE_COMPARE,
            CODE_AND,
            CODE_OR,
            CODE_SEMICOLON,
            CODE_RPAREN,
        },
        "REL_OP": {CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_ERROR},
    },
}


def first(nonterminal):
    return set(GRAMMAR["FIRST"][nonterminal])


def concrete_first(nonterminal):
    return first(nonterminal) - {CODE_ERROR}


def follow(nonterminal):
    return set(GRAMMAR["FOLLOW"][nonterminal])


class IronsParser:
    PROGRAM_FOLLOW = first("Z") | follow("REPEAT")
    BODY_FOLLOW = follow("BODY")
    STMT_FOLLOW = follow("STMT")
    CONDITION_FOLLOW = follow("CONDITION")

    _KEYWORD_JOINED_LOWER = frozenset({"repeat", "while", "and", "or", "not"})
    _KEYWORD_SEMICOLON_EXPECT_MSG = {
        CODE_REPEAT: "Ожидалось ключевое слово repeat",
        CODE_WHILE: "Ожидалось ключевое слово while",
        CODE_AND: "Ожидалось ключевое слово and",
        CODE_OR: "Ожидалось ключевое слово or",
        CODE_NOT: "Ожидалось ключевое слово not",
    }

    def __init__(self, tokens):
        self.tokens = list(tokens)
        self.pos = 0
        self.errors = []
        self.condition_progress = 0
        self.current_stmt_start_token = None
        self.suffix_anchor_token = None
        self._virtual_open_brace = False
        self._open_brace_after_double_lbrace_lexer_error = False
        self._suppress_rbrace_expect_after_stray_lbrace = False
        self._ast_pre_s = 0
        self._ast_pre_e = 0
        self._ast_bs = None
        self._ast_be = None
        self._ast_cs = None
        self._ast_ce = None

    def _ast_spans(self):
        if self._ast_bs is None or self._ast_be is None:
            return None
        return (self._ast_pre_s, self._ast_pre_e, self._ast_bs, self._ast_be, self._ast_cs, self._ast_ce)

    def parse(self):
        self.skip_nl()
        self._ast_pre_s = 0
        while not self.eof():
            self.skip_nl()
            t = self.peek()
            if t is None:
                break
            if t.code == CODE_REPEAT:
                break
            if not self.is_statement_start(t):
                break
            self.parse_stmt(prelude=True)
        self._ast_pre_e = self.pos
        self.skip_nl()
        if not self.try_consume_keyword_split_by_semicolon(CODE_REPEAT):
            if not self.try_consume_keyword_from_two_identifiers(CODE_REPEAT):
                self.expect(CODE_REPEAT, "Ожидалось ключевое слово repeat", self.PROGRAM_FOLLOW)
        self.skip_nl()
        self.consume_extra_keywords({CODE_REPEAT, CODE_WHILE})
        paired_body_close, error_body_close = self.wrong_body_closer_for(self.peek())
        self.consume_identifier_junk_before_open_brace()
        self._consume_extra_rbrace_before_opening_body_brace()
        opened = self.expect(CODE_LBRACE, "Ожидался символ '{'", self.BODY_FOLLOW)
        if self._virtual_open_brace:
            opened = True
            self._virtual_open_brace = False
        elif self._open_brace_after_double_lbrace_lexer_error:
            opened = True
            self._open_brace_after_double_lbrace_lexer_error = False
            self.skip_nl()
            if self.peek() and self.peek().code == CODE_RBRACE:
                self.add_extra_symbol_error(self.peek())
                self.advance()
                self.skip_nl()
        self.suffix_anchor_token = None
        if (
            opened
            and self.peek()
            and self.peek().code == CODE_LBRACE
            and (self.previous() is None or self.previous().code != CODE_LBRACE)
        ):
            self.advance()
        self._ast_bs = self.pos
        body_end = set(self.BODY_FOLLOW)
        if paired_body_close is not None:
            body_end.add(paired_body_close)
        self.parse_body(body_end, error_body_close)
        self._ast_be = self.pos
        self.skip_nl()
        if self._suppress_rbrace_expect_after_stray_lbrace:
            self._suppress_rbrace_expect_after_stray_lbrace = False
        elif not (not opened and self.peek() and self.peek().code == CODE_RBRACE):
            self.expect(CODE_RBRACE, "Ожидался символ '}'", {CODE_WHILE, CODE_SEMICOLON})
        self.skip_nl()
        self.consume_illegal_semicolon_between_rbrace_and_while()
        if self.eof():
            self.add_missing_suffix_errors(0)
            return ParseResult(
                not self.errors and self.eof(), list(self.errors), self._ast_spans()
            )
        if self.try_consume_keyword_split_by_semicolon(CODE_WHILE):
            has_while = True
        elif self.try_consume_keyword_from_two_identifiers(CODE_WHILE):
            has_while = True
        else:
            has_while = self.expect(CODE_WHILE, "Ожидалось ключевое слово while", self.CONDITION_FOLLOW)
        if not has_while:
            if self.eof():
                self.add_missing_suffix_errors(0)
                return ParseResult(
                    not self.errors and self.eof(), list(self.errors), self._ast_spans()
                )
            if self.is_condition_like_sequence(self.pos) or self.is_condition_prefix_start(self.peek()):
                self.condition_progress = 1
                self._ast_cs = self.pos
                self.parse_condition()
                self._ast_ce = self.pos
                self.skip_nl()
                if self.eof():
                    self.add_missing_suffix_errors(self.condition_progress)
                    return ParseResult(
                        not self.errors and self.eof(), list(self.errors), self._ast_spans()
                    )
                self.expect(CODE_SEMICOLON, "Ожидался символ ';' в конце конструкции", set())
                self.parse_trailing()
                return ParseResult(
                    not self.errors and self.eof(), list(self.errors), self._ast_spans()
                )
            self.sync_to_follow("CONDITION")
            if self.peek() and self.peek().code == CODE_SEMICOLON:
                self.advance()
            self.parse_trailing()
            return ParseResult(
                not self.errors and self.eof(), list(self.errors), self._ast_spans()
            )
        self.condition_progress = 1
        self._ast_cs = self.pos
        self.parse_condition()
        self._ast_ce = self.pos
        self.skip_nl()
        if self.eof():
            self.add_missing_suffix_errors(self.condition_progress)
            return ParseResult(
                not self.errors and self.eof(), list(self.errors), self._ast_spans()
            )
        self.expect(CODE_SEMICOLON, "Ожидался символ ';' в конце конструкции", set())
        self.parse_trailing()
        return ParseResult(
            not self.errors and self.eof(), list(self.errors), self._ast_spans()
        )

    def peek(self, offset=0):
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else None

    def previous(self):
        return self.tokens[self.pos - 1] if self.pos > 0 else None

    def eof(self):
        return self.pos >= len(self.tokens)

    def advance(self):
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    def take(self, code):
        self.skip_nl()
        tok = self.peek()
        if tok and tok.code == code:
            self.pos += 1
            return tok
        return None

    def skip_nl(self):
        while self.peek() and self.peek().code == CODE_NEWLINE:
            self.pos += 1

    def add_err(self, msg, tok=None, fragment=None, action=None):
        if tok is None:
            tok = self.peek() or self.previous()
        if tok is None:
            self.errors.append(ParseError("EOF", 1, 1, 1, msg))
            return
        if action == RECOVERY_INSERT:
            line, pos = self._insertion_anchor_for_missing(tok, msg)
            self.errors.append(ParseError("", line, pos, pos, msg))
            return
        if fragment == "":
            line, pos = self._insertion_anchor_for_missing(tok, msg)
            self.errors.append(ParseError("", line, pos, pos, msg))
            return
        if action is None and self._is_missing_expected_error(msg, tok, fragment):
            line, pos = self._insertion_anchor_for_missing(tok, msg)
            self.errors.append(ParseError("", line, pos, pos, msg))
            return
        self.errors.append(
            ParseError(
                tok.lexeme if fragment is None else fragment,
                tok.line,
                tok.start_pos,
                tok.end_pos,
                msg,
            )
        )

    def emit_recovery_error(self, action, msg, tok=None, fragment=None):
        self.add_err(msg, tok, fragment=fragment, action=action)

    def _insertion_anchor_for_missing(self, tok, msg):
        if tok is None:
            return 1, 1
        if self._prefer_left_anchor_for_missing(msg):
            anchor = self._left_anchor_token_for_suffix(tok)
            if anchor is not None:
                if msg == "Ожидался символ '{'" and self.suffix_anchor_token is not None:
                    return anchor.line, anchor.end_pos + 1
                return anchor.line, anchor.start_pos
        current = self.peek()
        if current is tok:
            if (
                msg == "В условии ожидался идентификатор"
                and tok.code == CODE_ERROR
            ):
                return tok.line, tok.end_pos + 1
            if self._should_anchor_after_previous_for_missing(tok, msg):
                prev_sig = self._previous_non_newline_token(self.pos)
                if prev_sig is not None:
                    return prev_sig.line, prev_sig.end_pos + 1
            return tok.line, tok.start_pos
        return tok.line, tok.end_pos + 1

    def _prefer_left_anchor_for_missing(self, msg):
        if not msg:
            return False
        if msg in {"Ожидался символ '}'", "Ожидалось ключевое слово while"}:
            return True
        if msg == "Ожидался символ '{'" and self.suffix_anchor_token is not None:
            return True
        return False

    def _left_anchor_token_for_suffix(self, tok):
        if self.suffix_anchor_token is not None:
            return self.suffix_anchor_token
        current = self.peek()
        if current is not None:
            return current
        return tok

    def _previous_non_newline_token(self, before_index):
        i = before_index - 1
        while i >= 0:
            tok = self.tokens[i]
            if tok.code != CODE_NEWLINE:
                return tok
            i -= 1
        return None

    def _should_anchor_after_previous_for_missing(self, tok, msg):
        if tok is None or not msg:
            return False
        lower = msg.lower()
        if "ожидался оператор сравнения" in lower and tok.code == CODE_ERROR:
            if self._is_float_literal_lexical_error(tok) or self._is_value_like_error(tok):
                return True
            return False
        insertion_after_previous_markers = (
            "ожидалось значение выражения",
            "ожидались идентификатор или целое число в условии",
            "ожидался оператор сравнения",
            "ожидался оператор '=' или составной оператор",
            "ожидался оператор присваивания",
        )
        if any(marker in lower for marker in insertion_after_previous_markers):
            return True
        if tok.code in (CODE_RBRACE, CODE_RPAREN, CODE_SEMICOLON):
            return True
        return False

    def _is_missing_expected_error(self, msg, tok, fragment):
        if fragment is not None:
            return False
        if not msg:
            return False
        lower = msg.lower()
        if "лексичес" in lower:
            return False
        if "лишн" in lower:
            return False
        if "получена последовательность" in lower:
            return False
        if "найден" in lower:
            return False
        missing_markers = (
            "ожидалось значение выражения",
            "ожидались идентификатор или целое число в условии",
            "в условии ожидался идентификатор",
            "ожидался символ ';' в конце",
            "ожидался оператор в теле цикла",
            "ожидалось ключевое слово while",
        )
        if any(marker in lower for marker in missing_markers):
            return True

        # At hard EOF, generic "expected ..." diagnostics should anchor as insertion.
        if self.peek() is None and tok is self.previous():
            if msg.startswith("Ожидал") or msg.startswith("Ожидалось") or msg.startswith("Ожидались"):
                return True
        return False

    def add_missing_semicolon_after_previous(self):
        prev = self.previous()
        if prev is None:
            self.emit_recovery_error(RECOVERY_INSERT, "Ожидался символ ';' в конце конструкции")
            return
        self.emit_recovery_error(RECOVERY_INSERT, "Ожидался символ ';' в конце конструкции", prev)

    def add_extra_keyword_error(self, tok):
        self.add_err(f"Лишнее ключевое слово '{tok.lexeme}'", tok)

    def add_extra_symbol_error(self, tok):
        self.add_err(f"Лишний символ '{tok.lexeme}'", tok)

    def consume_extra_semicolon(self):
        tok = self.peek()
        if not tok or tok.code != CODE_SEMICOLON:
            return False
        self.add_extra_symbol_error(tok)
        self.advance()
        self.skip_nl()
        return True

    def consume_illegal_semicolon_between_rbrace_and_while(self):
        self.skip_nl()
        tok = self.peek()
        if not tok or tok.code != CODE_SEMICOLON:
            return False
        nxt_i = self._next_non_nl_index(self.pos + 1)
        if nxt_i is None or self.tokens[nxt_i].code != CODE_WHILE:
            return False
        self.add_extra_symbol_error(tok)
        self.advance()
        self.skip_nl()
        return True

    def consume_extra_semicolon_before_more_input(self):
        tok = self.peek()
        if not tok or tok.code != CODE_SEMICOLON:
            return False
        if self.next_non_nl(self.pos + 1) is None:
            return False
        return self.consume_extra_semicolon()

    def assignment_operator_error_message(self, tok):
        if tok and tok.code == CODE_ERROR:
            return "Ожидался оператор присваивания (лексическая ошибка)"
        return "Ожидался оператор '=' или составной оператор (+=, -=, ...)"

    def comparison_operator_error_message(self, tok):
        if tok and tok.code == CODE_ERROR and self._is_comparison_like_error(tok):
            return "Ожидался оператор сравнения (лексическая ошибка)"
        return "Ожидался оператор сравнения (<, >, ==, ...)"

    def consume_extra_keywords(self, keyword_codes):
        consumed = False
        keyword_codes = set(keyword_codes)
        while self.peek() and self.peek().code in keyword_codes:
            self.add_extra_keyword_error(self.peek())
            self.advance()
            self.skip_nl()
            consumed = True
        return consumed

    def consume_extra_symbols(self, symbol_codes):
        consumed = False
        symbol_codes = set(symbol_codes)
        while self.peek() and self.peek().code in symbol_codes:
            self.add_extra_symbol_error(self.peek())
            self.advance()
            self.skip_nl()
            consumed = True
        return consumed

    def is_extra_symbol_token(self, tok):
        return bool(
            tok
            and tok.code in (
                CODE_LBRACE,
                CODE_RBRACE,
                CODE_LPAREN,
                CODE_RPAREN,
                CODE_ARITH,
            )
        )

    def has_error_message(self, message):
        return any(err.message == message for err in self.errors)

    def add_missing_suffix_errors(self, progress):
        missing = [
            (5, "Ожидался символ ';' в конце конструкции"),
            (4, "Ожидались идентификатор или целое число в условии"),
            (3, "Ожидался оператор сравнения (<, >, ==, ...)"),
            (2, "В условии ожидался идентификатор"),
            (1, "Ожидалось ключевое слово while"),
        ]
        for required_progress, message in missing:
            if progress >= required_progress:
                continue
            if self.has_error_message(message):
                continue
            self.emit_recovery_error(RECOVERY_INSERT, message)

    def next_non_nl(self, start):
        i = start
        while i < len(self.tokens) and self.tokens[i].code == CODE_NEWLINE:
            i += 1
        return self.tokens[i] if i < len(self.tokens) else None

    def recover_errors_before(
        self,
        expected_codes,
        blocking_error=None,
        commit_on_failure=False,
        commit_on_blocking=False,
    ):
        expected_codes = set(expected_codes)
        i = self.pos
        skipped = []
        while i < len(self.tokens) and self.tokens[i].code in (CODE_ERROR, CODE_NEWLINE):
            tok = self.tokens[i]
            if tok.code == CODE_ERROR:
                if blocking_error is not None and blocking_error(tok):
                    if commit_on_blocking and skipped:
                        self.pos = i
                        return False, skipped
                    break
                skipped.append(tok)
            i += 1

        if i < len(self.tokens) and self.tokens[i].code in expected_codes:
            self.pos = i
            return True, skipped

        if commit_on_failure and skipped:
            self.pos = i
        return False, skipped

    def recover_to_first(self, nonterminal, **kwargs):
        return self.recover_errors_before(first(nonterminal), **kwargs)

    def sync_to(self, follow):
        follow = set(follow)
        while self.peek() and self.peek().code not in follow:
            self.pos += 1

    def sync_to_follow(self, nonterminal, extra=None):
        stop = follow(nonterminal)
        if extra:
            stop |= set(extra)
        self.sync_to(stop)

    def delete_extra_before_expected(self, tok, expected_code):
        if tok.code == CODE_IDENTIFIER:
            self.add_err(f"Лишний токен '{tok.lexeme}'", tok)
        elif self.is_extra_symbol_token(tok):
            self.add_extra_symbol_error(tok)
        else:
            self.add_err(
                f"Лишний токен '{tok.lexeme}' перед ожидаемым '{self.label(expected_code)}'",
                tok,
            )
        self.advance()
        self.skip_nl()
        self.advance()
        return True

    def sync_to_expected_or_follow(self, expected_code, follow_codes):
        stop = set(follow_codes)
        stop.add(expected_code)
        self.sync_to(stop)
        if self.peek() and self.peek().code == expected_code:
            self.advance()
            return True
        return False

    def expect(self, code, msg, follow):
        self.skip_nl()
        tok = self.peek()
        if tok and tok.code == code:
            self.pos += 1
            return True

        return self.recover_expected(code, msg, follow)

    def recover_expected(self, code, msg, follow):
        tok = self.peek()
        if tok and tok.code == CODE_SEMICOLON and code != CODE_SEMICOLON:
            self.consume_extra_semicolon()
            return self.expect(code, msg, follow)
        if code == CODE_LBRACE and tok and tok.code == CODE_ERROR and self._is_repeated_symbol_error(tok, "}"):
            self.add_err(msg, tok)
            self.advance()
            self._virtual_open_brace = True
            return False
        if code == CODE_LBRACE and tok and tok.code == CODE_RBRACE:
            self.add_err(msg, tok)
            self.advance()
            self._virtual_open_brace = True
            return False
        if code == CODE_LBRACE and tok and tok.code == CODE_ERROR and self._is_repeated_symbol_error(tok, "{"):
            self.add_err(
                f"Ожидался символ '{{'. Получена последовательность '{tok.lexeme}'.",
                tok,
            )
            self.advance()
            self._open_brace_after_double_lbrace_lexer_error = True
            return False
        if code == CODE_REPEAT and tok:
            if tok.code in (CODE_IDENTIFIER, CODE_ERROR) and tok.lexeme and tok.lexeme[0].lower() == "r":
                self.emit_recovery_error(RECOVERY_REPLACE, msg, tok)
                self.advance()
                return True
            if tok.code in (CODE_IDENTIFIER, CODE_ERROR) and tok.lexeme and _looks_like_keyword(tok.lexeme, "repeat"):
                if tok.code == CODE_IDENTIFIER:
                    self.emit_recovery_error(RECOVERY_REPLACE, msg, tok)
                self.advance()
                return True
            if tok.code == CODE_LBRACE:
                self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
                return False
            if self.is_statement_start(tok):
                self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
                return False
        if code == CODE_WHILE and tok:
            if (
                tok.code in (CODE_IDENTIFIER, CODE_ERROR)
                and tok.lexeme
                and _looks_like_keyword(tok.lexeme, "while")
            ):
                self.emit_recovery_error(RECOVERY_REPLACE, msg, tok)
                self.advance()
                return True
            if self.consume_extra_tokens_before_missing_while():
                return self.expect(code, msg, follow)
        if tok and tok.code == CODE_ERROR:
            if self.is_wrong_body_bracket(tok):
                self.add_err(msg, tok)
                self.advance()
                return True
            repeated_symbol = self.expected_repeated_symbol(code)
            if repeated_symbol and self._is_repeated_symbol_error(tok, repeated_symbol):
                self.add_err(
                    f"Ожидался символ '{repeated_symbol}'. Получена последовательность '{tok.lexeme}'.",
                    tok,
                )
                self.advance()
                return True

        repeated_symbol = self.expected_repeated_symbol(code)
        nxt = self.next_non_nl(self.pos + 1)
        expected_keyword = {CODE_REPEAT: "repeat", CODE_WHILE: "while"}.get(code)
        if (
            tok
            and tok.code == CODE_ERROR
            and nxt
            and expected_keyword
            and self.is_keyword_prefix_noise_error(tok)
            and (
                nxt.code == code
                or (nxt.code == CODE_ERROR and _looks_like_keyword(nxt.lexeme, expected_keyword))
            )
        ):
            self.advance()
            self.skip_nl()
            return self.expect(code, msg, follow)
        if (
            tok
            and tok.code == CODE_ERROR
            and nxt
            and repeated_symbol
            and self._is_repeated_symbol_error(nxt, repeated_symbol)
        ):
            self.advance()
            self.skip_nl()
            return self.expect(code, msg, follow)

        if repeated_symbol:
            repeated_idx = self.find_repeated_symbol_error_ahead(self.pos, repeated_symbol)
            if repeated_idx is not None and repeated_idx > self.pos:
                self.pos = repeated_idx
                return self.expect(code, msg, follow)

        recovered, _ = self.recover_errors_before({code})
        if recovered:
            self.advance()
            return True

        if tok and tok.code != CODE_ERROR and nxt and nxt.code == code:
            return self.delete_extra_before_expected(tok, code)

        if code == CODE_LBRACE and self.is_statement_start(tok):
            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            return True

        if code == CODE_RBRACE and tok and tok.code == CODE_WHILE:
            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            return False
        if code == CODE_RBRACE and self.is_while_boundary_token(tok):
            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            return False
        if code == CODE_RBRACE and self.is_condition_like_sequence(self.pos):
            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            return False

        if code == CODE_WHILE and self.is_while_boundary_token(tok):
            self.add_err(msg, tok)
            self.advance()
            return True
        if code == CODE_WHILE and self.is_condition_prefix_start(tok):
            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            return False
        if code == CODE_WHILE and self.is_condition_like_sequence(self.pos):
            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            return False

        if code == CODE_LBRACE and tok and tok.code not in follow:
            self.add_err(msg, tok)
            self.advance()
            return True

        if tok is None or tok.code in follow:
            self.emit_recovery_error(RECOVERY_INSERT, msg)
            return False

        if tok.code == CODE_ERROR:
            self.emit_recovery_error(RECOVERY_REPLACE, msg, tok)
            return False

        self.emit_recovery_error(RECOVERY_SYNC, msg, tok)
        return self.sync_to_expected_or_follow(code, follow)

    def consume_extra_tokens_before_missing_while(self):
        tok = self.peek()
        if not tok or tok.code not in (CODE_IDENTIFIER, CODE_ERROR):
            return False
        first_extra = tok
        consumed = False
        extra_chain = ""
        while self.peek():
            tok = self.peek()
            if tok.code == CODE_NEWLINE:
                self.advance()
                continue
            if tok.code == CODE_SEMICOLON:
                if not consumed:
                    break
                self.consume_extra_semicolon()
                continue
            if tok.code not in (CODE_IDENTIFIER, CODE_ERROR):
                break
            if tok.code == CODE_ERROR:
                if not (tok.lexeme and tok.lexeme[0].isalpha()):
                    break
            if tok.lexeme and _looks_like_keyword(tok.lexeme, "while"):
                break
            if consumed and self.is_condition_prefix_start(tok):
                candidate = (extra_chain + (tok.lexeme or "")).lower()
                if not _looks_like_keyword(candidate, "while"):
                    break
            nxt_index = self._next_non_nl_index(self.pos + 1)
            while nxt_index is not None and self.tokens[nxt_index].code == CODE_SEMICOLON:
                nxt_index = self._next_non_nl_index(nxt_index + 1)
            nxt = self.tokens[nxt_index] if nxt_index is not None else None
            if not nxt:
                break
            if (
                tok.code == CODE_IDENTIFIER
                and nxt.code == CODE_DIGIT
                and not (tok.lexeme and tok.lexeme[0].lower() == "w")
            ):
                break
            if not self.is_condition_prefix_start(nxt):
                break
            self.add_err(f"Лишний токен '{tok.lexeme}'", tok)
            extra_chain += tok.lexeme or ""
            self.advance()
            consumed = True
        if consumed:
            self.suffix_anchor_token = first_extra
        return consumed

    def is_keyword_prefix_noise_error(self, tok):
        return bool(
            tok
            and tok.code == CODE_ERROR
            and tok.lexeme
            and all(not ch.isalnum() for ch in tok.lexeme)
        )

    def find_repeated_symbol_error_ahead(self, start, symbol):
        i = start
        while i < len(self.tokens):
            tok = self.tokens[i]
            if tok.code == CODE_NEWLINE:
                i += 1
                continue
            if tok.code != CODE_ERROR:
                return None
            if self._is_repeated_symbol_error(tok, symbol):
                return i
            i += 1
        return None

    def label(self, code):
        labels = {
            CODE_REPEAT: "repeat",
            CODE_WHILE: "while",
            CODE_IDENTIFIER: "идентификатор",
            CODE_LBRACE: "{",
            CODE_RBRACE: "}",
            CODE_COMPOUND_ASSIGN: "составной оператор присваивания",
            CODE_DIGIT: "целое число",
            CODE_COMPARE: "оператор сравнения",
            CODE_SEMICOLON: ";",
            CODE_ASSIGN: "=",
            CODE_AND: "and",
            CODE_OR: "or",
            CODE_NOT: "not",
            CODE_LPAREN: "(",
            CODE_RPAREN: ")",
        }
        return labels.get(code, str(code))

    def is_statement_start(self, tok):
        return bool(tok and (tok.code == CODE_IDENTIFIER or self._is_corrupted_identifier(tok)))

    def is_while_like_token(self, tok):
        return bool(
            tok
            and tok.lexeme
            and tok.code in (CODE_IDENTIFIER, CODE_ERROR)
            and _looks_like_keyword(tok.lexeme, "while")
        )

    def is_while_boundary_token(self, tok=None):
        tok = tok or self.peek()
        if not self.is_while_like_token(tok):
            return False
        nxt = self.next_non_nl(self.pos + 1)
        return bool(
            nxt
            and (
                nxt.code in (CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_NOT)
                or (nxt.code == CODE_ERROR and self._is_corrupted_identifier(nxt))
            )
        )

    def parse_body(self, end_codes=None, error_end_lexeme=None):
        end_codes = set(end_codes or self.BODY_FOLLOW)
        self.skip_nl()
        if self.is_while_boundary_token():
            return
        if self.is_body_end_token(self.peek(), end_codes, error_end_lexeme):
            tok = self.peek()
            handled = False
            if tok and tok.code == CODE_RBRACE:
                nxt_i = self._next_non_nl_index(self.pos + 1)
                if nxt_i is not None and self.tokens[nxt_i].code != CODE_WHILE:
                    close_idx = self._find_body_rbrace_before_while(self.pos + 1)
                    if (
                        close_idx is not None
                        and close_idx > self.pos
                        and self._has_substance_between(self.pos, close_idx)
                    ):
                        self.add_extra_symbol_error(tok)
                        self.advance()
                        self.skip_nl()
                        handled = True
            if not handled:
                self.emit_recovery_error(RECOVERY_INSERT, "Ожидался оператор в теле цикла", self.peek())
                return

        while self.peek() and not self.is_body_end_token(self.peek(), end_codes, error_end_lexeme):
            if self.is_while_boundary_token():
                return
            if self._consume_stray_open_braces_run_before_while():
                return
            if self._consume_wrong_lbrace_semicolon_while_instead_of_rbrace():
                return
            if self._consume_stray_open_brace_before_rbrace_semicolon_while():
                continue
            if self.is_condition_like_sequence(self.pos):
                return
            if self.consume_extra_semicolon():
                continue
            if self.peek().code == CODE_ERROR:
                if self.is_repeated_closing_brace_error(self.peek()):
                    return
                if self.is_statement_leading_noise(self.peek()) and self.looks_like_assignment_stmt_after_noise(self.pos + 1):
                    self.advance()
                    self.skip_nl()
                    continue
                if (
                    self._is_corrupted_statement_identifier(self.peek())
                    or self.is_broken_statement_identifier(self.peek())
                    or self._is_operator_like_error(self.peek())
                ):
                    self.parse_stmt()
                    self.skip_nl()
                    continue
                self.advance()
                continue
            self.parse_stmt()
            self.skip_nl()

    def is_statement_leading_noise(self, tok):
        return bool(
            tok
            and tok.code == CODE_ERROR
            and tok.lexeme
            and not any(ch.isalnum() for ch in tok.lexeme)
        )

    def _identifiers_mergeable_across_semicolon(self, a, b):
        if not (
            a
            and b
            and a.code == CODE_IDENTIFIER
            and b.code == CODE_IDENTIFIER
        ):
            return False
        cat = (a.lexeme or "") + (b.lexeme or "")
        if not cat or not cat[0].isalpha() or not cat.isascii():
            return False
        core = cat.replace("_", "")
        if not core.isalnum():
            return False
        return True

    def try_recover_split_identifier_semicolon_statement(self):
        tok = self.peek()
        if not (tok and tok.code == CODE_IDENTIFIER):
            return False
        semi_i = self._next_non_nl_index(self.pos + 1)
        if semi_i is None or self.tokens[semi_i].code != CODE_SEMICOLON:
            return False
        id2_i = self._next_non_nl_index(semi_i + 1)
        if id2_i is None or self.tokens[id2_i].code != CODE_IDENTIFIER:
            return False
        id2 = self.tokens[id2_i]
        cat = ((tok.lexeme or "") + (id2.lexeme or "")).lower()
        if cat in self._KEYWORD_JOINED_LOWER:
            return False
        if not self._identifiers_mergeable_across_semicolon(tok, id2):
            return False
        semi = self.tokens[semi_i]
        self.add_extra_symbol_error(semi)
        self.pos = id2_i + 1
        self.skip_nl()
        return True

    def try_consume_keyword_split_by_semicolon(self, code):
        name = {
            CODE_REPEAT: "repeat",
            CODE_WHILE: "while",
            CODE_AND: "and",
            CODE_OR: "or",
            CODE_NOT: "not",
        }.get(code)
        if not name:
            return False
        tok = self.peek()
        if not (tok and tok.code == CODE_IDENTIFIER):
            return False
        semi_i = self._next_non_nl_index(self.pos + 1)
        if semi_i is None or self.tokens[semi_i].code != CODE_SEMICOLON:
            return False
        id2_i = self._next_non_nl_index(semi_i + 1)
        if id2_i is None or self.tokens[id2_i].code != CODE_IDENTIFIER:
            return False
        b = self.tokens[id2_i]
        cat = ((tok.lexeme or "") + (b.lexeme or "")).lower()
        if cat != name:
            if not (
                code == CODE_WHILE
                and name == "while"
                and (tok.lexeme or "").lower() == "whi"
                and _levenshtein(cat, "while") <= 1
            ):
                return False
        msg = self._KEYWORD_SEMICOLON_EXPECT_MSG.get(code)
        if not msg:
            return False
        combined = (tok.lexeme or "") + ";" + (b.lexeme or "")
        self.errors.append(
            ParseError(
                combined,
                tok.line,
                tok.start_pos,
                b.end_pos,
                msg,
            )
        )
        self.pos = id2_i + 1
        self.skip_nl()
        return True

    def try_consume_keyword_from_two_identifiers(self, code):
        name = {CODE_REPEAT: "repeat", CODE_WHILE: "while"}.get(code)
        if not name:
            return False
        a = self.peek()
        if not (a and a.code == CODE_IDENTIFIER):
            return False
        id2_i = self._next_non_nl_index(self.pos + 1)
        if id2_i is None:
            return False
        for i in range(self.pos + 1, id2_i):
            if self.tokens[i].code != CODE_NEWLINE:
                return False
        b = self.tokens[id2_i]
        if b.code != CODE_IDENTIFIER:
            return False
        cat = ((a.lexeme or "") + (b.lexeme or "")).lower()
        if cat != name:
            return False
        if len(a.lexeme or "") + len(b.lexeme or "") != len(name):
            return False
        msg = self._KEYWORD_SEMICOLON_EXPECT_MSG.get(code)
        if not msg:
            return False
        self.errors.append(
            ParseError(
                a.lexeme or "",
                a.line,
                a.start_pos,
                a.end_pos,
                msg,
            )
        )
        self.add_err(f"Лишний токен '{b.lexeme}'", b)
        self.pos = id2_i + 1
        self.skip_nl()
        return True

    def try_recover_semicolon_split_condition_identifier(self):
        tok = self.peek()
        if not (tok and tok.code == CODE_IDENTIFIER):
            return False
        semi_i = self._next_non_nl_index(self.pos + 1)
        if semi_i is None or self.tokens[semi_i].code != CODE_SEMICOLON:
            return False
        id2_i = self._next_non_nl_index(semi_i + 1)
        if id2_i is None or self.tokens[id2_i].code != CODE_IDENTIFIER:
            return False
        id2 = self.tokens[id2_i]
        cat = ((tok.lexeme or "") + (id2.lexeme or "")).lower()
        if cat in self._KEYWORD_JOINED_LOWER:
            return False
        if not self._identifiers_mergeable_across_semicolon(tok, id2):
            return False
        self.add_extra_symbol_error(self.tokens[semi_i])
        self.condition_progress = max(self.condition_progress, 2)
        self.pos = id2_i + 1
        self.skip_nl()
        return True

    def _next_non_nl_index(self, start):
        i = start
        while i < len(self.tokens) and self.tokens[i].code == CODE_NEWLINE:
            i += 1
        return i if i < len(self.tokens) else None

    def _find_body_rbrace_before_while(self, search_from):
        for i in range(search_from, len(self.tokens)):
            if self.tokens[i].code != CODE_RBRACE:
                continue
            j = self._next_non_nl_index(i + 1)
            if j is None:
                continue
            if self.tokens[j].code == CODE_WHILE:
                return i
            if self.tokens[j].code == CODE_SEMICOLON:
                k = self._next_non_nl_index(j + 1)
                if k is not None and self.tokens[k].code == CODE_WHILE:
                    return i
        return None

    def _has_substance_between(self, lo, hi):
        for i in range(lo + 1, hi):
            if self.tokens[i].code != CODE_NEWLINE:
                return True
        return False

    def looks_like_assignment_stmt_after_noise(self, start):
        i = self._next_non_nl_index(start)
        if i is None:
            return False
        lhs = self.tokens[i]
        if not (lhs.code == CODE_IDENTIFIER or self._is_corrupted_identifier(lhs)):
            return False
        j = self._next_non_nl_index(i + 1)
        if j is None:
            return False
        op = self.tokens[j]
        return op.code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN) or (
            op.code == CODE_ERROR and self._is_operator_like_error(op)
        )

    def is_body_end_token(self, tok, end_codes, error_end_lexeme=None):
        if not tok:
            return False
        if tok.code in end_codes:
            return True
        return bool(
            error_end_lexeme
            and tok.code == CODE_ERROR
            and tok.lexeme == error_end_lexeme
        )

    def parse_stmt(self, prelude=False):
        self.skip_nl()
        tok = self.peek()
        if tok and tok.code == CODE_ERROR and self.is_statement_leading_noise(tok):
            if self.looks_like_assignment_stmt_after_noise(self.pos + 1):
                self.advance()
                self.skip_nl()
                tok = self.peek()
        if tok is None or tok.code in self.BODY_FOLLOW:
            return

        if self.try_recover_split_identifier_semicolon_statement():
            self.current_stmt_start_token = self.previous()
            if not self.parse_assignment_operator_and_expr():
                self.current_stmt_start_token = None
                return
            self.finish_stmt(successful_assignment=True, prelude=prelude)
            self.current_stmt_start_token = None
            return

        self.current_stmt_start_token = tok
        self.parse_assignment_left()
        if not self.parse_assignment_operator_and_expr():
            self.current_stmt_start_token = None
            return

        self.finish_stmt(successful_assignment=True, prelude=prelude)
        self.current_stmt_start_token = None

    def finish_stmt(self, successful_assignment=False, prelude=False):
        if self.peek() and self.peek().code == CODE_NEWLINE:
            return
        self.skip_nl()
        end = self.peek()
        if end is None or end.code in (CODE_RBRACE, CODE_WHILE) or self.is_while_boundary_token(end):
            return
        if end.code == CODE_SEMICOLON:
            nxt = self.next_non_nl(self.pos + 1)
            if prelude:
                self.advance()
                return
            if (
                successful_assignment
                and nxt
                and nxt.code == CODE_RBRACE
            ):
                self.advance()
                return
            self.add_extra_symbol_error(end)
            self.advance()
            return
        if end.code == CODE_RPAREN and self._next_significant_code(self.pos + 1) == CODE_WHILE:
            return
        if end.code in (CODE_LPAREN, CODE_RPAREN):
            self.add_extra_symbol_error(end)
            self.advance()
            self.sync_to_follow("STMT")
            return
        if end.code == CODE_ERROR and self.is_separator_punctuation_error(end):
            self.advance()
            self.sync_to_follow("STMT")
            return
        if end.code == CODE_ERROR:
            if self.is_repeated_closing_brace_error(end):
                return
            lookahead = self.pos
            while lookahead < len(self.tokens) and self.tokens[lookahead].code in (
                CODE_ERROR,
                CODE_NEWLINE,
            ):
                tok = self.tokens[lookahead]
                if self.is_repeated_closing_brace_error(tok):
                    self.pos = lookahead
                    return
                lookahead += 1
            if lookahead < len(self.tokens) and self.tokens[lookahead].code in (
                CODE_RBRACE,
                CODE_WHILE,
            ):
                self.pos = lookahead
                return
            if lookahead < len(self.tokens) and self.tokens[lookahead].code == CODE_RPAREN:
                after_rparen = self._next_non_nl_index(lookahead + 1)
                if after_rparen is not None and self.tokens[after_rparen].code in (
                    CODE_RBRACE,
                    CODE_WHILE,
                ):
                    self.pos = lookahead
                    return
        self.emit_recovery_error(RECOVERY_INSERT, "Ожидался символ ';' в конце оператора", end)
        self.recover_stmt_terminator()

    def parse_assignment_operator_and_expr(self):
        self.skip_nl()
        op = self.peek()
        if self.is_extra_identifier_before_assignment(op):
            self.add_err("Лишний идентификатор перед оператором присваивания", op)
            self.advance()
            self.skip_nl()
            op = self.peek()

        self.recover_assignment_operator_noise()
        op = self.peek()
        if op is None or op.code in self.STMT_FOLLOW:
            if op is None and self.current_stmt_start_token is not None:
                self.suffix_anchor_token = self.current_stmt_start_token
            self.emit_recovery_error(RECOVERY_INSERT, self.assignment_operator_error_message(op), op)
            return False

        if op.code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN):
            self.advance()
            self.parse_arith_expr()
            return True

        if op.code in (CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_NOT):
            self.emit_recovery_error(RECOVERY_INSERT, self.assignment_operator_error_message(op), op)
            self.parse_arith_expr()
            return True
        self.add_err(self.assignment_operator_error_message(op), op)
        if op.code == CODE_ERROR and self._is_operator_like_error(op):
            self.advance()
            self.parse_arith_expr()
            return True

        self.sync_to_follow("STMT")
        if self.peek() and self.peek().code == CODE_SEMICOLON:
            self.advance()
        return False

    def recover_stmt_terminator(self):
        self.sync_to_follow("STMT")
        if self.peek() and self.peek().code == CODE_SEMICOLON:
            self.advance()

    def parse_assignment_left(self):
        tok = self.peek()
        if self._is_corrupted_identifier(tok):
            self.advance()
            return True
        if self.is_broken_statement_identifier(tok):
            self.advance()
            return True
        if tok and tok.code == CODE_IDENTIFIER:
            self.advance()
            return False

        action = RECOVERY_INSERT
        if tok and tok.code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN):
            action = RECOVERY_REPLACE
        self.emit_recovery_error(
            action,
            "Ожидался идентификатор (начало оператора присваивания)",
            tok,
        )
        if tok and tok.code == CODE_ERROR and self._is_operator_like_error(tok):
            return False
        nxt = self.next_non_nl(self.pos + 1)
        if nxt and nxt.code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN):
            self.advance()
        else:
            self.sync_to_follow("STMT", concrete_first("ASSIGN_OP"))
        return False

    def is_broken_statement_identifier(self, tok):
        if not (tok and tok.code == CODE_ERROR and tok.lexeme):
            return False
        if self._is_operator_like_error(tok):
            return False
        if not any(ch.isalpha() for ch in tok.lexeme):
            return False
        nxt = self.next_non_nl(self.pos + 1)
        return bool(nxt and nxt.code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN))

    def is_extra_identifier_before_assignment(self, tok):
        nxt = self.next_non_nl(self.pos + 1)
        return bool(
            tok
            and tok.code == CODE_IDENTIFIER
            and nxt
            and nxt.code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN)
        )

    def is_condition_like_sequence(self, start):
        i = self._skip_newlines_index(start)
        if i >= len(self.tokens):
            return False
        tok = self.tokens[i]
        if tok.code == CODE_LPAREN:
            close_pos = self._paren_wrapped_value_before_compare_from(i)
            return close_pos is not None
        if tok.code not in (CODE_IDENTIFIER, CODE_ERROR):
            return False
        if tok.code == CODE_ERROR and not self._is_corrupted_identifier(tok):
            return False
        i = self._skip_noise_before_condition_operator(i + 1)
        return i < len(self.tokens) and self._is_condition_operator_token(self.tokens[i])

    def is_condition_prefix_start(self, tok):
        return bool(
            tok
            and (
                tok.code in (CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_NOT)
                or (tok.code == CODE_ERROR and self._is_corrupted_identifier(tok))
            )
        )

    def _skip_newlines_index(self, start):
        i = start
        while i < len(self.tokens) and self.tokens[i].code == CODE_NEWLINE:
            i += 1
        return i

    def _find_stray_open_brace_run_before_while(self, start_idx):
        i = self._skip_newlines_index(start_idx)
        if i >= len(self.tokens):
            return None
        t = self.tokens[i]
        if t.code == CODE_ERROR and self._is_repeated_symbol_error(t, "{"):
            w = self._next_non_nl_index(i + 1)
            if w is not None and self.tokens[w].code == CODE_WHILE:
                return (i, i)
            return None
        if t.code != CODE_LBRACE:
            return None
        first_idx = i
        last_idx = i
        j = i
        while True:
            if j >= len(self.tokens) or self.tokens[j].code != CODE_LBRACE:
                return None
            last_idx = j
            w = self._next_non_nl_index(j + 1)
            if w is None:
                return None
            if self.tokens[w].code == CODE_WHILE:
                return (first_idx, last_idx)
            if self.tokens[w].code != CODE_LBRACE:
                return None
            j = w

    def _consume_stray_open_braces_run_before_while(self):
        span = self._find_stray_open_brace_run_before_while(self.pos)
        if span is None:
            return False
        first_i, last_i = span
        first_t = self.tokens[first_i]
        last_t = self.tokens[last_i]
        parts = []
        for k in range(first_i, last_i + 1):
            c = self.tokens[k].code
            if c == CODE_NEWLINE:
                continue
            if c not in (CODE_LBRACE, CODE_ERROR):
                continue
            parts.append(self.tokens[k].lexeme or "")
        frag = "".join(parts)
        self.errors.append(
            ParseError(
                frag,
                first_t.line,
                first_t.start_pos,
                last_t.end_pos,
                "Ожидался символ '}'",
            )
        )
        self.pos = self._next_non_nl_index(last_i + 1)
        self.skip_nl()
        self._suppress_rbrace_expect_after_stray_lbrace = True
        return True

    def _consume_wrong_lbrace_semicolon_while_instead_of_rbrace(self):
        tok = self.peek()
        if not tok or tok.code != CODE_LBRACE:
            return False
        k = self._next_non_nl_index(self.pos + 1)
        if k is None or self.tokens[k].code != CODE_SEMICOLON:
            return False
        w = self._next_non_nl_index(k + 1)
        if w is None or self.tokens[w].code != CODE_WHILE:
            return False
        self.add_err("Ожидался символ '}'", tok)
        self.pos = w
        self.skip_nl()
        self._suppress_rbrace_expect_after_stray_lbrace = True
        return True

    def _consume_stray_open_brace_before_rbrace_semicolon_while(self):
        tok = self.peek()
        if not tok or tok.code != CODE_LBRACE:
            return False
        j = self._next_non_nl_index(self.pos + 1)
        if j is None or self.tokens[j].code != CODE_RBRACE:
            return False
        w = self._next_non_nl_index(j + 1)
        if w is None:
            return False
        if self.tokens[w].code == CODE_WHILE:
            self.add_extra_symbol_error(tok)
            self.advance()
            self.skip_nl()
            return True
        if self.tokens[w].code != CODE_SEMICOLON:
            return False
        w2 = self._next_non_nl_index(w + 1)
        if w2 is None or self.tokens[w2].code != CODE_WHILE:
            return False
        self.add_extra_symbol_error(tok)
        self.advance()
        self.skip_nl()
        return True

    def _skip_noise_before_condition_operator(self, start):
        i = self._skip_newlines_index(start)
        while (
            i < len(self.tokens)
            and self.tokens[i].code == CODE_ERROR
            and not self._is_comparison_like_error(self.tokens[i])
            and not self._is_operator_like_error(self.tokens[i])
        ):
            i = self._skip_newlines_index(i + 1)
        return i

    def _is_condition_operator_token(self, tok):
        return bool(
            tok
            and (
                tok.code == CODE_COMPARE
                or (tok.code == CODE_ERROR and self._is_comparison_like_error(tok))
            )
        )

    def recover_assignment_operator_noise(self):
        op = self.peek()
        if not (op and op.code == CODE_ERROR):
            return

        self.recover_to_first(
            "ASSIGN_OP",
            blocking_error=self._is_operator_like_error,
            commit_on_failure=True,
            commit_on_blocking=True,
        )

    def parse_arith_expr(self):
        self.skip_nl()
        if not self.parse_stmt_expr_value_slot("Ожидалось значение выражения (идентификатор или число)"):
            return
        while True:
            before_newlines = self.pos
            self.skip_nl()
            tok = self.peek()
            if not tok or tok.code != CODE_ARITH:
                self.pos = before_newlines
                return
            self.advance()
            if not self.parse_stmt_expr_value_slot("Ожидалось значение выражения после арифметического оператора"):
                return

    def parse_stmt_expr_value_slot(self, msg):
        if self.parse_value(msg):
            return True
        if self.is_while_boundary_token():
            return False
        self.sync_to_follow("STMT")
        return False

    def operator_error_kind(self, tok):
        if not (tok and tok.code == CODE_ERROR and tok.lexeme):
            return None
        if any(ch.isalnum() for ch in tok.lexeme):
            return None
        first_char = tok.lexeme[0]
        if first_char in "<>=!":
            return "compare_like"
        if any(ch in "<>=!+-*/" for ch in tok.lexeme):
            return "assign_like"
        return None

    def _is_operator_like_error(self, tok):
        return self.operator_error_kind(tok) in {"assign_like", "compare_like"}

    def _is_corrupted_identifier(self, tok):
        return bool(tok and tok.code == CODE_ERROR and tok.lexeme and tok.lexeme[0].isalpha())

    def _is_corrupted_statement_identifier(self, tok):
        if not self._is_corrupted_identifier(tok):
            return False
        i = self.pos + 1
        while i < len(self.tokens) and self.tokens[i].code in (CODE_ERROR, CODE_NEWLINE):
            if self.tokens[i].code == CODE_ERROR and self._is_operator_like_error(self.tokens[i]):
                return True
            i += 1
        return i < len(self.tokens) and self.tokens[i].code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN)

    def _is_repeated_symbol_error(self, tok, symbol):
        return (
            tok
            and tok.code == CODE_ERROR
            and tok.lexeme
            and len(tok.lexeme) > 1
            and set(tok.lexeme) == {symbol}
        )

    def expected_repeated_symbol(self, code):
        return {
            CODE_LBRACE: "{",
            CODE_RBRACE: "}",
        }.get(code)

    def is_repeated_closing_brace_error(self, tok):
        return self._is_repeated_symbol_error(tok, "}")

    def _next_significant_code(self, start):
        tok = self.next_non_nl(start)
        return tok.code if tok else None

    def parse_value(self, msg):
        self.skip_nl()
        tok = self.peek()
        while tok and tok.code == CODE_ERROR:
            if self.is_while_boundary_token(tok):
                self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
                return False

            if self._is_value_like_error(tok):
                self.advance()
                return True

            nxt = self.next_non_nl(self.pos + 1)
            if nxt and (
                nxt.code in (CODE_IDENTIFIER, CODE_DIGIT)
                or (nxt.code == CODE_ERROR and self._is_value_like_error(nxt))
            ):
                self.advance()
                self.skip_nl()
                tok = self.peek()
                continue

            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            self.advance()
            return False

        if self.is_while_boundary_token(tok):
            self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
            return False

        if tok and tok.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.advance()
            return True
        self.emit_recovery_error(RECOVERY_INSERT, msg, tok)
        return False

    def _is_value_like_error(self, tok):
        return bool(
            tok
            and tok.code == CODE_ERROR
            and tok.lexeme
            and (tok.lexeme[0].isalnum() or tok.lexeme[0] in ".")
        )

    def parse_condition(self):
        self.skip_nl()
        if self.peek() is None:
            return
        self.consume_extra_keywords({CODE_REPEAT, CODE_WHILE})
        while self.consume_extra_semicolon_before_more_input():
            pass
        self.consume_condition_prefix_noise()
        self.parse_condition_term()
        if not self.parse_condition_logic_chain():
            return
        self.parse_condition_tail_noise()

    def consume_condition_prefix_noise(self):
        while self.peek() and self.peek().code == CODE_ERROR:
            tok = self.peek()
            if not self.is_condition_prefix_noise_error(tok):
                return
            nxt = self.next_non_nl(self.pos + 1)
            if not nxt:
                return
            if nxt.code in (CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_NOT):
                self.advance()
                self.skip_nl()
                continue
            if nxt.code == CODE_ERROR and self._is_corrupted_identifier(nxt):
                self.advance()
                self.skip_nl()
                continue
            return

    def parse_condition_logic_chain(self):
        while True:
            self.skip_nl()
            tok = self.peek()
            if tok and tok.code in (CODE_AND, CODE_OR):
                if not self.parse_logic_op_slot():
                    return False
                self.parse_condition_term()
                continue
            break
        return True

    def parse_logic_op_slot(self):
        op = self.advance()
        self.skip_nl()
        nxt = self.peek()
        if nxt is None or nxt.code in self.CONDITION_FOLLOW or nxt.code in (CODE_AND, CODE_OR):
            self.emit_recovery_error(
                RECOVERY_INSERT,
                "После логического оператора ожидалось условие",
                op,
            )
            return False
        return True

    def parse_condition_tail_noise(self):
        self.skip_nl()
        tok = self.peek()
        if tok and tok.code not in self.CONDITION_FOLLOW:
            if tok.code == CODE_ERROR:
                if self.is_trailing_separator_lexical_noise(tok):
                    has_semicolon = self.has_following_semicolon()
                    consumed = 0
                    last_tok = tok
                    while self.peek() and self.peek().code == CODE_ERROR:
                        last_tok = self.advance()
                        consumed += 1
                    first_lx = (tok.lexeme or "") if tok else ""
                    want_semicolon_hint = (
                        not has_semicolon
                        and consumed == 1
                        and len(first_lx) == 1
                        and first_lx != ":"
                    )
                    if want_semicolon_hint:
                        self.emit_recovery_error(
                            RECOVERY_INSERT,
                            "Ожидался символ ';' в конце конструкции",
                            last_tok,
                        )
                    self.condition_progress = max(self.condition_progress, 5)
                    return
                elif not self.has_following_semicolon():
                    self.add_missing_semicolon_after_previous()
                while self.peek() and self.peek().code == CODE_ERROR:
                    self.advance()
                return
            if tok.code in (CODE_REPEAT, CODE_WHILE):
                self.consume_extra_keywords({CODE_REPEAT, CODE_WHILE})
                return
            if tok.code in (CODE_ARITH, CODE_LPAREN, CODE_RPAREN, CODE_LBRACE, CODE_RBRACE):
                self.consume_extra_symbols(
                    {
                        CODE_ARITH,
                        CODE_LPAREN,
                        CODE_RPAREN,
                        CODE_LBRACE,
                        CODE_RBRACE,
                    }
                )
                return
            self.add_err(
                f"Ожидается логический оператор (and, or) или конец условия перед '{tok.lexeme}'",
                tok,
                fragment="" if tok and tok.code == CODE_IDENTIFIER else None,
            )
            self.sync_to_follow("CONDITION")

    def has_following_semicolon(self):
        i = self.pos
        while i < len(self.tokens):
            code = self.tokens[i].code
            if code == CODE_SEMICOLON:
                return True
            if code not in (CODE_ERROR, CODE_NEWLINE, CODE_RPAREN):
                return False
            i += 1
        return False

    def is_trailing_separator_lexical_noise(self, tok):
        return bool(
            tok
            and tok.code == CODE_ERROR
            and self.is_separator_punctuation_error(tok)
            and self.condition_progress >= 4
            and self.only_errors_until_eof_or_semicolon(self.pos)
        )

    def is_separator_punctuation_error(self, tok):
        return bool(
            tok
            and tok.lexeme
            and all(ch in ".,:" for ch in tok.lexeme)
        )

    def only_errors_until_eof_or_semicolon(self, start):
        i = start
        while i < len(self.tokens):
            code = self.tokens[i].code
            if code == CODE_SEMICOLON:
                return True
            if code not in (CODE_ERROR, CODE_NEWLINE):
                return False
            i += 1
        return True

    def parse_condition_term(self):
        self.skip_nl()
        self.consume_unary_not_in_condition()

        if self.peek() and self.peek().code == CODE_LPAREN:
            if self.try_parenthesized_left_operand():
                return
            self.parse_parenthesized_condition_term()
            return

        self.parse_comparison()

    def consume_unary_not_in_condition(self):
        if self.peek() and self.peek().code == CODE_NOT:
            self.advance()
            self.skip_nl()

    def parse_parenthesized_condition_term(self):
        open_paren = self.advance()
        self.skip_nl()
        incomplete_parenthesized_condition = False
        if self.peek() and self.peek().code in (CODE_RPAREN, CODE_SEMICOLON):
            anchor = self.peek()
            self.add_incomplete_comparison_errors(anchor)
            if anchor.code == CODE_RPAREN:
                self.advance()
            incomplete_parenthesized_condition = True
        else:
            self.parse_condition()
        self.skip_nl()
        if not incomplete_parenthesized_condition and not self.take(CODE_RPAREN):
            self.add_err("Не хватает «)».", open_paren)

    def add_incomplete_comparison_errors(self, anchor):
        self.emit_recovery_error(RECOVERY_INSERT, "В условии ожидался идентификатор", anchor)
        self.emit_recovery_error(RECOVERY_INSERT, "Ожидался оператор сравнения (<, >, ==, ...)", anchor)
        self.emit_recovery_error(RECOVERY_INSERT, "Ожидались идентификатор или целое число в условии", anchor)

    def try_parenthesized_left_operand(self):
        close_pos = self._paren_wrapped_value_before_compare()
        if close_pos is None:
            return False

        self.advance()
        self.skip_nl()
        self.parse_value("В условии ожидался идентификатор")
        self.skip_nl()
        self.advance()
        rel_ok = self.parse_rel_op_slot()
        if rel_ok:
            self.parse_rhs_slot()
        return True

    def _paren_wrapped_value_before_compare(self):
        return self._paren_wrapped_value_before_compare_from(self.pos)

    def _paren_wrapped_value_before_compare_from(self, start):
        if start >= len(self.tokens) or self.tokens[start].code != CODE_LPAREN:
            return None
        value_pos = start + 1
        while value_pos < len(self.tokens) and self.tokens[value_pos].code == CODE_NEWLINE:
            value_pos += 1
        if value_pos >= len(self.tokens) or self.tokens[value_pos].code not in (CODE_IDENTIFIER, CODE_DIGIT, CODE_ERROR):
            return None
        close_pos = value_pos + 1
        while close_pos < len(self.tokens) and self.tokens[close_pos].code == CODE_NEWLINE:
            close_pos += 1
        after_close = close_pos + 1
        while after_close < len(self.tokens) and self.tokens[after_close].code == CODE_NEWLINE:
            after_close += 1
        if (
            close_pos < len(self.tokens)
            and self.tokens[close_pos].code == CODE_RPAREN
            and after_close < len(self.tokens)
            and (
                self.tokens[after_close].code == CODE_COMPARE
                or (
                    self.tokens[after_close].code == CODE_ERROR
                    and self._is_comparison_like_error(self.tokens[after_close])
                )
            )
        ):
            return close_pos
        return None

    def parse_comparison(self):
        self.skip_nl()
        ok, left_was_bad_token = self.parse_comparison_left_operand()
        if not ok:
            return
        rel_ok = self.parse_rel_op_slot(left_was_bad_token)
        if rel_ok:
            self.parse_rhs_slot()
        self._consume_malformed_comma_decimal_rhs_suffix()

    def _consume_malformed_comma_decimal_rhs_suffix(self):
        tok = self.peek()
        if not (tok and tok.code == CODE_ERROR and tok.lexeme == ","):
            return
        nxi = self._next_non_nl_index(self.pos + 1)
        if not (nxi and self.tokens[nxi].code == CODE_DIGIT):
            return
        self.advance()
        self.condition_progress = max(self.condition_progress, 4)
        self.advance()
        self.skip_nl()

    def parse_comparison_left_operand(self):
        left = self.peek()
        left_was_bad_token = False
        if self.try_recover_semicolon_split_condition_identifier():
            return True, left_was_bad_token
        if left and left.code == CODE_IDENTIFIER:
            self.condition_progress = max(self.condition_progress, 2)
            self.advance()
            return True, left_was_bad_token

        if left and left.code == CODE_ERROR and left.lexeme and left.lexeme[0].isalpha():
            self.condition_progress = max(self.condition_progress, 2)
            self.advance()
            self.skip_nl()
            op = self.peek()
            if not op or op.code != CODE_COMPARE:
                left_was_bad_token = True
            return True, left_was_bad_token

        if left and left.code == CODE_ERROR:
            nxt = self.next_non_nl(self.pos + 1)
            if self.is_condition_lhs_start(nxt) or self.has_lhs_after_prefix_noise(self.pos + 1):
                self.advance()
                self.skip_nl()
                lhs = self.peek()
                if lhs and lhs.code in (CODE_IDENTIFIER, CODE_DIGIT):
                    self.condition_progress = max(self.condition_progress, 2)
                    self.advance()
                elif lhs and lhs.code == CODE_ERROR and self._is_corrupted_identifier(lhs):
                    self.condition_progress = max(self.condition_progress, 2)
                    self.advance()
                return True, left_was_bad_token

            self.add_err("В условии ожидался идентификатор", left)
            self.advance()
            left_was_bad_token = True
            self.skip_nl()
            if self.peek() is None or self.peek().code in (CODE_SEMICOLON, CODE_RPAREN):
                anchor = self.peek() or left
                self.emit_recovery_error(RECOVERY_INSERT, "Ожидался оператор сравнения (<, >, ==, ...)", anchor)
                self.emit_recovery_error(
                    RECOVERY_INSERT,
                    "Ожидались идентификатор или целое число в условии",
                    anchor,
                )
                return False, left_was_bad_token
            return True, left_was_bad_token

        if left and left.code == CODE_ARITH:
            self.add_err("Ожидался оператор сравнения (<, >, ==, ...)", left)
            self.add_err("В условии ожидался идентификатор перед сравнением", left)
            self.add_extra_symbol_error(left)
            self.advance()
            self.sync_to_follow("CONDITION", concrete_first("LOGIC_OP"))
            return False, left_was_bad_token

        if left and left.code == CODE_DIGIT:
            self.emit_recovery_error(RECOVERY_INSERT, "В условии ожидался идентификатор", left)
            self.condition_progress = max(self.condition_progress, 2)
            left_was_bad_token = False
            return True, left_was_bad_token

        if left and left.code in (CODE_SEMICOLON, CODE_RPAREN):
            self.emit_recovery_error(RECOVERY_INSERT, "В условии ожидался идентификатор", left)
            self.emit_recovery_error(RECOVERY_INSERT, "Ожидался оператор сравнения (<, >, ==, ...)", left)
            self.emit_recovery_error(
                RECOVERY_INSERT,
                "Ожидались идентификатор или целое число в условии",
                left,
            )
            return False, left_was_bad_token

        self.add_err("В условии ожидался идентификатор", left)
        if left and left.code not in (CODE_COMPARE, CODE_SEMICOLON, CODE_RPAREN):
            self.advance()
            left_was_bad_token = True
        return True, left_was_bad_token

    def is_condition_lhs_start(self, tok):
        return bool(
            tok
            and (
                tok.code == CODE_IDENTIFIER
                or tok.code == CODE_LPAREN
                or self._is_corrupted_identifier(tok)
            )
        )

    def is_condition_prefix_noise_error(self, tok):
        if not tok or tok.code != CODE_ERROR or not tok.lexeme:
            return False
        first = tok.lexeme[0]
        if first in "<>=!|&+-*/":
            return False
        return True

    def has_lhs_after_prefix_noise(self, start_pos):
        i = start_pos
        while i < len(self.tokens):
            tok = self.tokens[i]
            if tok.code == CODE_NEWLINE:
                i += 1
                continue
            if self.is_condition_lhs_start(tok):
                return True
            if tok.code in (CODE_SEMICOLON, CODE_RPAREN, CODE_COMPARE, CODE_AND, CODE_OR):
                return False
            if self.is_condition_prefix_noise_error(tok):
                i += 1
                continue
            return False
        return False

    def _bump_condition_progress_after_wrong_rel_op(self, op):
        self.condition_progress = max(self.condition_progress, 3)
        if not op:
            return
        nxt_i = self._next_non_nl_index(self.pos + 1)
        if nxt_i is None:
            return
        nxt = self.tokens[nxt_i]
        if nxt.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.condition_progress = max(self.condition_progress, 4)
            return
        if nxt.code == CODE_ERROR and (
            self._is_value_like_error(nxt) or self._is_float_literal_lexical_error(nxt)
        ):
            self.condition_progress = max(self.condition_progress, 4)

    def _is_float_literal_lexical_error(self, tok):
        if not (tok and tok.code == CODE_ERROR and tok.lexeme):
            return False
        if "." not in tok.lexeme:
            return False
        head = tok.lexeme.lstrip("+-")
        if not head or not head[0].isdigit():
            return False
        return all(ch.isdigit() or ch == "." for ch in head)

    def _missing_comparison_before_rhs_value_token(self, tok):
        if not (tok and tok.code == CODE_ERROR):
            return False
        if self._is_comparison_like_error(tok):
            return False
        if self._is_float_literal_lexical_error(tok):
            return True
        return bool(self._is_value_like_error(tok))

    def _identifier_starts_body_assignment_at(self, idx):
        if idx >= len(self.tokens) or self.tokens[idx].code != CODE_IDENTIFIER:
            return False
        nxt_i = self._next_non_nl_index(idx + 1)
        if nxt_i is None:
            return False
        nxt = self.tokens[nxt_i]
        if nxt.code in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN):
            return True
        if nxt.code == CODE_ERROR and self._is_operator_like_error(nxt):
            return True
        return False

    def consume_identifier_junk_before_open_brace(self):
        junk_tail = None
        while self.peek() and self.peek().code == CODE_IDENTIFIER:
            nxt = self.next_non_nl(self.pos + 1)
            if nxt and nxt.code == CODE_LBRACE:
                break
            nxt_i = self._next_non_nl_index(self.pos + 1)
            if nxt_i is None:
                break
            if self.tokens[nxt_i].code != CODE_IDENTIFIER:
                break
            if self._identifier_starts_body_assignment_at(nxt_i):
                break
            junk = self.peek()
            self.add_err(f"Лишний токен '{junk.lexeme}'", junk)
            junk_tail = junk
            self.advance()
            self.skip_nl()
        if junk_tail is not None:
            self.suffix_anchor_token = junk_tail

    def _consume_extra_rbrace_before_opening_body_brace(self):
        tok = self.peek()
        if not tok or tok.code != CODE_RBRACE:
            return
        nxt = self._next_non_nl_index(self.pos + 1)
        if nxt is None or self.tokens[nxt].code != CODE_LBRACE:
            return
        self.add_extra_symbol_error(tok)
        self.advance()
        self.skip_nl()

    def parse_rel_op_slot(self, left_was_bad_token=False):
        self.skip_nl()
        while self.consume_extra_semicolon_before_more_input():
            pass
        op = self.peek()
        if op and op.code == CODE_ERROR and op.lexeme == "@":
            self.add_err(f"Недопустимая лексема '@' (лексическая ошибка)", op)
            self.advance()
            self.skip_nl()
            op2 = self.peek()
            if op2 and op2.code == CODE_DIGIT:
                nxi = self._next_non_nl_index(self.pos + 1)
                if nxi is not None and self.tokens[nxi].code == CODE_COMPARE:
                    self.add_extra_symbol_error(op2)
                    self.advance()
                    self.skip_nl()
            return self.parse_rel_op_slot(left_was_bad_token)
        if op and op.code == CODE_ERROR:
            self.recover_to_first(
                "REL_OP",
                blocking_error=self._is_comparison_like_error,
                commit_on_blocking=True,
            )
            op = self.peek()
        if left_was_bad_token and op and op.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.sync_to_follow("CONDITION", concrete_first("LOGIC_OP"))
            return False
        if op is None or op.code in (CODE_SEMICOLON, CODE_RPAREN):
            return False
        if op.code != CODE_COMPARE:
            if op.code == CODE_ERROR and self._is_comparison_like_error(op):
                self.add_err(self.comparison_operator_error_message(op), op)
                self.condition_progress = max(self.condition_progress, 3)
                self.advance()
                return True
            if op.code in (CODE_IDENTIFIER, CODE_DIGIT, CODE_LPAREN, CODE_NOT):
                self.emit_recovery_error(RECOVERY_INSERT, self.comparison_operator_error_message(op), op)
                self.condition_progress = max(self.condition_progress, 3)
                return True
            if op.code == CODE_ERROR:
                if self._missing_comparison_before_rhs_value_token(op):
                    self.emit_recovery_error(
                        RECOVERY_INSERT,
                        self.comparison_operator_error_message(op),
                        op,
                    )
                    self.condition_progress = max(self.condition_progress, 3)
                    self.condition_progress = max(self.condition_progress, 4)
                    self.sync_to_follow("CONDITION", concrete_first("LOGIC_OP"))
                    return False
                rhs_missing = self.missing_rhs_after_comparison_noise()
                fragment = "" if rhs_missing else op.lexeme
                self.add_err(self.comparison_operator_error_message(op), op, fragment=fragment)
                if rhs_missing:
                    anchor = self.next_non_nl(self.pos + 1)
                    if anchor:
                        self.emit_recovery_error(
                            RECOVERY_INSERT,
                            "Ожидались идентификатор или целое число в условии",
                            anchor,
                        )
                    else:
                        self.emit_recovery_error(
                            RECOVERY_INSERT,
                            "Ожидались идентификатор или целое число в условии",
                            op,
                        )
            else:
                self.add_err(self.comparison_operator_error_message(op), op)
            self._bump_condition_progress_after_wrong_rel_op(op)
            self.sync_to_follow("CONDITION", concrete_first("LOGIC_OP"))
            return False
        self.condition_progress = max(self.condition_progress, 3)
        self.advance()
        return True

    def parse_rhs_slot(self):
        self.skip_nl()
        rhs = self.peek()
        if self.parse_condition_rhs_value_slot(rhs):
            return
        self.sync_to_follow("CONDITION", concrete_first("LOGIC_OP"))

    def parse_condition_rhs_value_slot(self, rhs):
        while self.consume_extra_semicolon_before_more_input():
            rhs = self.peek()
        if rhs and rhs.code == CODE_ERROR:
            if rhs.lexeme and rhs.lexeme[0] in "<>=!+-*/":
                self.add_err("Ожидались идентификатор или целое число в условии (лексическая ошибка)", rhs)
                self.advance()
                return True
            self.condition_progress = max(self.condition_progress, 4)
            self.advance()
            return True
        if rhs and rhs.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.condition_progress = max(self.condition_progress, 4)
            self.advance()
            return True
        if rhs is not None:
            self.emit_recovery_error(
                RECOVERY_INSERT,
                "Ожидались идентификатор или целое число в условии",
                rhs,
            )
        return False

    def missing_rhs_after_comparison_noise(self):
        i = self.pos
        while i < len(self.tokens):
            tok = self.tokens[i]
            if tok.code == CODE_NEWLINE:
                i += 1
                continue
            if tok.code == CODE_ERROR and not self._is_value_like_error(tok):
                i += 1
                continue
            if tok.code in (CODE_SEMICOLON, CODE_RPAREN, CODE_AND, CODE_OR):
                return True
            return tok.code not in (CODE_IDENTIFIER, CODE_DIGIT) and not (
                tok.code == CODE_ERROR and self._is_value_like_error(tok)
            )
        return True

    def parse_trailing(self):
        self.skip_nl()
        while self.peek():
            tok = self.peek()
            if tok.code == CODE_NEWLINE:
                self.advance()
                continue
            if tok.code == CODE_ERROR:
                self.advance()
                continue
            self.add_err("Лишние символы после завершения конструкции", tok)
            self.advance()

    def _is_comparison_like_error(self, tok):
        return self.operator_error_kind(tok) == "compare_like"

    def wrong_body_closer_for(self, tok):
        if not tok:
            return None, None
        if tok.code == CODE_LPAREN:
            return CODE_RPAREN, None
        if tok.code == CODE_ERROR and tok.lexeme == "[":
            return None, "]"
        return None, None

    def is_wrong_body_bracket(self, tok):
        return bool(tok and tok.code == CODE_ERROR and tok.lexeme in ("[", "]"))


def filter_tokens_for_parser(tokens):
    return [t for t in tokens if t.code != TOKEN_TYPES["WHITESPACE"][0]]


def collect_lexer_errors(tokens):
    err_code = TOKEN_TYPES["ERROR"][0]
    lexer_errors = []
    prev_significant = None
    seen_while = False
    after_construction_semicolon = False
    for token in tokens:
        if token.code == err_code:
            if token.lexeme and all(ch in "<>=!+-*/%" for ch in token.lexeme):
                if token.lexeme not in ("!",):
                    if token.code not in (CODE_WHITESPACE, CODE_NEWLINE):
                        prev_significant = token
                    continue
            if token.lexeme and token.lexeme != "!" and token.lexeme[0] in "<>=!+-*/%":
                if token.code not in (CODE_WHITESPACE, CODE_NEWLINE):
                    prev_significant = token
                continue
            message = _lexer_message_for_token(token)
            if after_construction_semicolon or (
                prev_significant and prev_significant.code == CODE_SEMICOLON
            ):
                message = (
                    f"Лишняя лексема после завершения конструкции: "
                    f"'{token.lexeme}' (лексическая ошибка)"
                )
            elif seen_while and not after_construction_semicolon:
                message = f"Недопустимая лексема '{token.lexeme}' (лексическая ошибка)"

            split_parts = _split_keyword_like_error_with_edge_noise(token, message)
            if split_parts is not None:
                lexer_errors.extend(split_parts)
                if token.code not in (CODE_WHITESPACE, CODE_NEWLINE):
                    prev_significant = token
                continue

            fragment = token.lexeme
            start_pos = token.start_pos
            end_pos = token.end_pos
            affix_noise = _keyword_affix_noise_fragment(token)
            if affix_noise is not None:
                fragment, start_pos, end_pos = affix_noise
            lexer_errors.append(
                ParseError(
                    fragment,
                    token.line,
                    start_pos,
                    end_pos,
                    message,
                )
            )
        if token.code not in (CODE_WHITESPACE, CODE_NEWLINE):
            if token.code == CODE_WHILE:
                seen_while = True
            elif token.code == CODE_SEMICOLON and seen_while:
                after_construction_semicolon = True
            prev_significant = token
    return lexer_errors


def _dedup_errors(errors):
    seen = set()
    out = []
    for err in errors:
        key = (err.line, err.start_pos, err.end_pos, err.fragment, err.message)
        if key in seen:
            continue
        seen.add(key)
        out.append(err)
    return out


def _suppress_lexer_brace_dup_after_wrong_open(parser_errors, lex_err):
    frag = lex_err.fragment or ""
    if len(frag) < 2 or set(frag) != {"}"}:
        return False
    msg = lex_err.message or ""
    if "Получена последовательность" not in msg:
        return False
    if "Ожидался символ '}'" not in msg:
        return False
    for pe in parser_errors:
        if (
            pe.message == "Ожидался символ '{'"
            and pe.fragment == frag
            and pe.line == lex_err.line
            and pe.start_pos == lex_err.start_pos
            and pe.end_pos == lex_err.end_pos
        ):
            return True
    return False


def _suppress_lexer_double_lbrace_when_parser_missing_close(parser_errors, lex_err):
    frag = lex_err.fragment or ""
    if frag != "{{" or "Получена последовательность" not in (lex_err.message or ""):
        return False
    if "Ожидался символ '{'" not in (lex_err.message or ""):
        return False
    for pe in parser_errors:
        if pe.message == "Ожидался символ '}'" and pe.line == lex_err.line:
            return True
    return False


def _is_bracket_replacement_error(err):
    return (
        (err.fragment == "[" and err.message == "Ожидался символ '{'")
        or (err.fragment == "]" and err.message == "Ожидался символ '}'")
    )


def _without_replaced_bracket_lexer_errors(lexer_errors, parser_errors):
    replaced = {
        (err.line, err.start_pos, err.end_pos, err.fragment)
        for err in parser_errors
        if _is_bracket_replacement_error(err)
    }
    return [
        err
        for err in lexer_errors
        if (err.line, err.start_pos, err.end_pos, err.fragment) not in replaced
    ]


def _without_keyword_replacement_lexer_errors(lexer_errors, parser_errors):
    keyword_replaced_spans = {
        (err.line, err.start_pos, err.end_pos, err.fragment)
        for err in parser_errors
        if err.message.startswith("Ожидалось ключевое слово ")
    }
    return [
        err
        for err in lexer_errors
        if not (
            (
                err.message == "Ожидался идентификатор (лексическая ошибка)"
                and (err.line, err.start_pos, err.end_pos, err.fragment) in keyword_replaced_spans
            )
            or (
                err.message.startswith("Ожидалось ключевое слово ")
                and (err.line, err.start_pos, err.end_pos, err.fragment) in keyword_replaced_spans
            )
        )
    ]


def _error_order_key(err, parser_error_ids):
    syntax_priority = 0 if id(err) in parser_error_ids else 1
    completion_priority = 1 if err.message == "Ожидался символ ';' в конце конструкции" else 0
    return (err.line, err.start_pos, err.end_pos, completion_priority, syntax_priority)


def analyze_syntax(tokens):
    lexer_errors = collect_lexer_errors(tokens)
    clean = filter_tokens_for_parser(tokens)
    result = IronsParser(clean).parse()
    lexer_errors = [
        e
        for e in lexer_errors
        if not _suppress_lexer_brace_dup_after_wrong_open(result.errors, e)
        and not _suppress_lexer_double_lbrace_when_parser_missing_close(result.errors, e)
    ]
    lexer_errors = _without_replaced_bracket_lexer_errors(lexer_errors, result.errors)
    lexer_errors = _without_keyword_replacement_lexer_errors(lexer_errors, result.errors)
    parser_error_ids = {id(err) for err in result.errors}
    all_errors = _dedup_errors(lexer_errors + result.errors)
    all_errors = sorted(all_errors, key=lambda e: _error_order_key(e, parser_error_ids))
    return ParseResult(len(all_errors) == 0, all_errors, result.ast_spans)