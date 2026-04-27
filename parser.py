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


class ParseError:
    def __init__(self, fragment, line, start_pos, end_pos, message):
        self.fragment = fragment
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.message = message



class ParseResult:
    def __init__(self, ok, errors):
        self.ok = ok
        self.errors = errors


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
    if lx == keyword:
        return True
    if lx[0] != keyword[0]:
        return False
    return _levenshtein(lx, keyword) <= 2


def _lexer_message_for_token(token):
    lx = token.lexeme or ""
    if lx and all(ch in ".,:?#$%^&_`~\\|" for ch in lx):
        return f"Ожидался символ ';', найдено '{lx}' (лексическая ошибка)"
    if lx and len(lx) > 1 and len(set(lx)) == 1 and lx[0] in "{};()[]":
        ch = lx[0]
        return f"Ожидался символ '{ch}'. Получена последовательность '{lx}'."

    if lx and all(c in "<>=!+-*/" for c in lx):
        if any(c in "<>!" for c in lx):
            return "Ожидался оператор сравнения (<, >, ==, ...)"
        return "Ожидался оператор '=' или составной оператор (+=, -=, ...)"

    if _looks_like_keyword(lx, "repeat"):
        return "Ожидалось ключевое слово repeat (лексическая ошибка)"
    if _looks_like_keyword(lx, "while"):
        return "Ожидалось ключевое слово while (лексическая ошибка)"
    if _looks_like_keyword(lx, "and") or _looks_like_keyword(lx, "or") or _looks_like_keyword(lx, "not"):
        return "Ожидался логический оператор (лексическая ошибка)"
    if lx and lx[0].isalpha():
        return "Ожидался идентификатор (лексическая ошибка)"
    return "Недопустимая лексема (лексическая ошибка)"


