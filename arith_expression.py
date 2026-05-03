from __future__ import annotations

from dataclasses import dataclass, field

from parser import (
    CODE_ARITH,
    CODE_DIGIT,
    CODE_IDENTIFIER,
    CODE_LPAREN,
    CODE_NEWLINE,
    CODE_RPAREN,
    CODE_WHITESPACE,
    CODE_ERROR,
    ParseError,
)


_EXPR_CODES = frozenset(
    {
        CODE_DIGIT,
        CODE_IDENTIFIER,
        CODE_ARITH,
        CODE_LPAREN,
        CODE_RPAREN,
    }
)

_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2}


def _valid_identifier(lexeme: str) -> bool:
    if not lexeme or not lexeme[0].isalpha():
        return False
    for ch in lexeme[1:]:
        if ch == "_":
            continue
        if ch.isascii() and ch.isalnum():
            continue
        return False
    return True


@dataclass
class ExprIrResult:
    ok: bool
    errors: list = field(default_factory=list)
    quadruples: list[tuple[str, str, str, str]] = field(default_factory=list)
    rpn_tokens: list[str] = field(default_factory=list)
    rpn_string: str = ""
    rpn_value: int | None = None
    rpn_message: str = ""
    integers_only: bool = False


def _collect_preparse_errors(tokens) -> list[ParseError]:
    errs: list[ParseError] = []
    for t in tokens:
        if t.code in (CODE_WHITESPACE, CODE_NEWLINE):
            continue
        if t.code == CODE_ERROR:
            errs.append(
                ParseError(
                    t.lexeme or "",
                    t.line,
                    t.start_pos,
                    t.end_pos,
                    "Лексическая ошибка (недопустимая лексема)",
                )
            )
            continue
        if t.code not in _EXPR_CODES:
            errs.append(
                ParseError(
                    t.lexeme or "",
                    t.line,
                    t.start_pos,
                    t.end_pos,
                    "Символ не входит в алфавит арифметического выражения "
                    "(ожидаются целое число, идентификатор, + - * / % ( ) и пробелы)",
                )
            )
    return errs


def _significant_tokens(tokens):
    return [t for t in tokens if t.code not in (CODE_WHITESPACE, CODE_NEWLINE)]


def _chain_is_integers_only(tokens_sig) -> bool:
    for t in tokens_sig:
        if t.code == CODE_IDENTIFIER:
            return False
    return True


def _infix_to_rpn_shunting_yard(tokens_sig) -> list[str] | None:
    out: list[str] = []
    stack: list[str] = []
    for t in tokens_sig:
        if t.code == CODE_DIGIT:
            out.append(t.lexeme)
        elif t.code == CODE_ARITH:
            op = t.lexeme
            if op not in _PREC:
                return None
            while stack and stack[-1] != "(" and _PREC[stack[-1]] >= _PREC[op]:
                out.append(stack.pop())
            stack.append(op)
        elif t.code == CODE_LPAREN:
            stack.append("(")
        elif t.code == CODE_RPAREN:
            while stack and stack[-1] != "(":
                out.append(stack.pop())
            if stack and stack[-1] == "(":
                stack.pop()
            else:
                return None
        else:
            return None
    while stack:
        if stack[-1] == "(":
            return None
        out.append(stack.pop())
    return out


