TOKEN_TYPES = {
    "REPEAT": (1, "Ключевое слово"),
    "WHILE": (2, "Ключевое слово"),
    "IDENTIFIER": (3, "Идентификатор"),
    "WHITESPACE": (4, "Разделитель (пробел)"),
    "LBRACE": (5, "Начало блока"),
    "COMPOUND_ASSIGNMENT_OPERATOR": (6, "Составной оператор присваивания"),
    "DIGIT_NUMBER": (7, "Целое число"),
    "RBRACE": (8, "Конец блока"),
    "OPERATOR_COMPARE": (9, "Оператор сравнения"),
    "SEMICOLON": (10, "Конец оператора"),
    "NEWLINE": (11, "Разделитель (перенос строки)"),
    "ARITHMETIC_OPERATOR": (12, "Арифметический оператор"),
    "ASSIGNMENT_OPERATOR": (13, "Оператор присваивания"),
    "AND": (14, "Логический оператор"),
    "OR": (15, "Логический оператор"),
    "NOT": (16, "Логический оператор"),
    "LPAREN": (17, "Скобка '('"),
    "RPAREN": (18, "Скобка ')'"),
    "ERROR": (100, "Ошибка (недопустимый символ)")
}


class Token:
    def __init__(self, code, type_name, lexeme, line, start_pos, end_pos):
        self.code = code
        self.type_name = type_name
        self.lexeme = lexeme
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos

    def __repr__(self):
        return f"{self.code} | {self.type_name} | {self.lexeme} | строка {self.line}, {self.start_pos}-{self.end_pos}"