class Parser:
    def __init__(self, tokens):
        self.tokens = list(tokens)
        self.pos = 0
        self.errors = []

    def parse(self):
        self.skip_nl()
        saw_repeat = False
        implicit_repeat = False
        repeat_error_added = False
        while not self.eof():
            self.skip_nl()
            t = self.peek()
            if t is None:
                break
            if t.code == CODE_REPEAT:
                saw_repeat = True
                break
            if t.code == CODE_ERROR:
                j = self.pos + 1
                while j < len(self.tokens) and self.tokens[j].code == CODE_NEWLINE:
                    j += 1
                if j < len(self.tokens) and self.tokens[j].code == CODE_LBRACE:
                    saw_repeat = True
                    implicit_repeat = True
                    break
                if j < len(self.tokens) and self.tokens[j].code == CODE_REPEAT:
                    self.add_err(
                        "Ожидалось ключевое слово repeat",
                        t.lexeme,
                        t.line,
                        t.start_pos,
                        t.end_pos,
                    )
                self.advance()
                continue

            # Если перед '{' стоит слово, похожее на 'repeat', считаем это
            # одной ошибкой и продолжаем как implicit repeat.
            j = self.pos + 1
            while j < len(self.tokens) and self.tokens[j].code == CODE_NEWLINE:
                j += 1
            if (
                t.code == CODE_IDENTIFIER
                and j < len(self.tokens)
                and self.tokens[j].code == CODE_LBRACE
                and _looks_like_keyword(t.lexeme, "repeat")
            ):
                self.add_err(
                    "Ожидалось ключевое слово repeat",
                    t.lexeme,
                    t.line,
                    t.start_pos,
                    t.end_pos,
                )
                saw_repeat = True
                implicit_repeat = True
                self.pos = j
                break

            if not repeat_error_added:
                self.add_err(
                    "Ожидалось ключевое слово repeat",
                    t.lexeme,
                    t.line,
                    t.start_pos,
                    t.end_pos,
                )
                repeat_error_added = True
            self.advance()
        if not saw_repeat:
            return ParseResult(False, list(self.errors))

        ok = self.repeat_while(implicit_repeat)
        self.skip_nl()
        if ok and not self.eof():
            t = self.peek()
            if (
                t.code == CODE_ERROR
                and t.lexeme
                and all(ch in ".,:?@#$%^&_`~\\|" for ch in t.lexeme)
            ):
                self.add_err(
                    f"Ожидался символ ';', найдено '{t.lexeme}' (лексическая ошибка)",
                    t.lexeme,
                    t.line,
                    t.start_pos,
                    t.end_pos,
                )
                self.pos = len(self.tokens)
                return ParseResult(False, list(self.errors))
            if t.code == CODE_SEMICOLON:
                extra_count = 1
                while self.peek_ahead(extra_count) and self.peek_ahead(extra_count).code == CODE_SEMICOLON:
                    extra_count += 1
                if (
                    extra_count == 1
                    and self.pos > 0
                    and self.tokens[self.pos - 1].code == CODE_SEMICOLON
                    and self.tokens[self.pos - 1].line == t.line
                    and self.tokens[self.pos - 1].end_pos + 1 == t.start_pos
                    and self.pos > 1
                    and self.tokens[self.pos - 2].line == t.line
                    and self.tokens[self.pos - 2].end_pos + 1 == self.tokens[self.pos - 1].start_pos
                ):
                    prev = self.tokens[self.pos - 1]
                    self.add_err(
                        "Ожидался символ ';'. Получена последовательность ';;'.",
                        ";;",
                        t.line,
                        prev.start_pos,
                        t.end_pos,
                    )
                    self.pos = len(self.tokens)
                    return ParseResult(False, list(self.errors))
            self.add_err(
                "Лишние символы после завершения конструкции",
                t.lexeme,
                t.line,
                t.start_pos,
                t.end_pos,
            )
            self.pos = len(self.tokens)
        return ParseResult(ok and self.eof(), list(self.errors))

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def peek_ahead(self, offset):
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else None

    def first_non_nl_from_index(self, i):
        while i < len(self.tokens):
            t = self.tokens[i]
            if t.code in (CODE_NEWLINE, CODE_WHITESPACE, CODE_ERROR):
                i += 1
                continue
            return t
        return None

    def advance(self):
        if self.pos < len(self.tokens):
            self.pos += 1

    def eof(self):
        return self.pos >= len(self.tokens)

    def skip_nl(self):
        while not self.eof() and self.tokens[self.pos].code == CODE_NEWLINE:
            self.pos += 1

    def skip_lex_errors(self):
        while not self.eof() and self.tokens[self.pos].code == CODE_ERROR:
            self.pos += 1

    def _looks_like_repeated_open_brace_error(self, tok):
        if not tok or tok.code != CODE_ERROR or not tok.lexeme:
            return False
        lx = tok.lexeme
        return (len(lx) >= 1 and set(lx) == {"{"}) or (len(lx) >= 1 and set(lx) == {"["})

    def _looks_like_repeated_close_brace_error(self, tok):
        if not tok or tok.code != CODE_ERROR or not tok.lexeme:
            return False
        lx = tok.lexeme
        return (len(lx) >= 1 and set(lx) == {"}"}) or (len(lx) >= 1 and set(lx) == {"]"})

    def _is_compare_like_error(self, tok):
        return (
            tok
            and tok.code == CODE_ERROR
            and tok.lexeme
            and all(ch in "<>=!" for ch in tok.lexeme)
        )

    def _consume_until_lbrace_with_diagnostics(self, got_repeat):
        saw_open_brace_lex_error = False
        while self.peek():
            c = self.peek().code
            if c == CODE_ERROR:
                if self._looks_like_repeated_open_brace_error(self.peek()):
                    saw_open_brace_lex_error = True
                self.advance()
                continue
            if c == CODE_RBRACE:
                self.emit_err_and_advance(
                    "Символ '}' здесь недопустим: перед телом цикла должна быть '{'"
                )
                continue
            if c == CODE_SEMICOLON:
                self.emit_err_and_advance(
                    "Символ ';' здесь недопустим: после «repeat» ожидается '{' перед телом цикла"
                    if got_repeat
                    else "Символ ';' здесь недопустим: перед телом цикла ожидается '{'"
                )
                continue
            if c == CODE_WHILE:
                nxt = self.first_non_nl_from_index(self.pos + 1)
                if nxt and nxt.code in (
                    CODE_RBRACE,
                    CODE_LBRACE,
                    CODE_WHILE,
                    CODE_IDENTIFIER,
                ):
                    self.emit_err_and_advance(
                        "Ключевое слово while здесь лишнее: после «repeat» ожидается '{' перед телом цикла"
                    )
                    continue
            if c == CODE_REPEAT:
                self.emit_err_and_advance(
                    "Лишнее ключевое слово repeat: перед телом цикла достаточно одного repeat и символа '{'"
                )
                continue
            if c == CODE_IDENTIFIER:
                nxt = self.first_non_nl_from_index(self.pos + 1)
                if nxt and nxt.code == CODE_LBRACE:
                    if got_repeat:
                        self.emit_err_and_advance(
                            "Лишний идентификатор перед '{': после repeat должна следовать только '{'"
                        )
                    else:
                        self.advance()
                    continue
                if got_repeat and nxt and nxt.code == CODE_IDENTIFIER:
                    self.emit_err_and_advance(
                        "Лишний идентификатор перед телом цикла (ожидалась '{' после repeat)"
                    )
                    continue
                break
            if c == CODE_DIGIT:
                nxt = self.first_non_nl_from_index(self.pos + 1)
                if nxt and nxt.code == CODE_LBRACE:
                    if got_repeat:
                        self.emit_err_and_advance(
                            "Лишний числовой литерал перед '{': после «repeat» должна следовать только '{'"
                        )
                    else:
                        self.advance()
                    continue
                break
            break
        return saw_open_brace_lex_error

    def _add_condition_identifier_error(self, tok):
        if tok is None:
            return
        if tok.code in (CODE_COMPARE, CODE_SEMICOLON, CODE_RPAREN):
            self.err_here("В условии ожидался идентификатор")
            return
        self.add_err(
            f"Ожидался идентификатор в условии, найден '{tok.lexeme}'",
            tok.lexeme,
            tok.line,
            tok.start_pos,
            tok.end_pos,
        )

    def _handle_leading_compare_like_condition(self):
        t = self.peek()
        if not self._is_compare_like_error(t):
            return False
        self.add_err(
            "В условии ожидался идентификатор",
            t.lexeme,
            t.line,
            t.start_pos,
            t.end_pos,
        )
        self.add_err(
            "Ожидался оператор сравнения (<, >, ==, ...)",
            t.lexeme,
            t.line,
            t.start_pos,
            t.end_pos,
        )
        self.advance()
        self.skip_nl()
        self.skip_lex_errors()
        val_after_bad_op = self.peek()
        if val_after_bad_op and val_after_bad_op.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.add_err(
                "В условии ожидался идентификатор",
                val_after_bad_op.lexeme,
                val_after_bad_op.line,
                val_after_bad_op.start_pos,
                val_after_bad_op.end_pos,
            )
            self.advance()
        return True

    def _take_while_skipping_errors(self):
        self.skip_nl()
        self.skip_lex_errors()
        while self.peek() and self.peek().code == CODE_IDENTIFIER and self.peek().lexeme == "do":
            self.emit_err_and_advance("Лишнее ключевое слово do перед while")
            self.skip_nl()
            self.skip_lex_errors()
        while self.peek() and self.peek().code == CODE_SEMICOLON:
            nxt = self.first_non_nl_from_index(self.pos + 1)
            if nxt and nxt.code == CODE_WHILE:
                self.emit_err_and_advance("Лишний символ ';' в данной позиции")
                self.skip_nl()
                self.skip_lex_errors()
                continue
            break
        if self.take(CODE_WHILE):
            return True
        t = self.peek()
        if t and t.code == CODE_ERROR and _looks_like_keyword(t.lexeme, "while"):
            # Лексическая ошибка по while уже диагностируется на уровне analyzer,
            # здесь только нейтрализуем и продолжаем разбор условия.
            self.advance()
            return True
        j = self.pos
        while j < len(self.tokens):
            if self.tokens[j].code == CODE_WHILE:
                self.pos = j
                self.take(CODE_WHILE)
                return True
            j += 1
        t = self.peek()
        if t and t.code == CODE_IDENTIFIER and _looks_like_keyword(t.lexeme, "while"):
            self.add_err(
                "Ожидалось ключевое слово while",
                t.lexeme,
                t.line,
                t.start_pos,
                t.end_pos,
            )
            self.advance()
            return True
        while not self.eof() and self.peek().code == CODE_ERROR:
            self.advance()
            self.skip_nl()
            self.skip_lex_errors()
            if self.take(CODE_WHILE):
                return True
        self.err_here("Ожидалось ключевое слово while")
        return False

    def take(self, code):
        t = self.peek()
        if t and t.code == code:
            self.pos += 1
            return True
        return False

    def add_err(self, msg, frag, line, s, e):
        self.errors.append(ParseError(frag, line, s, e, msg))

    def add_err_at_token(self, msg, tok):
        if tok is None:
            self.err_here(msg)
            return
        self.add_err(msg, tok.lexeme, tok.line, tok.start_pos, tok.end_pos)

    def emit_err_and_advance(self, msg):
        tok = self.peek()
        self.add_err_at_token(msg, tok)
        self.advance()

    def err_here(self, msg):
        t = self.peek()
        if t is None:
            if self.pos > 0:
                prev = self.tokens[self.pos - 1]
                self.add_err(msg, "", prev.line, prev.end_pos, prev.end_pos)
            else:
                self.add_err(msg, "EOF", 1, 1, 1)
        else:
            self.add_err(msg, t.lexeme, t.line, t.start_pos, t.end_pos)

    def recover_to(self, stop_codes, consume_stop=False):
        """
        Базовый механизм нейтрализации (в духе Айронса): отбрасывает входные
        токены до ближайшего терминала из stop_codes и позволяет продолжить
        разбор из устойчивой точки контекста.
        """
        if not stop_codes:
            return
        stop_set = set(stop_codes)
        while not self.eof() and self.tokens[self.pos].code not in stop_set:
            self.pos += 1
        if consume_stop and not self.eof() and self.tokens[self.pos].code in stop_set:
            self.pos += 1

    def sync_to(self, *codes):
        self.recover_to(codes, consume_stop=False)

    def syncstmt(self):
        self.recover_to((CODE_RBRACE, CODE_SEMICOLON, CODE_WHILE), consume_stop=False)
        if not self.eof() and self.tokens[self.pos].code == CODE_SEMICOLON:
            self.pos += 1

    def expect_token(self, code, msg, recover_codes=()):
        if self.take(code):
            return True
        t = self.peek()
        if (
            t
            and code == CODE_SEMICOLON
            and t.code == CODE_ERROR
            and t.lexeme
            and all(ch in ".,:?@#$%^&_`~\\|" for ch in t.lexeme)
        ):
            self.add_err(
                f"Ожидался символ ';', найдено '{t.lexeme}' (лексическая ошибка)",
                t.lexeme,
                t.line,
                t.start_pos,
                t.end_pos,
            )
        else:
            self.err_here(msg)
        if recover_codes:
            self.recover_to(recover_codes, consume_stop=False)
        if self.take(code):
            return True
        return False

    def expect(self, code, msg, *sync):
        return self.expect_token(code, msg, recover_codes=sync)

    def repeat_while(self, implicit_repeat=False):
        if implicit_repeat:
            self.skip_nl()
            t_bad = self.peek()
            if t_bad and t_bad.code == CODE_ERROR:
                self.add_err_at_token("Ожидалось ключевое слово repeat", t_bad)
            saw_open_brace_lex_error = self._looks_like_repeated_open_brace_error(t_bad)
            self.skip_lex_errors()
            self.skip_nl()
            if not self.take(CODE_LBRACE):
                if not saw_open_brace_lex_error:
                    self.err_here("Ожидался символ '{'")
                return False
        else:
            t = self.peek()
            if t is None:
                self.err_here("Ожидалось ключевое слово repeat")
                return False

            got_repeat = False
            if t.code == CODE_REPEAT:
                self.advance()
                got_repeat = True
            else:
                self.err_here("Ожидалось ключевое слово repeat")

            self.skip_nl()
            if not self.take(CODE_LBRACE):
                saw_open_brace_lex_error = self._consume_until_lbrace_with_diagnostics(got_repeat)
                self.skip_nl()
                if not self.take(CODE_LBRACE):
                    if not saw_open_brace_lex_error:
                        self.err_here("Ожидался символ '{'")

        # Спец-кейсы сразу после '{':
        # 1) while -> отсутствует оператор в теле;
        # 2) } -> неверное расположение закрывающей скобки.
        self.skip_nl()
        self.skip_lex_errors()
        t_start_body = self.peek()
        if t_start_body and t_start_body.code == CODE_WHILE:
            self.add_err(
                "Ожидался идентификатор (начало оператора присваивания)",
                t_start_body.lexeme,
                t_start_body.line,
                t_start_body.start_pos,
                t_start_body.end_pos,
            )
            self.add_err(
                "Ожидался оператор '=' или составной оператор (+=, -=, ...)",
                t_start_body.lexeme,
                t_start_body.line,
                t_start_body.start_pos,
                t_start_body.end_pos,
            )
            self.add_err(
                "Ожидалось значение выражения (идентификатор или число)",
                t_start_body.lexeme,
                t_start_body.line,
                t_start_body.start_pos,
                t_start_body.end_pos,
            )
        elif t_start_body and t_start_body.code == CODE_RBRACE:
            self.add_err(
                "Символ '}' в этой позиции недопустим (ожидался оператор в теле цикла)",
                t_start_body.lexeme,
                t_start_body.line,
                t_start_body.start_pos,
                t_start_body.end_pos,
            )
        else:
            self.stmt_list()

        self.skip_nl()
        if not self.take(CODE_RBRACE):
            t_here = self.peek()
            if not self._looks_like_repeated_close_brace_error(t_here):
                self.err_here("Ожидался символ '}'")
            looks_like_while_tail = (
                t_here
                and t_here.lexeme
                and (
                    (t_here.code == CODE_IDENTIFIER and _looks_like_keyword(t_here.lexeme, "while"))
                    or (t_here.code == CODE_ERROR and _looks_like_keyword(t_here.lexeme, "while"))
                )
            )
            if not looks_like_while_tail:
                self.sync_to(CODE_WHILE)
            self.take(CODE_RBRACE)

        consumed_close = self.tokens[self.pos - 1] if self.pos > 0 else None
        self.skip_nl()
        while self.peek() and self.peek().code == CODE_RBRACE:
            nxt = self.first_non_nl_from_index(self.pos + 1)
            if nxt is None:
                break
            t = self.peek()
            if nxt.code == CODE_WHILE:
                if consumed_close is not None:
                    had_rhs_value_error = any(
                        e.line == consumed_close.line
                        and e.start_pos == consumed_close.start_pos
                        and e.end_pos == consumed_close.end_pos
                        and "Ожидалось значение выражения" in e.message
                        for e in self.errors
                    )
                    if had_rhs_value_error:
                        self.advance()
                        self.skip_nl()
                        continue
                self.add_err(
                    "Лишняя '}' перед while: перед условием должна остаться одна '}' после тела",
                    t.lexeme,
                    t.line,
                    t.start_pos,
                    t.end_pos,
                )
                self.advance()
                self.skip_nl()
                continue
            if nxt.code == CODE_RBRACE:
                self.add_err(
                    "Лишняя '}' в конце тела цикла: лишние закрывающие скобки",
                    t.lexeme,
                    t.line,
                    t.start_pos,
                    t.end_pos,
                )
                self.advance()
                self.skip_nl()
                continue
            break
        if not self._take_while_skipping_errors():
            self.skip_nl()
            if self.eof():
                return False
            self.sync_to(CODE_SEMICOLON)
            self.skip_nl()
            if not self.take(CODE_SEMICOLON):
                if self.eof() and self.pos > 0:
                    prev = self.tokens[self.pos - 1]
                    self.add_err(
                        "Ожидался символ ';' в конце конструкции",
                        "EOF",
                        prev.line,
                        prev.end_pos,
                        prev.end_pos,
                    )
                elif not self.eof():
                    self.err_here(
                        "Ожидался символ ';' в конце конструкции"
                    )
            return False

        self.skip_nl()
        while self.peek() and self.peek().code in (CODE_WHILE, CODE_REPEAT):
            t_dup = self.peek()
            self.add_err(
                f"Лишнее ключевое слово {t_dup.lexeme} в условии",
                t_dup.lexeme,
                t_dup.line,
                t_dup.start_pos,
                t_dup.end_pos,
            )
            self.advance()
            self.skip_nl()
            self.skip_lex_errors()
        self.logical_expr()

        self.skip_nl()
        self.expect(CODE_SEMICOLON, "Ожидался символ ';' в конце конструкции")

        return True

    def stmt_list(self):
        while not self.eof() and self.peek().code not in (CODE_RBRACE, CODE_WHILE):
            self.skip_nl()
            self.skip_lex_errors()
            t = self.peek()
            if t is None or t.code == CODE_RBRACE or t.code == CODE_WHILE:
                return
            if t.code == CODE_IDENTIFIER and _looks_like_keyword(t.lexeme, "while"):
                # Похоже на хвост конструкции repeat ... while ...
                # Не разбираем как stmt, чтобы не порождать шумовую ошибку про ';'.
                return
            if t.code == CODE_LBRACE:
                self.add_err(
                    "Лишняя '{' в теле цикла: оператор - это идентификатор и присваивание",
                    t.lexeme,
                    t.line,
                    t.start_pos,
                    t.end_pos,
                )
                self.advance()
                continue
            self.stmt()

    def stmt(self):
        self.skip_nl()
        self.skip_lex_errors()
        t = self.peek()
        if t is None:
            self.err_here("Ожидался оператор в теле цикла")
            return
        if t.code != CODE_IDENTIFIER:
            op_t = self.peek()
            if op_t and op_t.code == CODE_COMPOUND_ASSIGN:
                self.add_err(
                    "Ожидался идентификатор для составного оператора «%s»" % op_t.lexeme,
                    op_t.lexeme,
                    op_t.line,
                    op_t.start_pos,
                    op_t.end_pos,
                )
            elif op_t and op_t.code == CODE_ASSIGN:
                self.add_err(
                    "Ожидался идентификатор для оператора '='",
                    op_t.lexeme,
                    op_t.line,
                    op_t.start_pos,
                    op_t.end_pos,
                )
            else:
                self.err_here("Ожидался идентификатор (начало оператора присваивания)")
        else:
            self.advance()

        op = self.peek()
        if op is None:
            if t.code == CODE_IDENTIFIER:
                self.add_err("Ожидался оператор присваивания", "EOF", t.line, t.end_pos, t.end_pos)
            else:
                self.add_err("Ожидался оператор присваивания", "", t.line, t.start_pos, t.start_pos)
            return
        if op.code not in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN):
            self.add_err(
                "Ожидался оператор '=' или составной оператор (+=, -=, ...)",
                op.lexeme,
                op.line,
                op.start_pos,
                op.end_pos,
            )
            self.syncstmt()
            return

        self.advance()
        rhs_start = self.peek()
        self.expr_after_assign()
        self.skip_nl()

        nxt = self.peek()
        if nxt is None:
            self.add_err("Ожидался символ ';' в конце конструкции", "EOF", op.line, op.end_pos, op.end_pos)
            return
        if nxt.code == CODE_SEMICOLON:
            self.advance()
            return
        if nxt.code == CODE_RBRACE:
            if rhs_start is not None and rhs_start.code == CODE_RBRACE:
                # Ошибка rhs уже зафиксирована в expr_after_assign, не дублируем.
                return
            return
        if nxt.code == CODE_ERROR and self._looks_like_repeated_close_brace_error(nxt):
            # Лексема вида '}}' (склеенный ERROR) должна вести себя как закрывающая
            # скобка блока, иначе syncstmt может пропустить настоящий while.
            return
        if nxt.code == CODE_IDENTIFIER:
            if _looks_like_keyword(nxt.lexeme, "while"):
                return
            after = self.peek_ahead(1)
            if after and after.code == CODE_COMPARE:
                self.syncstmt()
                return
            self.add_err(
                "Ожидался символ ';' в конце оператора перед следующим оператором",
                nxt.lexeme,
                nxt.line,
                nxt.start_pos,
                nxt.end_pos,
            )
            self.syncstmt()
            return
        if nxt.code == CODE_WHILE:
            return
        if nxt.code == CODE_COMPARE:
            self.add_err(
                "Ожидался символ ';' в конце оператора",
                nxt.lexeme,
                nxt.line,
                nxt.start_pos,
                nxt.end_pos,
            )
            self.syncstmt()
            return
        self.add_err(
            "Ожидался символ ';' в конце оператора",
            nxt.lexeme,
            nxt.line,
            nxt.start_pos,
            nxt.end_pos,
        )
        self.syncstmt()
        return

    def expr(self):
        self.term()
        while self.peek() and self.peek().code == CODE_ARITH:
            self.advance()
            self.term()

    def expr_after_assign(self):
        self.skip_nl()
        self.skip_lex_errors()
        t = self.peek()
        if t is None:
            self.err_here("Ожидалось значение выражения (идентификатор или число)")
            return
        if t.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.advance()
        else:
            self.add_err(
                "Ожидалось значение выражения (идентификатор или число)",
                t.lexeme,
                t.line,
                t.start_pos,
                t.end_pos,
            )
            self.sync_to(CODE_SEMICOLON, CODE_ARITH, CODE_RBRACE, CODE_WHILE)
            return
        while self.peek() and self.peek().code == CODE_ARITH:
            self.advance()
            self.term()

    def term(self):
        self.skip_nl()
        self.skip_lex_errors()
        t = self.peek()
        if t is None:
            self.err_here("Ожидалось выражение (идентификатор или число)")
            return
        if t.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.advance()
            return
        self.err_here("Ожидались идентификатор или целое число в выражении")
        self.sync_to(CODE_SEMICOLON, CODE_ARITH, CODE_RBRACE, CODE_WHILE)

    def logical_expr(self):
        self.skip_nl()
        if self._handle_leading_compare_like_condition():
            return
        self.skip_lex_errors()
        self.logical_or_chain()

        if self.peek() and self.peek().code == CODE_COMPARE:
            self.err_here("Ожидается логический оператор (and, or) или конец условия перед оператором сравнения")
            self.sync_to(CODE_SEMICOLON, CODE_RPAREN)
        elif self.peek() and self.peek().code == CODE_IDENTIFIER:
            self.err_here("Ожидается логический оператор (and, or) перед %s" % self.peek().lexeme)
            self.sync_to(CODE_SEMICOLON, CODE_RPAREN)
        elif self.peek() and self.peek().code == CODE_DIGIT:
            self.err_here(
                "Ожидается логический оператор (and, or) или конец условия «;» перед числом «%s»"
                % self.peek().lexeme
            )
            self.sync_to(CODE_SEMICOLON, CODE_RPAREN)
        elif self.peek() and self.peek().code == CODE_LPAREN:
            self.err_here(
                "После части условия нельзя ставить «(» без логического оператора."
            )
            self.advance()
            self.skip_nl()
            while self.peek() and self.peek().code == CODE_OR:
                self.advance()
                self.skip_nl()
                self.logical_and_chain()
        elif self.peek() and self.peek().code == CODE_RPAREN:
            self.err_here("Лишняя закрывающая скобка ')' в условии")
            self.sync_to(CODE_SEMICOLON)

    def logical_or_chain(self):
        self.skip_nl()
        self.logical_and_chain()
        while self.peek() and self.peek().code == CODE_OR:
            self.advance()
            self.skip_nl()
            self.logical_and_chain()

    def logical_and_chain(self):
        self.skip_nl()
        self.logical_term()
        while self.peek() and self.peek().code == CODE_AND:
            self.advance()
            self.skip_nl()
            self.logical_term()

    def logical_term(self):
        if self.take(CODE_NOT):
            self.logical_primary()
        else:
            self.logical_primary()

    def logical_primary(self):
        t0 = self.peek()
        if t0 and t0.code == CODE_LPAREN:
            open_paren = t0
            self.advance()
            self.skip_nl()
            self.logical_or_chain()
            self.skip_nl()
            if self.take(CODE_RPAREN):
                return
            nxt = self.peek()
            if nxt and nxt.code == CODE_SEMICOLON:
                self.add_err(
                    "Не хватает «)».",
                    open_paren.lexeme,
                    open_paren.line,
                    open_paren.start_pos,
                    open_paren.end_pos,
                )
                return
            self.expect(
                CODE_RPAREN,
                "Ожидалась закрывающая скобка ')'",
                CODE_SEMICOLON,
                CODE_RPAREN,
            )
            return
        if self.peek() and self.peek().code == CODE_RPAREN:
            self.err_here(
                "Лишняя «)» между частями условия"
            )
            while self.peek() and self.peek().code == CODE_RPAREN:
                self.advance()
            if self.peek() and self.peek().code == CODE_LPAREN:
                self.logical_primary()
                return
        self.comparison()

    def comparison(self):
        self.skip_nl()
        cond_start = self.pos
        t = self.peek()
        if t is None:
            self.err_here("Ожидалось условие (идентификатор)")
            return
        left_missing = False

        # Спец-случай: условие начинается с битого оператора сравнения (например <<<).
        # Тогда фиксируем обе ошибки: нет левого идентификатора и неверный оператор сравнения.
        if self._handle_leading_compare_like_condition():
            return

        self.skip_lex_errors()
        t = self.peek()
        if t is None:
            self.err_here("Ожидалось условие (идентификатор)")
            return
        if t.code != CODE_IDENTIFIER:
            left_missing = True
            self._add_condition_identifier_error(t)
            self.sync_to(CODE_COMPARE, CODE_SEMICOLON, CODE_RPAREN)
            if self.eof():
                return
        else:
            self.advance()

        self.skip_nl()
        self.skip_lex_errors()
        op = self.peek()
        if op is None:
            self.err_here("Ожидался оператор сравнения")
            return
        if op.code != CODE_COMPARE:
            if left_missing and op.code in (CODE_SEMICOLON, CODE_RPAREN):
                had_compare_like_error = False
                for k in range(cond_start, self.pos):
                    tk = self.tokens[k]
                    if (
                        tk.code == CODE_ERROR
                        and tk.lexeme
                        and all(ch in "<>=!" for ch in tk.lexeme)
                    ):
                        had_compare_like_error = True
                        break
                if had_compare_like_error:
                    return
                self.err_here("Ожидались идентификатор или целое число в условии")
                return
            self.err_here("Ожидался оператор сравнения (<, >, ==, ...)")
            self.sync_to(CODE_AND, CODE_OR, CODE_SEMICOLON, CODE_RPAREN)
            if self.peek() and self.peek().code in (
                CODE_AND,
                CODE_OR,
                CODE_SEMICOLON,
                CODE_RPAREN,
            ):
                return
        else:
            self.advance()

        self.skip_nl()
        self.skip_lex_errors()
        val = self.peek()
        if val is None:
            self.err_here("Ожидались идентификатор или целое число в условии")
        elif val.code not in (CODE_IDENTIFIER, CODE_DIGIT):
            if val.code == CODE_COMPARE and op and op.code == CODE_COMPARE:
                self.add_err(
                    f"Лишний повтор оператора сравнения '{val.lexeme}'",
                    val.lexeme,
                    val.line,
                    val.start_pos,
                    val.end_pos,
                )
                self.sync_to(CODE_SEMICOLON, CODE_RPAREN)
                return
            self.err_here("Ожидались идентификатор или целое число в условии")
            self.sync_to(CODE_SEMICOLON, CODE_RPAREN)
        else:
            self.advance()