def _eval_rpn(rpn: list[str]) -> tuple[int | None, str]:
    st: list[int] = []
    for x in rpn:
        if x in _PREC:
            if len(st) < 2:
                return None, "Некорректное ПОЛИЗ (мало операндов)"
            b = st.pop()
            a = st.pop()
            if x == "+":
                st.append(a + b)
            elif x == "-":
                st.append(a - b)
            elif x == "*":
                st.append(a * b)
            elif x == "/":
                if b == 0:
                    return None, "Деление на ноль"
                st.append(a // b)
            elif x == "%":
                if b == 0:
                    return None, "Остаток от деления на ноль"
                st.append(a % b)
        else:
            try:
                st.append(int(x))
            except ValueError:
                return None, f"Ожидалось целое число в ПОЛИЗ: {x!r}"
    if len(st) != 1:
        return None, "Некорректное ПОЛИЗ"
    return st[0], ""


class _RecursiveDescentExprParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errors: list[ParseError] = []
        self.quads: list[tuple[str, str, str, str]] = []
        self._temp = 0

    def _new_temp(self) -> str:
        self._temp += 1
        return f"t{self._temp}"

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self):
        t = self.peek()
        if t is not None:
            self.pos += 1
        return t

    def _err(self, msg: str, t):
        if t is None:
            prev = self.tokens[self.pos - 1] if self.pos > 0 else None
            if prev is None:
                self.errors.append(ParseError("", 1, 0, 0, msg))
            else:
                self.errors.append(
                    ParseError("", prev.line, prev.end_pos, prev.end_pos, msg)
                )
        else:
            self.errors.append(
                ParseError(
                    t.lexeme or "",
                    t.line,
                    t.start_pos,
                    t.end_pos,
                    msg,
                )
            )

    def parse(self) -> str | None:
        v = self._parse_e()
        t = self.peek()
        if t is not None:
            if t.code == CODE_RPAREN:
                self._err("Лишняя закрывающая скобка «)»", t)
            else:
                self._err(f"Лишняя лексема после конца выражения: «{t.lexeme}»", t)
        return v

    def _parse_e(self) -> str | None:
        left = self._parse_t()
        if left is None:
            return None
        return self._parse_a(left)

    def _parse_a(self, left: str) -> str | None:
        while True:
            t = self.peek()
            if t is None or t.code != CODE_ARITH or t.lexeme not in ("+", "-"):
                return left
            op_t = t
            op = t.lexeme
            self.advance()
            right = self._parse_t()
            if right is None:
                self._err("Пропущен операнд после «+» или «-»", op_t)
                return left
            tmp = self._new_temp()
            self.quads.append((op, left, right, tmp))
            left = tmp

    def _parse_t(self) -> str | None:
        left = self._parse_f()
        if left is None:
            return None
        return self._parse_b(left)

    def _parse_b(self, left: str) -> str | None:
        while True:
            t = self.peek()
            if t is None or t.code != CODE_ARITH or t.lexeme not in ("*", "/", "%"):
                return left
            op_t = t
            op = t.lexeme
            self.advance()
            right = self._parse_f()
            if right is None:
                self._err("Пропущен операнд после «*», «/» или «%»", op_t)
                return left
            tmp = self._new_temp()
            self.quads.append((op, left, right, tmp))
            left = tmp

    def _parse_f(self) -> str | None:
        t = self.peek()
        if t is None:
            self._err("Ожидался операнд (число, идентификатор или «(»)", None)
            return None

        if t.code == CODE_DIGIT:
            self.advance()
            return t.lexeme

        if t.code == CODE_IDENTIFIER:
            if not _valid_identifier(t.lexeme):
                self._err(
                    "Некорректный идентификатор (буква, затем буквы, цифры, _)",
                    t,
                )
            self.advance()
            return t.lexeme

        if t.code == CODE_LPAREN:
            self.advance()
            inner = self._parse_e()
            rp = self.peek()
            if rp is None or rp.code != CODE_RPAREN:
                self._err("Ожидалась закрывающая скобка «)»", rp if rp else None)
            else:
                self.advance()
            return inner

        if t.code == CODE_ARITH:
            self._err("Пропущен операнд перед оператором", t)
            return None

        if t.code == CODE_RPAREN:
            self._err("Лишняя закрывающая скобка «)» или пропущен операнд", t)
            self.advance()
            return None

        self._err("Недопустимый символ в позиции операнда", t)
        self.advance()
        return None


def analyze_arith_expression(tokens) -> ExprIrResult:
    pre = _collect_preparse_errors(tokens)
    if pre:
        return ExprIrResult(ok=False, errors=pre)

    sig = _significant_tokens(tokens)
    if not sig:
        return ExprIrResult(
            ok=False,
            errors=[
                ParseError("", 1, 0, 0, "Пустое выражение (нет значимых лексем)")
            ],
        )

    p = _RecursiveDescentExprParser(sig)
    p.parse()
    errs = list(p.errors)
    quads = list(p.quads)
    if errs:
        return ExprIrResult(ok=False, errors=errs, quadruples=[])

    ints_only = _chain_is_integers_only(sig)
    rpn: list[str] = []
    rpn_val: int | None = None
    rpn_msg = ""
    rpn_str = ""

    if ints_only:
        rpn = _infix_to_rpn_shunting_yard(sig) or []
        if not rpn:
            rpn_msg = "Не удалось построить ПОЛИЗ"
        else:
            rpn_str = " ".join(rpn)
            rpn_val, em = _eval_rpn(rpn)
            if em:
                rpn_msg = em
                rpn_val = None
    else:
        rpn_msg = (
            "ПОЛИЗ и численное значение не строятся: в выражении есть идентификаторы "
        )

    return ExprIrResult(
        ok=True,
        errors=[],
        quadruples=quads,
        rpn_tokens=rpn,
        rpn_string=rpn_str,
        rpn_value=rpn_val,
        rpn_message=rpn_msg,
        integers_only=ints_only,
    )
