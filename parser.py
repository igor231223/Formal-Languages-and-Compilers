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


class Parser:
    def __init__(self, tokens):
        self.tokens = list(tokens)
        self.pos = 0
        self.errors = []

    def parse(self):
        self.skip_nl()
        ok = self.repeat_while()
        self.skip_nl()
        if ok and not self.eof():
            t = self.peek()
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
            if t.code not in (CODE_NEWLINE, CODE_WHITESPACE):
                return t
            i += 1
        return None

    def advance(self):
        if self.pos < len(self.tokens):
            self.pos += 1

    def eof(self):
        return self.pos >= len(self.tokens)

    def skip_nl(self):
        while not self.eof() and self.tokens[self.pos].code == CODE_NEWLINE:
            self.pos += 1

    def take(self, code):
        t = self.peek()
        if t and t.code == code:
            self.pos += 1
            return True
        return False

    def add_err(self, msg, frag, line, s, e):
        self.errors.append(ParseError(frag, line, s, e, msg))

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

    def sync_to(self, *codes):
        while not self.eof() and self.tokens[self.pos].code not in codes:
            self.pos += 1

    def syncstmt(self):
        while not self.eof():
            c = self.tokens[self.pos].code
            if c == CODE_RBRACE:
                return
            if c == CODE_SEMICOLON:
                self.pos += 1
                return
            self.pos += 1

    def expect(self, code, msg, *sync):
        if self.take(code):
            return True
        self.err_here(msg)
        if sync:
            self.sync_to(*sync)
        if self.take(code):
            return True
        return False

    def repeat_while(self):
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
            if got_repeat:
                while self.peek():
                    c = self.peek().code
                    if c == CODE_RBRACE:
                        t = self.peek()
                        self.add_err(
                            "Символ '}' здесь недопустим: перед телом цикла должна быть '{'",
                            t.lexeme,
                            t.line,
                            t.start_pos,
                            t.end_pos,
                        )
                        self.advance()
                        continue
                    if c == CODE_SEMICOLON:
                        t = self.peek()
                        self.add_err(
                            "Символ ';' здесь недопустим: после «repeat» ожидается '{' перед телом цикла",
                            t.lexeme,
                            t.line,
                            t.start_pos,
                            t.end_pos,
                        )
                        self.advance()
                        continue
                    if c == CODE_WHILE:
                        nxt = self.first_non_nl_from_index(self.pos + 1)
                        if nxt and nxt.code in (
                            CODE_RBRACE,
                            CODE_LBRACE,
                            CODE_WHILE,
                            CODE_IDENTIFIER,
                        ):
                            t = self.peek()
                            self.add_err(
                                "Ключевое слово while здесь лишнее: после «repeat» ожидается '{' перед телом цикла",
                                t.lexeme,
                                t.line,
                                t.start_pos,
                                t.end_pos,
                            )
                            self.advance()
                            continue
                    if c == CODE_REPEAT:
                        t = self.peek()
                        self.add_err(
                            "Лишнее ключевое слово repeat: перед телом цикла достаточно одного repeat и символа '{'",
                            t.lexeme,
                            t.line,
                            t.start_pos,
                            t.end_pos,
                        )
                        self.advance()
                        continue
                    if c == CODE_IDENTIFIER:
                        nxt = self.first_non_nl_from_index(self.pos + 1)
                        if nxt and nxt.code == CODE_LBRACE:
                            t = self.peek()
                            self.add_err(
                                "Лишний идентификатор перед '{': после repeat должна следовать только '{'",
                                t.lexeme,
                                t.line,
                                t.start_pos,
                                t.end_pos,
                            )
                            self.advance()
                            continue
                        if nxt and nxt.code == CODE_IDENTIFIER:
                            t = self.peek()
                            self.add_err(
                                "Лишний идентификатор перед телом цикла (ожидалась '{' после repeat)",
                                t.lexeme,
                                t.line,
                                t.start_pos,
                                t.end_pos,
                            )
                            self.advance()
                            continue
                    if c == CODE_DIGIT:
                        nxt = self.first_non_nl_from_index(self.pos + 1)
                        if nxt and nxt.code == CODE_LBRACE:
                            t = self.peek()
                            self.add_err(
                                "Лишний числовой литерал перед '{': после «repeat» должна следовать только '{'",
                                t.lexeme,
                                t.line,
                                t.start_pos,
                                t.end_pos,
                            )
                            self.advance()
                            continue
                    break
                self.skip_nl()
                if not self.take(CODE_LBRACE):
                    self.err_here("Ожидался символ '{'")
            else:
                while self.peek():
                    c = self.peek().code
                    if c == CODE_RBRACE:
                        t = self.peek()
                        self.add_err(
                            "Символ '}' здесь недопустим: перед телом цикла должна быть '{'",
                            t.lexeme,
                            t.line,
                            t.start_pos,
                            t.end_pos,
                        )
                        self.advance()
                        continue
                    if c == CODE_SEMICOLON:
                        t = self.peek()
                        self.add_err(
                            "Символ ';' здесь недопустим: перед телом цикла ожидается '{'",
                            t.lexeme,
                            t.line,
                            t.start_pos,
                            t.end_pos,
                        )
                        self.advance()
                        continue
                    if c == CODE_WHILE:
                        nxt = self.first_non_nl_from_index(self.pos + 1)
                        if nxt and nxt.code in (
                            CODE_RBRACE,
                            CODE_LBRACE,
                            CODE_WHILE,
                            CODE_IDENTIFIER,
                        ):
                            t = self.peek()
                            self.add_err(
                                "Ключевое слово while здесь лишнее: после «repeat» ожидается '{' перед телом цикла",
                                t.lexeme,
                                t.line,
                                t.start_pos,
                                t.end_pos,
                            )
                            self.advance()
                            continue
                    if c == CODE_REPEAT:
                        t = self.peek()
                        self.add_err(
                            "Лишнее ключевое слово repeat: перед телом цикла достаточно одного repeat и символа '{'",
                            t.lexeme,
                            t.line,
                            t.start_pos,
                            t.end_pos,
                        )
                        self.advance()
                        continue
                    if c == CODE_IDENTIFIER:
                        nxt = self.first_non_nl_from_index(self.pos + 1)
                        if nxt and nxt.code == CODE_LBRACE:
                            self.advance()
                            continue
                        if nxt and nxt.code == CODE_IDENTIFIER:
                            break
                        break
                    if c == CODE_DIGIT:
                        nxt = self.first_non_nl_from_index(self.pos + 1)
                        if nxt and nxt.code == CODE_LBRACE:
                            self.advance()
                            continue
                        break
                    break
                self.skip_nl()
                if not self.take(CODE_LBRACE):
                    self.err_here("Ожидался символ '{'")

        self.stmt_list()

        self.skip_nl()
        self.expect(CODE_RBRACE, "Ожидался символ '}'", CODE_WHILE)

        self.skip_nl()
        while self.peek() and self.peek().code == CODE_RBRACE:
            nxt = self.first_non_nl_from_index(self.pos + 1)
            if nxt is None:
                break
            t = self.peek()
            if nxt.code == CODE_WHILE:
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
        if not self.expect(CODE_WHILE, "Ожидалось ключевое слово while"):
            self.skip_nl()
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
        self.logical_expr()

        self.skip_nl()
        self.expect(CODE_SEMICOLON, "Ожидался символ ';' в конце конструкции")

        return True

    def stmt_list(self):
        while not self.eof() and self.peek().code not in (CODE_RBRACE, CODE_WHILE):
            self.skip_nl()
            t = self.peek()
            if t is None or t.code == CODE_RBRACE or t.code == CODE_WHILE:
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
            return
        if nxt.code == CODE_IDENTIFIER:
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
        t = self.peek()
        if t is None:
            self.err_here("Ожидалось условие (идентификатор)")
            return
        if t.code != CODE_IDENTIFIER:
            self.err_here("В условии ожидался идентификатор")
            self.sync_to(CODE_COMPARE, CODE_SEMICOLON, CODE_RPAREN)
            if self.eof():
                return
        else:
            self.advance()

        self.skip_nl()
        op = self.peek()
        if op is None:
            self.err_here("Ожидался оператор сравнения")
            return
        if op.code != CODE_COMPARE:
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
        val = self.peek()
        if val is None:
            self.err_here("Ожидались идентификатор или целое число в условии")
        elif val.code not in (CODE_IDENTIFIER, CODE_DIGIT):
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
                    "Недопустимая лексема (лексическая ошибка)",
                )
            )
    return lexer_errors


def analyze_syntax(tokens):
    lexer_errors = collect_lexer_errors(tokens)
    err_code = TOKEN_TYPES["ERROR"][0]
    clean = [t for t in filter_tokens_for_parser(tokens) if t.code != err_code]
    result = Parser(clean).parse()
    all_errors = lexer_errors + result.errors
    return ParseResult(len(all_errors) == 0, all_errors)