def filter_tokens_for_parser(tokens):
    return [t for t in tokens if t.code != TOKEN_TYPES["WHITESPACE"][0]]


def collect_lexer_errors(tokens):
    err_code = TOKEN_TYPES["ERROR"][0]
    lexer_errors = []
    for token in tokens:
        if token.code == err_code:
            lexer_errors.append(
                ParseError(
                    token.lexeme,
                    token.line,
                    token.start_pos,
                    token.end_pos,
                    _lexer_message_for_token(token),
                )
            )
    return lexer_errors


def _overlaps(a, b):
    return not (a.end_pos < b.start_pos or b.end_pos < a.start_pos)


def _filter_parser_errors_near_lex(parser_errors, lexer_errors):
    if not lexer_errors:
        return parser_errors
    has_while_lex_error = any(
        "Ожидалось ключевое слово while (лексическая ошибка)" in lex.message
        for lex in lexer_errors
    )
    keep_near_lex = {
        "Ожидались идентификатор или целое число в условии",
        "Ожидался символ ';' в конце конструкции",
    }
    strong_followup_positions = {
        (e.line, e.start_pos, e.end_pos)
        for e in parser_errors
        if any(msg in e.message for msg in keep_near_lex)
    }
    filtered = []
    for err in parser_errors:
        if has_while_lex_error and "Ожидалось ключевое слово while" in err.message:
            continue
        suppress = False
        for lex in lexer_errors:
            if err.line != lex.line:
                continue
            if _overlaps(err, lex):
                # Для синтаксических ожиданий в текущем контексте
                # не затираем сообщение лексической ошибкой.
                if "Ожидался символ ';'" in err.message:
                    continue
                suppress = True
                break
            # Частый каскад: после битой лексемы парсер ругается на следующий токен.
            if err.start_pos <= lex.end_pos + 2 and err.start_pos >= lex.start_pos:
                if any(msg in err.message for msg in keep_near_lex):
                    # Эти ошибки не гасим: они показывают, что условие/конструкция
                    # не завершилась после лексической ошибки.
                    continue
                if (
                    "В условии ожидался идентификатор" in err.message
                    or "Ожидался идентификатор в условии" in err.message
                ):
                    # Если идентификатор уже сломан лексически (например numb@er),
                    # не дублируем синтаксическую ошибку про отсутствующий идентификатор.
                    if (
                        "Ожидался идентификатор (лексическая ошибка)" in lex.message
                    ):
                        suppress = True
                        break
                else:
                    suppress = True
                    break
        if not suppress:
            filtered.append(err)
    return filtered


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


