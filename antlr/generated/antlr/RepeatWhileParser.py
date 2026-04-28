# Generated from antlr\RepeatWhile.g4 by ANTLR 4.9.3
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO


def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3\36")
        buf.write("E\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7\4\b")
        buf.write("\t\b\4\t\t\t\4\n\t\n\3\2\3\2\3\2\5\2\30\n\2\3\2\3\2\3")
        buf.write("\2\3\2\3\2\3\2\3\3\6\3!\n\3\r\3\16\3\"\3\4\3\4\3\4\3\4")
        buf.write("\5\4)\n\4\3\5\3\5\3\6\3\6\3\6\3\6\3\6\3\6\5\6\63\n\6\3")
        buf.write("\7\3\7\3\b\3\b\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\5\tA\n")
        buf.write("\t\3\n\3\n\3\n\2\2\13\2\4\6\b\n\f\16\20\22\2\6\3\2\f\20")
        buf.write("\3\2\5\6\3\2\21\26\3\2\27\32\2A\2\24\3\2\2\2\4 \3\2\2")
        buf.write("\2\6$\3\2\2\2\b*\3\2\2\2\n,\3\2\2\2\f\64\3\2\2\2\16\66")
        buf.write("\3\2\2\2\20@\3\2\2\2\22B\3\2\2\2\24\25\7\3\2\2\25\27\7")
        buf.write("\7\2\2\26\30\5\4\3\2\27\26\3\2\2\2\27\30\3\2\2\2\30\31")
        buf.write("\3\2\2\2\31\32\7\b\2\2\32\33\7\4\2\2\33\34\5\n\6\2\34")
        buf.write("\35\7\13\2\2\35\36\7\2\2\3\36\3\3\2\2\2\37!\5\6\4\2 \37")
        buf.write("\3\2\2\2!\"\3\2\2\2\" \3\2\2\2\"#\3\2\2\2#\5\3\2\2\2$")
        buf.write("%\7\33\2\2%&\5\b\5\2&(\5\20\t\2\')\7\13\2\2(\'\3\2\2\2")
        buf.write("()\3\2\2\2)\7\3\2\2\2*+\t\2\2\2+\t\3\2\2\2,-\5\20\t\2")
        buf.write("-.\5\16\b\2.\62\5\20\t\2/\60\5\f\7\2\60\61\5\n\6\2\61")
        buf.write("\63\3\2\2\2\62/\3\2\2\2\62\63\3\2\2\2\63\13\3\2\2\2\64")
        buf.write("\65\t\3\2\2\65\r\3\2\2\2\66\67\t\4\2\2\67\17\3\2\2\28")
        buf.write("A\7\33\2\29A\7\34\2\2:;\7\t\2\2;<\5\20\t\2<=\5\22\n\2")
        buf.write("=>\5\20\t\2>?\7\n\2\2?A\3\2\2\2@8\3\2\2\2@9\3\2\2\2@:")
        buf.write("\3\2\2\2A\21\3\2\2\2BC\t\5\2\2C\23\3\2\2\2\7\27\"(\62")
        buf.write("@")
        return buf.getvalue()


