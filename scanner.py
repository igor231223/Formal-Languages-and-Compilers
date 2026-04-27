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
                self.tokens.append(token)
        return self.tokens

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

        if char in "<>=!+-*/":
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
            while (
                not self.is_at_end()
                and self.peek().isascii()
                and self.peek().isalnum()
            ):
                lexeme += self.advance()

            # Обобщенно ловим "разорванные" идентификаторы:
            # rep{eat, nu==mber, nu<mber и подобные.
            if self._looks_like_broken_identifier_tail():
                while not self.is_at_end() and self.peek() not in " \n\t;":
                    lexeme += self.advance()
                code, type_name = TOKEN_TYPES["ERROR"]
                end_pos = start_pos + len(lexeme) - 1
                return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

            if not self.is_at_end() and not self.could_start_token(self.peek()):
                lexeme += self.advance()
                while not self.is_at_end() and self.peek().isalnum():
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
        while not self.is_at_end() and not self.could_start_token(self.peek()):
            lexeme += self.advance()
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
        if c in "+-*/":
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
        if self.peek() not in "<>=!+-*/{}[]()":
            return False
        i = self.pos
        saw_symbol = False
        while i < len(self.text) and self.text[i] in "<>=!+-*/{}[]()":
            saw_symbol = True
            i += 1
        if not saw_symbol or i >= len(self.text):
            return False
        return self.text[i].isalpha()

    def scan_operator_sequence(self, first_char, start_pos):
        lexeme = first_char
        while not self.is_at_end() and self.peek() in "<>=!+-*/":
            lexeme += self.advance()

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
        }

        token_type = valid_map.get(lexeme)
        end_pos = start_pos + len(lexeme) - 1
        if token_type is None:
            code, type_name = TOKEN_TYPES["ERROR"]
            return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

        code, type_name = TOKEN_TYPES[token_type]
        return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

    def scan_bracket_or_separator_sequence(self, first_char, start_pos):
        # Склеиваем длинные повторы одного и того же символа в ERROR-токен.
        # Исключение: ';' оставляем покомпонентно, чтобы парсер корректно
        # выдавал синтаксические ошибки о лишних/пропущенных ';'.
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