class Scanner:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.line = 1
        self.line_start = 0
        self.tokens = []

    def scan_tokens(self):
        while not self.is_at_end():
            token = self.scan_token()
            if token:
                self.tokens.extend(self._split_edge_noise_error_token(token))
        return self.tokens

    def _split_edge_noise_error_token(self, token):
        if token.code != TOKEN_TYPES["ERROR"][0]:
            return [token]

        lex = token.lexeme or ""
        if len(lex) <= 1 or not any(ch.isalpha() for ch in lex):
            return [token]

        lead_len = 0
        i = 0
        while i < len(lex) and not lex[i].isalnum():
            lead_len += 1
            i += 1

        tail_len = 0
        j = len(lex) - 1
        while j >= 0 and not lex[j].isalnum():
            tail_len += 1
            j -= 1

        if lead_len + tail_len >= len(lex):
            return [token]
        if lead_len == 0 and tail_len == 0:
            return [token]

        core_start_idx = lead_len
        core_end_idx = len(lex) - tail_len
        core = lex[core_start_idx:core_end_idx]
        if not core:
            return [token]

        out = []
        if lead_len > 0:
            lead = lex[:lead_len]
            out.append(
                Token(
                    TOKEN_TYPES["ERROR"][0],
                    TOKEN_TYPES["ERROR"][1],
                    lead,
                    token.line,
                    token.start_pos,
                    token.start_pos + lead_len - 1,
                )
            )

        core_start_pos = token.start_pos + lead_len
        core_end_pos = core_start_pos + len(core) - 1
        out.append(self._build_core_token_from_error(core, token.line, core_start_pos, core_end_pos))

        if tail_len > 0:
            tail = lex[-tail_len:]
            out.append(
                Token(
                    TOKEN_TYPES["ERROR"][0],
                    TOKEN_TYPES["ERROR"][1],
                    tail,
                    token.line,
                    core_end_pos + 1,
                    token.end_pos,
                )
            )
        return out

    def _build_core_token_from_error(self, core, line, start_pos, end_pos):
        if core == "repeat":
            code, type_name = TOKEN_TYPES["REPEAT"]
            return Token(code, type_name, core, line, start_pos, end_pos)
        if core == "while":
            code, type_name = TOKEN_TYPES["WHILE"]
            return Token(code, type_name, core, line, start_pos, end_pos)
        if core == "and":
            code, type_name = TOKEN_TYPES["AND"]
            return Token(code, type_name, core, line, start_pos, end_pos)
        if core == "or":
            code, type_name = TOKEN_TYPES["OR"]
            return Token(code, type_name, core, line, start_pos, end_pos)
        if core == "not":
            code, type_name = TOKEN_TYPES["NOT"]
            return Token(code, type_name, core, line, start_pos, end_pos)
        if core.isdigit():
            code, type_name = TOKEN_TYPES["DIGIT_NUMBER"]
            return Token(code, type_name, core, line, start_pos, end_pos)
        if core and core[0].isalpha() and core.isascii() and core.replace("_", "").isalnum():
            code, type_name = TOKEN_TYPES["IDENTIFIER"]
            return Token(code, type_name, core, line, start_pos, end_pos)
        code, type_name = TOKEN_TYPES["ERROR"]
        return Token(code, type_name, core, line, start_pos, end_pos)

    def scan_token(self):
        char = self.advance()
        start_pos = self.pos - self.line_start

        if char == ' ':
            code, type_name = TOKEN_TYPES["WHITESPACE"]
            return Token(code, type_name, "(пробел)", self.line, start_pos, start_pos)

        if char == '\t':
            code, type_name = TOKEN_TYPES["WHITESPACE"]
            return Token(code, type_name, "(пробел)", self.line, start_pos, start_pos)

        if char == '\n':
            code, type_name = TOKEN_TYPES["NEWLINE"]
            token = Token(code, type_name, "\\n", self.line, start_pos, start_pos)
            self.line += 1
            self.line_start = self.pos
            return token

        if char in "{};()[]":
            return self.scan_bracket_or_separator_sequence(char, start_pos)

        if char in "<>=!+-*/%":
            return self.scan_operator_sequence(char, start_pos)

        if char.isdigit():
            lexeme = char
            while not self.is_at_end() and self.peek().isdigit():
                lexeme += self.advance()
            if not self.is_at_end() and self.peek() == '.':
                lexeme += self.advance()
                while not self.is_at_end() and self.peek().isdigit():
                    lexeme += self.advance()
                code, type_name = TOKEN_TYPES["ERROR"]
                end_pos = start_pos + len(lexeme) - 1
                return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

            code, type_name = TOKEN_TYPES["DIGIT_NUMBER"]
            end_pos = start_pos + len(lexeme) - 1
            return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

        if char.isalpha():
            lexeme = char
            while not self.is_at_end():
                nx = self.peek()
                if nx == "_" or (nx.isascii() and nx.isalnum()):
                    lexeme += self.advance()
                else:
                    break

            if self._looks_like_broken_identifier_tail():
                while not self.is_at_end() and self.peek() not in " \n\t;":
                    lexeme += self.advance()
                code, type_name = TOKEN_TYPES["ERROR"]
                end_pos = start_pos + len(lexeme) - 1
                return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

            if not self.is_at_end() and not self.could_start_token(self.peek()):
                lexeme += self.advance()
                while (
                    not self.is_at_end()
                    and self.peek() not in " \n\t{};()[]<>!=+-*/%"
                ):
                    lexeme += self.advance()
                code, type_name = TOKEN_TYPES["ERROR"]
                end_pos = start_pos + len(lexeme) - 1
                return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

            if lexeme == "repeat":
                code, type_name = TOKEN_TYPES["REPEAT"]
            elif lexeme == "while":
                code, type_name = TOKEN_TYPES["WHILE"]
            elif lexeme == "and":
                code, type_name = TOKEN_TYPES["AND"]
            elif lexeme == "or":
                code, type_name = TOKEN_TYPES["OR"]
            elif lexeme == "not":
                code, type_name = TOKEN_TYPES["NOT"]
            else:
                code, type_name = TOKEN_TYPES["IDENTIFIER"]

            end_pos = start_pos + len(lexeme) - 1
            return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

        lexeme = char
        code, type_name = TOKEN_TYPES["ERROR"]
        end_pos = start_pos + len(lexeme) - 1
        return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

    def could_start_token(self, c):
        if c == "\0":
            return False
        if c in " \n\t":
            return True
        if c in "{};()":
            return True
        if c in "<>=":
            return True
        if c == "!":
            return True
        if c in "+-*/%":
            return True
        if c == "_":
            return True
        if c.isdigit():
            return True
        if c.isalpha():
            return True
        return False

    def peek_n(self, offset):
        i = self.pos + offset
        if i >= len(self.text):
            return '\0'
        return self.text[i]

    def _looks_like_broken_identifier_tail(self):
        if self.is_at_end():
            return False
        if self.peek() not in "<>=!+-*/%{}[]()":
            return False
        i = self.pos
        saw_symbol = False
        only_arithmetic = True
        while i < len(self.text) and self.text[i] in "<>=!+-*/%{}[]()":
            saw_symbol = True
            c = self.text[i]
            if c not in "+-*/%":
                only_arithmetic = False
            i += 1
        if not saw_symbol or i >= len(self.text):
            return False
        if not self.text[i].isalpha():
            return False
        if only_arithmetic:
            return False
        return True

    def scan_operator_sequence(self, first_char, start_pos):
        lexeme = first_char
        while not self.is_at_end() and self.peek() in "<>=!+-*/%":
            lexeme += self.advance()
        if not self.is_at_end():
            nxt = self.peek()
            if nxt not in " \n\t{};()[]" and not (
                nxt.isdigit() or nxt.isalpha() or nxt == "_"
            ):
                while not self.is_at_end() and self.peek() not in " \n\t{};()[]":
                    lexeme += self.advance()
                code, type_name = TOKEN_TYPES["ERROR"]
                end_pos = start_pos + len(lexeme) - 1
                return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

        valid_map = {
            "<": "OPERATOR_COMPARE",
            ">": "OPERATOR_COMPARE",
            "<=": "OPERATOR_COMPARE",
            ">=": "OPERATOR_COMPARE",
            "==": "OPERATOR_COMPARE",
            "!=": "OPERATOR_COMPARE",
            "=": "ASSIGNMENT_OPERATOR",
            "+=": "COMPOUND_ASSIGNMENT_OPERATOR",
            "-=": "COMPOUND_ASSIGNMENT_OPERATOR",
            "*=": "COMPOUND_ASSIGNMENT_OPERATOR",
            "/=": "COMPOUND_ASSIGNMENT_OPERATOR",
            "+": "ARITHMETIC_OPERATOR",
            "-": "ARITHMETIC_OPERATOR",
            "*": "ARITHMETIC_OPERATOR",
            "/": "ARITHMETIC_OPERATOR",
            "%": "ARITHMETIC_OPERATOR",
        }

        token_type = valid_map.get(lexeme)
        end_pos = start_pos + len(lexeme) - 1
        if token_type is None:
            code, type_name = TOKEN_TYPES["ERROR"]
            return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

        code, type_name = TOKEN_TYPES[token_type]
        return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

    def scan_bracket_or_separator_sequence(self, first_char, start_pos):
        if first_char == ";":
            code, type_name = TOKEN_TYPES["SEMICOLON"]
            return Token(code, type_name, first_char, self.line, start_pos, start_pos)

        lexeme = first_char
        while not self.is_at_end() and self.peek() == first_char:
            lexeme += self.advance()

        end_pos = start_pos + len(lexeme) - 1
        if len(lexeme) > 1:
            code, type_name = TOKEN_TYPES["ERROR"]
            return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

        valid_single = {
            "{": "LBRACE",
            "}": "RBRACE",
            ";": "SEMICOLON",
            "(": "LPAREN",
            ")": "RPAREN",
        }
        token_type = valid_single.get(first_char)
        if token_type is None:
            code, type_name = TOKEN_TYPES["ERROR"]
            return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

        code, type_name = TOKEN_TYPES[token_type]
        return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

    def advance(self):
        char = self.text[self.pos]
        self.pos += 1
        return char

    def peek(self):
        if self.is_at_end():
            return '\0'
        return self.text[self.pos]

    def match(self, expected):
        if self.is_at_end():
            return False
        if self.text[self.pos] != expected:
            return False
        self.pos += 1
        return True

    def is_at_end(self):
        return self.pos >= len(self.text)