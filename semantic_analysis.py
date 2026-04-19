from __future__ import annotations

import json

from parser import (
    CODE_AND,
    CODE_ARITH,
    CODE_ASSIGN,
    CODE_COMPARE,
    CODE_COMPOUND_ASSIGN,
    CODE_DIGIT,
    CODE_IDENTIFIER,
    CODE_LPAREN,
    CODE_NEWLINE,
    CODE_NOT,
    CODE_OR,
    CODE_RPAREN,
    CODE_SEMICOLON,
    analyze_syntax,
    filter_tokens_for_parser,
)
from scanner import TOKEN_TYPES


INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1


class SemanticError:
    def __init__(self, message, line, start_pos, end_pos, fragment=""):
        self.message = message
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.fragment = fragment


class SemanticResult:
    def __init__(self, syntax_ok, syntax_errors, semantic_errors, ast_root, ast_tree_text, ast_json_text):
        self.syntax_ok = syntax_ok
        self.syntax_errors = syntax_errors
        self.semantic_errors = semantic_errors
        self.ast_root = ast_root
        self.ast_tree_text = ast_tree_text
        self.ast_json_text = ast_json_text


class AstNode:
    node_type = "AstNode"


class IntLiteralNode(AstNode):
    node_type = "IntLiteralNode"

    def __init__(self, value, token):
        self.value = value
        self.token = token


class IdentifierNode(AstNode):
    node_type = "IdentifierNode"

    def __init__(self, name, token):
        self.name = name
        self.token = token


class IntNode(AstNode):
    node_type = "IntNode"

    def __init__(self):
        pass


class BinaryOpNode(AstNode):
    node_type = "BinaryOpNode"

    def __init__(self, operator, left, right=None):
        self.operator = operator
        self.left = left
        self.right = right


class ComparisonNode(AstNode):
    node_type = "ComparisonNode"

    def __init__(self, left, operator, right=None):
        self.left = left
        self.operator = operator
        self.right = right


class LogicalAndNode(AstNode):
    node_type = "LogicalAndNode"

    def __init__(self, left, right):
        self.left = left
        self.right = right


class LogicalOrNode(AstNode):
    node_type = "LogicalOrNode"

    def __init__(self, left, right):
        self.left = left
        self.right = right


class NotNode(AstNode):
    node_type = "NotNode"

    def __init__(self, child):
        self.child = child


class AssignStmtNode(AstNode):
    node_type = "AssignStmtNode"

    def __init__(self, name, name_token, operator, value_type, value):
        self.name = name
        self.name_token = name_token
        self.operator = operator
        self.value_type = value_type
        self.value = value


class RepeatWhileNode(AstNode):
    node_type = "RepeatWhileNode"

    def __init__(self, body, condition):
        self.body = body
        self.condition = condition


class ProgramNode(AstNode):
    node_type = "Program"

    def __init__(self, declarations, repeat_while):
        self.declarations = declarations
        self.repeat_while = repeat_while


class SymbolTable:
    def __init__(self):
        self._symbols = {}

    def declare(self, name, typ, decl_line):
        self._symbols[name] = {"type": typ, "line": decl_line}

    def lookup(self, name):
        return self._symbols.get(name)

    def is_declared(self, name):
        return name in self._symbols


