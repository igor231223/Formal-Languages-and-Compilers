from scanner import TOKEN_TYPES

CODE_REPEAT = 1
CODE_WHILE = 2
CODE_IDENTIFIER = 3
CODE_LBRACE = 5
CODE_COMPOUND_ASSIGN = 6
CODE_DIGIT = 7
CODE_RBRACE = 8
CODE_COMPARE = 9
CODE_SEMICOLON = 10
CODE_NEWLINE = 11
CODE_ARITH = 12
CODE_ASSIGN = 13


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
        self.repeat_while()
        if not self.eof():
            t = self.peek()
            self.add_err(
                "Лишние символы после завершения конструкции repeat-while",
                t.lexeme,
                t.line,
                t.start_pos,
                t.end_pos,
            )
            self.pos = len(self.tokens)
        return ParseResult(len(self.errors) == 0, list(self.errors))

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

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
            return

        if t.code == CODE_REPEAT:
            self.advance()
        else:
            self.err_here("Ожидалось ключевое слово repeat")
            if t.code != CODE_LBRACE:
                self.sync_to(CODE_LBRACE, CODE_RBRACE)
                if self.eof():
                    return

        if not self.expect(CODE_LBRACE, "Ожидался символ '{'", CODE_LBRACE, CODE_RBRACE, CODE_WHILE):
            return

        self.stmt_list()

        if not self.expect(CODE_RBRACE, "Ожидался символ '}'", CODE_RBRACE, CODE_WHILE):
            return

        if not self.expect(CODE_WHILE, "Ожидалось ключевое слово while", CODE_WHILE, CODE_SEMICOLON):
            return

        self.condition()

        self.expect(CODE_SEMICOLON, "Ожидался символ ';' в конце конструкции", CODE_SEMICOLON)

    def stmt_list(self):
        while not self.eof():
            self.skip_nl()
            t = self.peek()
            if t is None or t.code == CODE_RBRACE:
                return
            self.stmt()

    def stmt(self):
        t = self.peek()
        if t is None:
            self.err_here("Ожидался оператор в теле цикла")
            return
        if t.code != CODE_IDENTIFIER:
            self.err_here("Ожидался идентификатор (начало оператора присваивания)")
            self.syncstmt()
            return

        self.advance()
        op = self.peek()
        if op is None:
            self.add_err("Ожидался оператор присваивания", "EOF", t.line, t.end_pos, t.end_pos)
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
        self.expr()
        self.skip_nl()

        nxt = self.peek()
        if nxt is None:
            self.add_err("Ожидался символ ';' или конец строки перед '}'", "EOF", op.line, op.end_pos, op.end_pos)
            return
        if nxt.code == CODE_SEMICOLON:
            self.advance()
            return
        if nxt.code in (CODE_RBRACE, CODE_IDENTIFIER):
            return
        self.add_err(
            "Ожидался символ ';', перенос строки, начало следующего оператора или '}'",
            nxt.lexeme,
            nxt.line,
            nxt.start_pos,
            nxt.end_pos,
        )
        self.syncstmt()

    def expr(self):
        self.term()
        while self.peek() and self.peek().code == CODE_ARITH:
            self.advance()
            self.term()

    def term(self):
        t = self.peek()
        if t is None:
            self.err_here("Ожидалось выражение (идентификатор или число)")
            return
        if t.code in (CODE_IDENTIFIER, CODE_DIGIT):
            self.advance()
            return
        self.err_here("Ожидались идентификатор или целое число")
        self.sync_to(CODE_SEMICOLON, CODE_ARITH, CODE_RBRACE)

    def condition(self):
        t = self.peek()
        if t is None:
            self.err_here("Ожидалось условие (идентификатор)")
            return
        if t.code != CODE_IDENTIFIER:
            self.err_here("В условии ожидался идентификатор")
            self.sync_to(CODE_COMPARE, CODE_SEMICOLON)
            if self.eof():
                return
        else:
            self.advance()

        op = self.peek()
        if op is None:
            self.err_here("Ожидался оператор сравнения")
            return
        if op.code != CODE_COMPARE:
            self.err_here("Ожидался оператор сравнения (<, >, ==, ...)")
            self.sync_to(CODE_DIGIT, CODE_IDENTIFIER, CODE_SEMICOLON)
        else:
            self.advance()

        val = self.peek()
        if val is None:
            self.err_here("Ожидалось значение после оператора сравнения")
            return
        if val.code not in (CODE_IDENTIFIER, CODE_DIGIT):
            self.err_here("Ожидались идентификатор или целое число в условии")
            self.sync_to(CODE_SEMICOLON)
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