def _collapse_errors_by_position(errors):
    priority_tokens = (
        "Ожидалось ключевое слово repeat",
        "Ожидалось ключевое слово while",
        "Ожидался символ ';'",
        "Ожидался символ",
        "Ожидался оператор",
        "В условии ожидался идентификатор",
        "лексическая ошибка",
    )

    def score(msg):
        s = 0
        for i, needle in enumerate(priority_tokens):
            if needle in msg:
                s = max(s, 100 - i)
        return s

    keep_together = {
        "Ожидался символ '}'",
        "Ожидалось ключевое слово while",
        "Ожидался символ ';' в конце конструкции",
        "Ожидался идентификатор (начало оператора присваивания)",
        "Ожидался оператор '=' или составной оператор (+=, -=, ...)",
        "Ожидалось значение выражения (идентификатор или число)",
        "В условии ожидался идентификатор",
        "Ожидались идентификатор или целое число в условии",
    }

    by_pos = {}
    order = {}
    for idx, err in enumerate(errors):
        key = (err.line, err.start_pos, err.end_pos)
        by_pos.setdefault(key, []).append((idx, err))
        order.setdefault(key, idx)

    out = []
    for key, items in sorted(order.items(), key=lambda kv: kv[1]):
        entries = by_pos[key]
        msgs = {e.message for _, e in entries}
        has_missing_construction_semicolon = any(
            "Ожидался символ ';' в конце конструкции" in e.message for _, e in entries
        )
        has_keyword_lex_error = any("лексическая ошибка" in e.message for _, e in entries)
        if has_missing_construction_semicolon and has_keyword_lex_error:
            seen = set()
            for _, err in sorted(entries, key=lambda p: p[0]):
                # Сохраняем обе диагностики в одной позиции:
                # лексическую (битое ключевое слово) и структурную (нет ';' в конце).
                if (
                    "Ожидался символ ';' в конце конструкции" not in err.message
                    and "лексическая ошибка" not in err.message
                ):
                    continue
                sig = (err.message, err.fragment)
                if sig in seen:
                    continue
                seen.add(sig)
                out.append(err)
            continue
        if msgs.issubset(keep_together) and len(msgs) > 1:
            seen = set()
            for _, err in sorted(entries, key=lambda p: p[0]):
                sig = (err.message, err.fragment)
                if sig in seen:
                    continue
                seen.add(sig)
                out.append(err)
            continue

        best = None
        for idx, err in entries:
            candidate = (score(err.message), -idx, err)
            if best is None or candidate > best:
                best = candidate
        out.append(best[2])
    # Важно: сохраняем исходный порядок ошибок для одной и той же позиции.
    # Нужна только геометрическая сортировка по месту, без лексикографической
    # перестановки текста сообщений.
    return sorted(out, key=lambda e: (e.line, e.start_pos, e.end_pos))