class _BodyAstParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def skip_nl(self):
        while self.pos < len(self.tokens) and self.tokens[self.pos].code == CODE_NEWLINE:
            self.pos += 1

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def parse_all(self):
        stmts = []
        while self.pos < len(self.tokens):
            self.skip_nl()
            t = self.peek()
            if t is None:
                break
            if t.code != CODE_IDENTIFIER:
                self.pos += 1
                continue
            st = self._parse_stmt()
            if st is not None:
                stmts.append(st)
        return stmts

    def _parse_stmt(self):
        id_t = self.peek()
        if id_t is None or id_t.code != CODE_IDENTIFIER:
            return None
        self.pos += 1
        self.skip_nl()
        op_t = self.peek()
        if op_t is None or op_t.code not in (CODE_ASSIGN, CODE_COMPOUND_ASSIGN):
            return AssignStmtNode(id_t.lexeme, id_t, None, IntNode(), None)
        op_lex = op_t.lexeme
        self.pos += 1
        rhs = self._parse_additive()
        self.skip_nl()
        if self.peek() and self.peek().code == CODE_SEMICOLON:
            self.pos += 1
        return AssignStmtNode(id_t.lexeme, id_t, op_lex, IntNode(), rhs)

    def _parse_additive(self):
        self.skip_nl()
        left = self._parse_term()
        if left is None:
            return None
        while self.peek() and self.peek().code == CODE_ARITH:
            op = self.peek().lexeme
            self.pos += 1
            right = self._parse_term()
            left = BinaryOpNode(op, left, right)
        return left

    def _parse_term(self):
        self.skip_nl()
        t = self.peek()
        if t is None:
            return None
        if t.code == CODE_IDENTIFIER:
            self.pos += 1
            return IdentifierNode(t.lexeme, t)
        if t.code == CODE_DIGIT:
            self.pos += 1
            try:
                val = int(t.lexeme)
            except ValueError:
                val = 0
            return IntLiteralNode(val, t)
        return None


class _ConditionAstParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def skip_nl(self):
        while self.pos < len(self.tokens) and self.tokens[self.pos].code == CODE_NEWLINE:
            self.pos += 1

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def parse(self):
        self.skip_nl()
        return self._parse_logical_or()

    def _parse_logical_or(self):
        self.skip_nl()
        left = self._parse_logical_and()
        while self.peek() and self.peek().code == CODE_OR:
            self.pos += 1
            self.skip_nl()
            right = self._parse_logical_and()
            if left is None or right is None:
                break
            left = LogicalOrNode(left, right)
        return left

    def _parse_logical_and(self):
        self.skip_nl()
        left = self._parse_logical_term()
        while self.peek() and self.peek().code == CODE_AND:
            self.pos += 1
            self.skip_nl()
            right = self._parse_logical_term()
            if left is None or right is None:
                break
            left = LogicalAndNode(left, right)
        return left

    def _parse_logical_term(self):
        self.skip_nl()
        if self.peek() and self.peek().code == CODE_NOT:
            self.pos += 1
            self.skip_nl()
            inner = self._parse_logical_primary()
            if inner is None:
                return None
            return NotNode(inner)
        return self._parse_logical_primary()

    def _parse_logical_primary(self):
        self.skip_nl()
        t = self.peek()
        if t and t.code == CODE_LPAREN:
            self.pos += 1
            self.skip_nl()
            inner = self._parse_logical_or()
            self.skip_nl()
            if self.peek() and self.peek().code == CODE_RPAREN:
                self.pos += 1
            return inner
        if t and t.code == CODE_RPAREN:
            self.pos += 1
            return self._parse_logical_primary()
        return self._parse_comparison()

    def _parse_comparison(self):
        self.skip_nl()
        t = self.peek()
        if t is None or t.code != CODE_IDENTIFIER:
            return None
        self.pos += 1
        left = IdentifierNode(t.lexeme, t)
        self.skip_nl()
        op_t = self.peek()
        if op_t is None or op_t.code != CODE_COMPARE:
            return left
        op_lex = op_t.lexeme
        self.pos += 1
        self.skip_nl()
        val = self.peek()
        if val is None:
            return ComparisonNode(left, op_lex, None)
        if val.code == CODE_IDENTIFIER:
            self.pos += 1
            right = IdentifierNode(val.lexeme, val)
        elif val.code == CODE_DIGIT:
            self.pos += 1
            try:
                v = int(val.lexeme)
            except ValueError:
                v = 0
            right = IntLiteralNode(v, val)
        else:
            return ComparisonNode(left, op_lex, None)
        return ComparisonNode(left, op_lex, right)