class RepeatWhileParser ( Parser ):

    grammarFileName = "RepeatWhile.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'repeat'", "'while'", "'and'", "'or'", 
                     "'{'", "'}'", "'('", "')'", "';'", "'+='", "'-='", 
                     "'*='", "'/='", "'='", "'=='", "'!='", "'<='", "'>='", 
                     "'<'", "'>'", "'+'", "'-'", "'*'", "'/'" ]

    symbolicNames = [ "<INVALID>", "REPEAT", "WHILE", "AND", "OR", "LBRACE", 
                      "RBRACE", "LPAREN", "RPAREN", "SEMI", "ADD_ASSIGN", 
                      "SUB_ASSIGN", "MUL_ASSIGN", "DIV_ASSIGN", "ASSIGN", 
                      "EQ", "NEQ", "LE", "GE", "LT", "GT", "ADD", "SUB", 
                      "MUL", "DIV", "IDENTIFIER", "NUMBER", "WS", "ERROR_CHAR" ]

    RULE_program = 0
    RULE_stmtList = 1
    RULE_stmt = 2
    RULE_assignOp = 3
    RULE_condition = 4
    RULE_logicOp = 5
    RULE_relOp = 6
    RULE_expr = 7
    RULE_arithOp = 8

    ruleNames =  [ "program", "stmtList", "stmt", "assignOp", "condition", 
                   "logicOp", "relOp", "expr", "arithOp" ]

    EOF = Token.EOF
    REPEAT=1
    WHILE=2
    AND=3
    OR=4
    LBRACE=5
    RBRACE=6
    LPAREN=7
    RPAREN=8
    SEMI=9
    ADD_ASSIGN=10
    SUB_ASSIGN=11
    MUL_ASSIGN=12
    DIV_ASSIGN=13
    ASSIGN=14
    EQ=15
    NEQ=16
    LE=17
    GE=18
    LT=19
    GT=20
    ADD=21
    SUB=22
    MUL=23
    DIV=24
    IDENTIFIER=25
    NUMBER=26
    WS=27
    ERROR_CHAR=28

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.9.3")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ProgramContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def REPEAT(self):
            return self.getToken(RepeatWhileParser.REPEAT, 0)

        def LBRACE(self):
            return self.getToken(RepeatWhileParser.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(RepeatWhileParser.RBRACE, 0)

        def WHILE(self):
            return self.getToken(RepeatWhileParser.WHILE, 0)

        def condition(self):
            return self.getTypedRuleContext(RepeatWhileParser.ConditionContext,0)


        def SEMI(self):
            return self.getToken(RepeatWhileParser.SEMI, 0)

        def EOF(self):
            return self.getToken(RepeatWhileParser.EOF, 0)

        def stmtList(self):
            return self.getTypedRuleContext(RepeatWhileParser.StmtListContext,0)


        def getRuleIndex(self):
            return RepeatWhileParser.RULE_program

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgram" ):
                return visitor.visitProgram(self)
            else:
                return visitor.visitChildren(self)




    def program(self):

        localctx = RepeatWhileParser.ProgramContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_program)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 18
            self.match(RepeatWhileParser.REPEAT)
            self.state = 19
            self.match(RepeatWhileParser.LBRACE)
            self.state = 21
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==RepeatWhileParser.IDENTIFIER:
                self.state = 20
                self.stmtList()


            self.state = 23
            self.match(RepeatWhileParser.RBRACE)
            self.state = 24
            self.match(RepeatWhileParser.WHILE)
            self.state = 25
            self.condition()
            self.state = 26
            self.match(RepeatWhileParser.SEMI)
            self.state = 27
            self.match(RepeatWhileParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StmtListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stmt(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(RepeatWhileParser.StmtContext)
            else:
                return self.getTypedRuleContext(RepeatWhileParser.StmtContext,i)


        def getRuleIndex(self):
            return RepeatWhileParser.RULE_stmtList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStmtList" ):
                return visitor.visitStmtList(self)
            else:
                return visitor.visitChildren(self)




    def stmtList(self):

        localctx = RepeatWhileParser.StmtListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_stmtList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 30 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 29
                self.stmt()
                self.state = 32 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==RepeatWhileParser.IDENTIFIER):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(RepeatWhileParser.IDENTIFIER, 0)

        def assignOp(self):
            return self.getTypedRuleContext(RepeatWhileParser.AssignOpContext,0)


        def expr(self):
            return self.getTypedRuleContext(RepeatWhileParser.ExprContext,0)


        def SEMI(self):
            return self.getToken(RepeatWhileParser.SEMI, 0)

        def getRuleIndex(self):
            return RepeatWhileParser.RULE_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStmt" ):
                return visitor.visitStmt(self)
            else:
                return visitor.visitChildren(self)




    def stmt(self):

        localctx = RepeatWhileParser.StmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 34
            self.match(RepeatWhileParser.IDENTIFIER)
            self.state = 35
            self.assignOp()
            self.state = 36
            self.expr()
            self.state = 38
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==RepeatWhileParser.SEMI:
                self.state = 37
                self.match(RepeatWhileParser.SEMI)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AssignOpContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSIGN(self):
            return self.getToken(RepeatWhileParser.ASSIGN, 0)

        def ADD_ASSIGN(self):
            return self.getToken(RepeatWhileParser.ADD_ASSIGN, 0)

        def SUB_ASSIGN(self):
            return self.getToken(RepeatWhileParser.SUB_ASSIGN, 0)

        def MUL_ASSIGN(self):
            return self.getToken(RepeatWhileParser.MUL_ASSIGN, 0)

        def DIV_ASSIGN(self):
            return self.getToken(RepeatWhileParser.DIV_ASSIGN, 0)

        def getRuleIndex(self):
            return RepeatWhileParser.RULE_assignOp

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignOp" ):
                return visitor.visitAssignOp(self)
            else:
                return visitor.visitChildren(self)




    def assignOp(self):

        localctx = RepeatWhileParser.AssignOpContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_assignOp)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 40
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << RepeatWhileParser.ADD_ASSIGN) | (1 << RepeatWhileParser.SUB_ASSIGN) | (1 << RepeatWhileParser.MUL_ASSIGN) | (1 << RepeatWhileParser.DIV_ASSIGN) | (1 << RepeatWhileParser.ASSIGN))) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConditionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(RepeatWhileParser.ExprContext)
            else:
                return self.getTypedRuleContext(RepeatWhileParser.ExprContext,i)


        def relOp(self):
            return self.getTypedRuleContext(RepeatWhileParser.RelOpContext,0)


        def logicOp(self):
            return self.getTypedRuleContext(RepeatWhileParser.LogicOpContext,0)


        def condition(self):
            return self.getTypedRuleContext(RepeatWhileParser.ConditionContext,0)


        def getRuleIndex(self):
            return RepeatWhileParser.RULE_condition

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCondition" ):
                return visitor.visitCondition(self)
            else:
                return visitor.visitChildren(self)




    def condition(self):

        localctx = RepeatWhileParser.ConditionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_condition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 42
            self.expr()
            self.state = 43
            self.relOp()
            self.state = 44
            self.expr()
            self.state = 48
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==RepeatWhileParser.AND or _la==RepeatWhileParser.OR:
                self.state = 45
                self.logicOp()
                self.state = 46
                self.condition()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LogicOpContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def AND(self):
            return self.getToken(RepeatWhileParser.AND, 0)

        def OR(self):
            return self.getToken(RepeatWhileParser.OR, 0)

        def getRuleIndex(self):
            return RepeatWhileParser.RULE_logicOp

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLogicOp" ):
                return visitor.visitLogicOp(self)
            else:
                return visitor.visitChildren(self)




    def logicOp(self):

        localctx = RepeatWhileParser.LogicOpContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_logicOp)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 50
            _la = self._input.LA(1)
            if not(_la==RepeatWhileParser.AND or _la==RepeatWhileParser.OR):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RelOpContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EQ(self):
            return self.getToken(RepeatWhileParser.EQ, 0)

        def NEQ(self):
            return self.getToken(RepeatWhileParser.NEQ, 0)

        def LT(self):
            return self.getToken(RepeatWhileParser.LT, 0)

        def GT(self):
            return self.getToken(RepeatWhileParser.GT, 0)

        def LE(self):
            return self.getToken(RepeatWhileParser.LE, 0)

        def GE(self):
            return self.getToken(RepeatWhileParser.GE, 0)

        def getRuleIndex(self):
            return RepeatWhileParser.RULE_relOp

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRelOp" ):
                return visitor.visitRelOp(self)
            else:
                return visitor.visitChildren(self)




    def relOp(self):

        localctx = RepeatWhileParser.RelOpContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_relOp)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 52
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << RepeatWhileParser.EQ) | (1 << RepeatWhileParser.NEQ) | (1 << RepeatWhileParser.LE) | (1 << RepeatWhileParser.GE) | (1 << RepeatWhileParser.LT) | (1 << RepeatWhileParser.GT))) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(RepeatWhileParser.IDENTIFIER, 0)

        def NUMBER(self):
            return self.getToken(RepeatWhileParser.NUMBER, 0)

        def LPAREN(self):
            return self.getToken(RepeatWhileParser.LPAREN, 0)

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(RepeatWhileParser.ExprContext)
            else:
                return self.getTypedRuleContext(RepeatWhileParser.ExprContext,i)


        def arithOp(self):
            return self.getTypedRuleContext(RepeatWhileParser.ArithOpContext,0)


        def RPAREN(self):
            return self.getToken(RepeatWhileParser.RPAREN, 0)

        def getRuleIndex(self):
            return RepeatWhileParser.RULE_expr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpr" ):
                return visitor.visitExpr(self)
            else:
                return visitor.visitChildren(self)




    def expr(self):

        localctx = RepeatWhileParser.ExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_expr)
        try:
            self.state = 62
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [RepeatWhileParser.IDENTIFIER]:
                self.enterOuterAlt(localctx, 1)
                self.state = 54
                self.match(RepeatWhileParser.IDENTIFIER)
                pass
            elif token in [RepeatWhileParser.NUMBER]:
                self.enterOuterAlt(localctx, 2)
                self.state = 55
                self.match(RepeatWhileParser.NUMBER)
                pass
            elif token in [RepeatWhileParser.LPAREN]:
                self.enterOuterAlt(localctx, 3)
                self.state = 56
                self.match(RepeatWhileParser.LPAREN)
                self.state = 57
                self.expr()
                self.state = 58
                self.arithOp()
                self.state = 59
                self.expr()
                self.state = 60
                self.match(RepeatWhileParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArithOpContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ADD(self):
            return self.getToken(RepeatWhileParser.ADD, 0)

        def SUB(self):
            return self.getToken(RepeatWhileParser.SUB, 0)

        def MUL(self):
            return self.getToken(RepeatWhileParser.MUL, 0)

        def DIV(self):
            return self.getToken(RepeatWhileParser.DIV, 0)

        def getRuleIndex(self):
            return RepeatWhileParser.RULE_arithOp

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArithOp" ):
                return visitor.visitArithOp(self)
            else:
                return visitor.visitChildren(self)




    def arithOp(self):

        localctx = RepeatWhileParser.ArithOpContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_arithOp)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 64
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << RepeatWhileParser.ADD) | (1 << RepeatWhileParser.SUB) | (1 << RepeatWhileParser.MUL) | (1 << RepeatWhileParser.DIV))) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