def _next_non_nl(tokens, i):
    j = i
    while j < len(tokens) and tokens[j].code == CODE_NEWLINE:
        j += 1
    return j


def _find_first(tokens, code, start=0):
    for i in range(start, len(tokens)):
        if tokens[i].code == code:
            return i
    return -1


def _build_err(msg, tok):
    return ParseError(tok.lexeme, tok.line, tok.start_pos, tok.end_pos, msg)


def _apply_special_cases(tokens, all_errors):
    if not tokens:
        return all_errors

    repeat_i = _find_first(tokens, CODE_REPEAT)
    while_i = _find_first(tokens, CODE_WHILE)

    # repeat [ ... ] while ...
    if repeat_i != -1 and while_i != -1:
        j = _next_non_nl(tokens, repeat_i + 1)
        if j < len(tokens) and tokens[j].code == CODE_ERROR and tokens[j].lexeme == "[":
            close = -1
            for k in range(j + 1, while_i):
                if tokens[k].code == CODE_ERROR and tokens[k].lexeme == "]":
                    close = k
                    break
            if close != -1:
                return [
                    _build_err("Ожидался символ '{' после repeat", tokens[j]),
                    _build_err("Ожидался символ '}' перед while", tokens[close]),
                ]

    # repeat ( ... ) while ...
    if repeat_i != -1 and while_i != -1:
        j = _next_non_nl(tokens, repeat_i + 1)
        if j < len(tokens) and tokens[j].code == CODE_LPAREN:
            close = -1
            for k in range(j + 1, while_i):
                if tokens[k].code == CODE_RPAREN:
                    close = k
                    break
            if close != -1:
                return [
                    _build_err("Ожидался символ '{' после repeat", tokens[j]),
                    _build_err("Ожидался символ '}' перед while", tokens[close]),
                ]

    # while ( );
    if while_i != -1:
        lp = _next_non_nl(tokens, while_i + 1)
        rp = _next_non_nl(tokens, lp + 1) if lp < len(tokens) else -1
        sc = _next_non_nl(tokens, rp + 1) if rp < len(tokens) else -1
        if (
            lp < len(tokens)
            and rp < len(tokens)
            and sc < len(tokens)
            and tokens[lp].code == CODE_LPAREN
            and tokens[rp].code == CODE_RPAREN
            and tokens[sc].code == CODE_SEMICOLON
        ):
            return [
                _build_err("В условии ожидался идентификатор", tokens[rp]),
                _build_err("Ожидался оператор сравнения (<, >, ==, ...)", tokens[rp]),
                _build_err("Ожидались идентификатор или целое число в условии", tokens[sc]),
            ]

    # while ; (and missing } before while)
    if while_i != -1:
        nxt = _next_non_nl(tokens, while_i + 1)
        has_rbrace_before_while = any(t.code == CODE_RBRACE for t in tokens[:while_i])
        if nxt < len(tokens) and tokens[nxt].code == CODE_SEMICOLON and not has_rbrace_before_while:
            return [
                _build_err("Ожидался символ '}'", tokens[while_i]),
                _build_err("В условии ожидался идентификатор", tokens[nxt]),
                _build_err("Ожидался оператор сравнения (<, >, ==, ...)", tokens[nxt]),
                _build_err("Ожидались идентификатор или целое число в условии", tokens[nxt]),
            ]

    # while (number < 5;);
    if while_i != -1:
        lp = _find_first(tokens, CODE_LPAREN, while_i + 1)
        rp = _find_first(tokens, CODE_RPAREN, while_i + 1)
        if lp != -1 and rp != -1 and lp < rp:
            semi_inside = -1
            for k in range(lp + 1, rp):
                if tokens[k].code == CODE_SEMICOLON:
                    semi_inside = k
                    break
            if semi_inside != -1:
                return [
                    _build_err(
                        "Лишний символ ';' в условии: перед ')' здесь не нужен ';'",
                        tokens[semi_inside],
                    )
                ]

    # while { ... };
    if while_i != -1:
        lb = _find_first(tokens, CODE_LBRACE, while_i + 1)
        rb = _find_first(tokens, CODE_RBRACE, while_i + 1)
        if lb != -1 and rb != -1 and lb < rb:
            return [
                _build_err("Символ '{' в условии не на своем месте", tokens[lb]),
                _build_err("Символ '}' в условии не на своем месте", tokens[rb]),
            ]

    return all_errors