def _format_assign_stmt_innards(pfx, stmt):
    op_json = json.dumps(stmt.operator, ensure_ascii=False)
    return (
        f'{pfx}├── name: "{stmt.name}"\n'
        + f"{pfx}├── operator: {op_json}\n"
        + _format_int_type_block(pfx, with_continuation_below=True)
        + _format_value_under_assign(pfx, stmt.value)
    )


def _format_comparison_innards(pfx, cmp):
    name_line = ""
    if cmp.left is not None:
        name_line = f'{pfx}├── name: "{cmp.left.name}"\n'
    op_json = json.dumps(cmp.operator, ensure_ascii=False)
    return (
        name_line
        + f"{pfx}├── operator: {op_json}\n"
        + _format_int_type_block(pfx, with_continuation_below=True)
        + _format_value_under_comparison(pfx, cmp.right)
    )


def _format_repeat_while_innards(child_prefix, rw):
    lines = []
    stmts = rw.body
    n_st = len(stmts)
    has_cond = rw.condition is not None
    if n_st == 0:
        arm0 = "├── " if has_cond else "└── "
        lines.append(f"{child_prefix}{arm0}body: (пусто)\n")
    for i, st in enumerate(stmts):
        more_below = (i < n_st - 1) or has_cond
        arm = "├── " if more_below else "└── "
        lines.append(f"{child_prefix}{arm}body: AssignStmtNode\n")
        inner = child_prefix + ("│   " if more_below else "    ")
        lines.append(_format_assign_stmt_innards(inner, st))
    if has_cond:
        cond = rw.condition
        ctype = cond.node_type
        if isinstance(cond, ComparisonNode):
            lines.append(f"{child_prefix}└── condition: ComparisonNode\n")
            lines.append(_format_comparison_innards(child_prefix + "    ", cond))
        else:
            lines.append(f"{child_prefix}└── condition: {ctype}\n")
            lines.append(format_ast_tree(cond, child_prefix + "    ", True))
    return "".join(lines)


def _format_int_literal_tree(prefix, is_last, n):
    arm = "└── " if is_last else "├── "
    np = prefix + ("    " if is_last else "│   ")
    return f"{prefix}{arm}IntLiteralNode\n{np}└── value: {n.value}\n"


def _format_identifier_tree(prefix, is_last, n):
    arm = "└── " if is_last else "├── "
    np = prefix + ("    " if is_last else "│   ")
    return (
        f"{prefix}{arm}IdentifierNode\n"
        f"{np}├── type: Int\n"
        f'{np}└── name: "{n.name}"\n'
    )


def _format_int_type_block(pfx, with_continuation_below):
    cont = "│   " if with_continuation_below else "    "
    return f'{pfx}├── type: IntNode\n{pfx}{cont}└── name: "Int"\n'


def _format_value_under_assign(child_prefix, val):
    p = child_prefix
    if val is None:
        return f"{p}└── value: null\n"
    if isinstance(val, IntLiteralNode):
        return (
            f"{p}└── value: IntLiteralNode\n"
            f"{p}    └── value: {val.value}\n"
        )
    if isinstance(val, IdentifierNode):
        return (
            f"{p}└── value: IdentifierNode\n"
            f'{p}    ├── type: Int\n'
            f'{p}    └── name: "{val.name}"\n'
        )
    if isinstance(val, BinaryOpNode):
        np = p + "    "
        return (
            f"{p}└── value: BinaryOpNode\n"
            + format_ast_tree(val.left, np, False)
            + f"{np}├── operator: {json.dumps(val.operator, ensure_ascii=False)}\n"
            + format_ast_tree(val.right, np, True)
        )
    return f"{p}└── value: {type(val).__name__}\n"


def _format_value_under_comparison(child_prefix, val):
    p = child_prefix
    if val is None:
        return f"{p}└── value: null\n"
    if isinstance(val, IntLiteralNode):
        return (
            f"{p}└── value: IntLiteralNode\n"
            f"{p}    └── value: {val.value}\n"
        )
    return (
        f"{p}└── value: IdentifierNode\n"
        f'{p}    ├── type: Int\n'
        f'{p}    └── name: "{val.name}"\n'
    )


