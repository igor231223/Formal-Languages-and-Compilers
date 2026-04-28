from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.Token import Token

from antlr.generated.antlr.RepeatWhileLexer import RepeatWhileLexer
from antlr.generated.antlr.RepeatWhileParser import RepeatWhileParser
from parser import ParseError, ParseResult


class _CollectingErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        fragment = ""
        start_pos = column + 1
        end_pos = start_pos
        if offendingSymbol is not None and offendingSymbol.type != Token.EOF:
            fragment = offendingSymbol.text or ""
            if fragment:
                end_pos = start_pos + len(fragment) - 1
        self.errors.append(
            ParseError(
                fragment,
                line,
                start_pos,
                end_pos,
                f"Синтаксическая ошибка: {msg}",
            )
        )


def _collect_lexer_errors(token_stream):
    errors = []
    for tok in token_stream.tokens:
        if tok.type != RepeatWhileLexer.ERROR_CHAR:
            continue
        fragment = tok.text or ""
        start = tok.column + 1
        end = start + len(fragment) - 1 if fragment else start
        errors.append(
            ParseError(
                fragment,
                tok.line,
                start,
                end,
                "Недопустимая лексема (лексическая ошибка)",
            )
        )
    return errors


def analyze_syntax_antlr(text):
    input_stream = InputStream(text)
    lexer = RepeatWhileLexer(input_stream)
    lexer_listener = _CollectingErrorListener()
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)

    token_stream = CommonTokenStream(lexer)
    token_stream.fill()

    parser = RepeatWhileParser(token_stream)
    parser_listener = _CollectingErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(parser_listener)
    parser.program()

    all_errors = []
    all_errors.extend(_collect_lexer_errors(token_stream))
    all_errors.extend(lexer_listener.errors)
    all_errors.extend(parser_listener.errors)

    all_errors.sort(key=lambda e: (e.line, e.start_pos, e.end_pos, e.message))
    return ParseResult(len(all_errors) == 0, all_errors)