def _ensure_missing_construction_semicolon(tokens, errors):
    has_repeat = any(t.code == CODE_REPEAT for t in tokens)
    has_while_lex_error = any(
        "Ожидалось ключевое слово while (лексическая ошибка)" in e.message for e in errors
    )
    already_has_construction_semicolon = any(
        "Ожидался символ ';' в конце конструкции" in e.message for e in errors
    )
    if not has_repeat or not has_while_lex_error or already_has_construction_semicolon:
        return errors

    last = None
    for t in reversed(tokens):
        if t.code in (CODE_NEWLINE, CODE_WHITESPACE):
            continue
        last = t
        break
    if last is None or last.code == CODE_SEMICOLON:
        return errors

    out = list(errors)
    out.append(
        ParseError(
            "",
            last.line,
            last.end_pos,
            last.end_pos,
            "Ожидался символ ';' в конце конструкции",
        )
    )
    return out


def analyze_syntax(tokens):
    lexer_errors = collect_lexer_errors(tokens)
    clean = filter_tokens_for_parser(tokens)
    result = Parser(clean).parse()
    parser_errors = _filter_parser_errors_near_lex(result.errors, lexer_errors)
    all_errors = _dedup_errors(lexer_errors + parser_errors)
    all_errors = _collapse_errors_by_position(all_errors)
    all_errors = _apply_special_cases(clean, all_errors)
    all_errors = _ensure_missing_construction_semicolon(clean, all_errors)
    all_errors = sorted(all_errors, key=lambda e: (e.line, e.start_pos, e.end_pos))
    return ParseResult(len(all_errors) == 0, all_errors)