def format_ast_tree(node, prefix="", is_last=True):
    if node is None:
        connector = "└── " if is_last else "├── "
        return f"{prefix}{connector}null\n"
    connector = "└── " if is_last else "├── "
    child_prefix = prefix + ("    " if is_last else "│   ")

    if isinstance(node, ProgramNode):
        lines = [f"{prefix}{connector}Program\n"]
        cp = child_prefix
        decls = node.declarations
        rw = node.repeat_while
        n_decl = len(decls)
        has_repeat = rw is not None
        for i, d in enumerate(decls):
            more = (i < n_decl - 1) or has_repeat
            arm = "├── " if more else "└── "
            lines.append(f"{cp}{arm}declaration: AssignStmtNode\n")
            inner = cp + ("│   " if more else "    ")
            lines.append(_format_assign_stmt_innards(inner, d))
        if has_repeat:
            arm_r = "└── "
            lines.append(f"{cp}{arm_r}repeatWhile: RepeatWhileNode\n")
            lines.append(_format_repeat_while_innards(cp + "    ", rw))
        return "".join(lines)

    if isinstance(node, RepeatWhileNode):
        lines = [f"{prefix}{connector}{node.node_type}\n"]
        lines.append(_format_repeat_while_innards(child_prefix, node))
        return "".join(lines)

    if isinstance(node, IntNode):
        lines = [f"{prefix}{connector}IntNode\n"]
        lines.append(f'{child_prefix}└── name: "Int"\n')
        return "".join(lines)

    if isinstance(node, AssignStmtNode):
        lines = [f"{prefix}{connector}{node.node_type}\n"]
        lines.append(
            f'{child_prefix}├── name: "{node.name}"\n'
            + f"{child_prefix}├── operator: {json.dumps(node.operator, ensure_ascii=False)}\n"
        )
        lines.append(_format_int_type_block(child_prefix, with_continuation_below=True))
        lines.append(_format_value_under_assign(child_prefix, node.value))
        return "".join(lines)

    if isinstance(node, BinaryOpNode):
        lines = [f"{prefix}{connector}BinaryOpNode\n"]
        if node.left is not None:
            lines.append(format_ast_tree(node.left, child_prefix, False))
            lines.append(
                f"{child_prefix}├── operator: {json.dumps(node.operator, ensure_ascii=False)}\n"
            )
            if node.right is None:
                lines.append(f"{child_prefix}└── null\n")
            else:
                lines.append(format_ast_tree(node.right, child_prefix, True))
        else:
            lines.append(
                f"{child_prefix}├── operator: {json.dumps(node.operator, ensure_ascii=False)}\n"
            )
            if node.right is None:
                lines.append(f"{child_prefix}└── null\n")
            else:
                lines.append(format_ast_tree(node.right, child_prefix, True))
        return "".join(lines)

    if isinstance(node, (LogicalAndNode, LogicalOrNode)):
        lines = [f"{prefix}{connector}{node.node_type}\n"]
        lines.append(format_ast_tree(node.left, child_prefix, False))
        lines.append(format_ast_tree(node.right, child_prefix, True))
        return "".join(lines)

    if isinstance(node, NotNode):
        lines = [f"{prefix}{connector}{node.node_type}\n"]
        lines.append(format_ast_tree(node.child, child_prefix, True))
        return "".join(lines)

    if isinstance(node, ComparisonNode):
        lines = [f"{prefix}{connector}{node.node_type}\n"]
        lines.append(_format_comparison_innards(child_prefix, node))
        return "".join(lines)

    if isinstance(node, IntLiteralNode):
        return _format_int_literal_tree(prefix, is_last, node)

    if isinstance(node, IdentifierNode):
        return _format_identifier_tree(prefix, is_last, node)

    return f"{prefix}{connector}{type(node).__name__}\n"


