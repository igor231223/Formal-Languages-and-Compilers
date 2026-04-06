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
    "LPAREN": (17, "Открывающая скобка"),
    "RPAREN": (18, "Закрывающая скобка"),
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

        # пробел
        if char == ' ':
            code, type_name = TOKEN_TYPES["WHITESPACE"]
            return Token(code, type_name, "(пробел)", self.line, start_pos, start_pos)

        # перенос строки
        if char == '\n':
            code, type_name = TOKEN_TYPES["NEWLINE"]
            token = Token(code, type_name, "\\n", self.line, start_pos, start_pos)
            self.line += 1
            self.line_start = self.pos
            return token

        # блоки
        if char == '{':
            code, type_name = TOKEN_TYPES["LBRACE"]
            return Token(code, type_name, char, self.line, start_pos, start_pos)

        if char == '}':
            code, type_name = TOKEN_TYPES["RBRACE"]
            return Token(code, type_name, char, self.line, start_pos, start_pos)

        # конец строки
        if char == ';':
            code, type_name = TOKEN_TYPES["SEMICOLON"]
            return Token(code, type_name, char, self.line, start_pos, start_pos)

        # операторы сравнения
        if char in ['<', '>']:
            if self.match('='):
                lexeme = char + '='
                code, type_name = TOKEN_TYPES["OPERATOR_COMPARE"]
                return Token(code, type_name, lexeme, self.line, start_pos, start_pos + 1)
            else:
                code, type_name = TOKEN_TYPES["OPERATOR_COMPARE"]
                return Token(code, type_name, char, self.line, start_pos, start_pos)
            
        # оператор присваивания и сравнения
        if char == '=':
            if self.match('='):
                code, type_name = TOKEN_TYPES["OPERATOR_COMPARE"]
                return Token(code, type_name, "==", self.line, start_pos, start_pos + 1)
            else:
                code, type_name = TOKEN_TYPES["ASSIGNMENT_OPERATOR"]
                return Token(code, type_name, char, self.line, start_pos, start_pos)

        # оператор неравенства
        if char == '!':
            if self.match('='):
                code, type_name = TOKEN_TYPES["OPERATOR_COMPARE"]
                return Token(code, type_name, "!=", self.line, start_pos, start_pos + 1)
            else:
                code, type_name = TOKEN_TYPES["ERROR"]
                return Token(code, type_name, char, self.line, start_pos, start_pos)

        # операторы и составные операторы присваивания
        if char in ['+', '-', '*', '/']:
            if self.match('='):
                lexeme = char + '='
                code, type_name = TOKEN_TYPES["COMPOUND_ASSIGNMENT_OPERATOR"]
                return Token(code, type_name, lexeme, self.line, start_pos, start_pos + 1)
            else:
                code, type_name = TOKEN_TYPES["ARITHMETIC_OPERATOR"]
                return Token(code, type_name, char, self.line, start_pos, start_pos)


        # числа
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

        # идентификаторы
        if char.isalpha():
            lexeme = char
            while not self.is_at_end() and self.peek().isalnum():
                lexeme += self.advance()

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

        if char == '(':
            code, type_name = TOKEN_TYPES["LPAREN"]
            return Token(code, type_name, char, self.line, start_pos, start_pos)

        if char == ')':
            code, type_name = TOKEN_TYPES["RPAREN"]
            return Token(code, type_name, char, self.line, start_pos, start_pos)

        lexeme = char
        while not self.is_at_end() and not self.could_start_token(self.peek()):
            lexeme += self.advance()
        code, type_name = TOKEN_TYPES["ERROR"]
        end_pos = start_pos + len(lexeme) - 1
        return Token(code, type_name, lexeme, self.line, start_pos, end_pos)

    def could_start_token(self, c):
        if c == "\0":
            return False
        if c in " \n":
            return True
        if c in "{}();":
            return True
        if c in "<>=":
            return True
        if c in "+-*/":
            return True
        if c.isdigit():
            return True
        if c.isalpha():
            return True
        return False

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