def format_ast_tree_pretty(node):
    if node is None:
        return "(AST отсутствует)\n"
    raw = format_ast_tree(node, "", True)
    if raw.startswith("└── "):
        raw = raw[4:]
    return raw


def ast_node_to_json(obj):
    """Сериализация AST в структуру для json.dumps."""
    if obj is None:
        return None
    if isinstance(obj, ProgramNode):
        return {
            "node": obj.node_type,
            "declarations": [ast_node_to_json(x) for x in obj.declarations],
            "repeatWhile": ast_node_to_json(obj.repeat_while),
        }
    if isinstance(obj, RepeatWhileNode):
        return {
            "node": obj.node_type,
            "body": [ast_node_to_json(x) for x in obj.body],
            "condition": ast_node_to_json(obj.condition),
        }
    if isinstance(obj, AssignStmtNode):
        return {
            "node": obj.node_type,
            "name": obj.name,
            "operator": obj.operator,
            "type": ast_node_to_json(obj.value_type),
            "value": ast_node_to_json(obj.value),
        }
    if isinstance(obj, IntNode):
        return {"node": obj.node_type, "name": "Int"}
    if isinstance(obj, IntLiteralNode):
        return {"node": obj.node_type, "value": obj.value}
    if isinstance(obj, IdentifierNode):
        return {"node": obj.node_type, "type": "Int", "name": obj.name}
    if isinstance(obj, BinaryOpNode):
        return {
            "node": obj.node_type,
            "left": ast_node_to_json(obj.left),
            "operator": obj.operator,
            "right": ast_node_to_json(obj.right),
        }
    if isinstance(obj, ComparisonNode):
        d = {"node": obj.node_type, "operator": obj.operator, "value": ast_node_to_json(obj.right)}
        if obj.left is not None:
            d["name"] = obj.left.name
        return d
    if isinstance(obj, LogicalAndNode):
        return {
            "node": obj.node_type,
            "left": ast_node_to_json(obj.left),
            "right": ast_node_to_json(obj.right),
        }
    if isinstance(obj, LogicalOrNode):
        return {
            "node": obj.node_type,
            "left": ast_node_to_json(obj.left),
            "right": ast_node_to_json(obj.right),
        }
    if isinstance(obj, NotNode):
        return {"node": obj.node_type, "child": ast_node_to_json(obj.child)}
    return str(type(obj).__name__)


def format_ast_json_pretty(ast_root):
    if ast_root is None:
        return "{}\n"
    return json.dumps(ast_node_to_json(ast_root), ensure_ascii=False, indent=2) + "\n"


class SemanticAnalyzer:
    def __init__(self):
        self.errors = []
        self.table = SymbolTable()

    def _err(self, msg, tok, fragment=None):
        frag = fragment if fragment is not None else (tok.lexeme if tok else "")
        self.errors.append(
            SemanticError(
                msg,
                tok.line if tok else 1,
                tok.start_pos if tok else 1,
                tok.end_pos if tok else 1,
                frag,
            )
        )

    def analyze(self, root):
        self.errors.clear()
        self.table = SymbolTable()
        if isinstance(root, ProgramNode):
            for st in root.declarations:
                self._stmt(st)
            rw = root.repeat_while
            if rw is not None:
                for st in rw.body:
                    self._stmt(st)
                if rw.condition is not None:
                    self._check_logical_use(rw.condition)
        elif isinstance(root, RepeatWhileNode):
            for st in root.body:
                self._stmt(st)
            if root.condition is not None:
                self._check_logical_use(root.condition)

    def _check_literal(self, n):
        if n.value < INT32_MIN or n.value > INT32_MAX:
            self._err(
                f"Значение литерала {n.value} вне допустимого диапазона Int32 "
                f"[{INT32_MIN}; {INT32_MAX}]",
                n.token,
                n.token.lexeme,
            )
        return "Int"

    def _check_expr_use(self, n):
        if n is None:
            return "Int"
        if isinstance(n, IntLiteralNode):
            return self._check_literal(n)
        if isinstance(n, IdentifierNode):
            info = self.table.lookup(n.name)
            if info is None:
                self._err(
                    f'Идентификатор "{n.name}" использован до объявления',
                    n.token,
                    n.token.lexeme,
                )
            return "Int"
        if isinstance(n, BinaryOpNode):
            if n.left is not None:
                self._check_expr_use(n.left)
            if n.right is not None:
                self._check_expr_use(n.right)
            return "Int"
        return "Int"

    def _stmt(self, st):
        if st.operator is None:
            return
        rhs_type = self._check_expr_use(st.value)
        if rhs_type != "Int":
            self._err("Ожидался тип Int для правой части", st.name_token, st.name)

        if st.operator == "=":
            if self.table.is_declared(st.name):
                prev = self.table.lookup(st.name)
                self._err(
                    f'Идентификатор "{st.name}" уже объявлен ранее '
                    f"(строка {prev['line']})",
                    st.name_token,
                    st.name_token.lexeme,
                )
            else:
                self.table.declare(st.name, "Int", st.name_token.line)
        else:
            if not self.table.is_declared(st.name):
                self._err(
                    f'Идентификатор "{st.name}" не объявлен '
                    f"(для составного присваивания нужно предварительное объявление «=»)",
                    st.name_token,
                    st.name_token.lexeme,
                )

    def _check_logical_use(self, n):
        if n is None:
            return
        if isinstance(n, IdentifierNode):
            if not self.table.is_declared(n.name):
                self._err(
                    f'Идентификатор "{n.name}" в условии использован до объявления',
                    n.token,
                    n.token.lexeme,
                )
            return
        if isinstance(n, IntLiteralNode):
            self._check_literal(n)
            return
        if isinstance(n, ComparisonNode):
            if n.left is not None:
                self._check_logical_use(n.left)
            if n.right is not None:
                self._check_logical_use(n.right)
            return
        if isinstance(n, (LogicalAndNode, LogicalOrNode)):
            self._check_logical_use(n.left)
            self._check_logical_use(n.right)
            return
        if isinstance(n, NotNode):
            self._check_logical_use(n.child)
            return
        if isinstance(n, BinaryOpNode):
            self._check_expr_use(n)


def _build_program_ast(clean_tokens, spans):
    if not spans:
        return None
    pre_s, pre_e, bs, be, cs, ce = spans
    if bs is None or be is None:
        return None
    prelude = []
    if pre_e > pre_s:
        prelude = _BodyAstParser(clean_tokens[pre_s:pre_e]).parse_all()
    body_toks = clean_tokens[bs:be]
    body = _BodyAstParser(body_toks).parse_all()
    cond = None
    if cs is not None and ce is not None and cs < ce:
        cond = _ConditionAstParser(clean_tokens[cs:ce]).parse()
    rw = RepeatWhileNode(body, cond)
    return ProgramNode(prelude, rw)


def analyze_program(tokens):
    err_code = TOKEN_TYPES["ERROR"][0]
    clean = [t for t in filter_tokens_for_parser(tokens) if t.code != err_code]
    syn = analyze_syntax(tokens)
    ast_root = _build_program_ast(clean, syn.ast_spans) if syn.ast_spans else None
    sem_errors = []
    if ast_root is not None:
        an = SemanticAnalyzer()
        an.analyze(ast_root)
        sem_errors = an.errors

    tree_txt = format_ast_tree_pretty(ast_root)
    json_txt = format_ast_json_pretty(ast_root)

    return SemanticResult(
        syntax_ok=syn.ok,
        syntax_errors=list(syn.errors),
        semantic_errors=sem_errors,
        ast_root=ast_root,
        ast_tree_text=tree_txt,
        ast_json_text=json_txt,
    )


def clean_tokens_for_semantics(tokens):
    err_code = TOKEN_TYPES["ERROR"][0]
    return [t for t in filter_tokens_for_parser(tokens) if t.code != err_code]
