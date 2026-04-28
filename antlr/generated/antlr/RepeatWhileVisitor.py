# Generated from antlr\RepeatWhile.g4 by ANTLR 4.9.3
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .RepeatWhileParser import RepeatWhileParser
else:
    from RepeatWhileParser import RepeatWhileParser

# This class defines a complete generic visitor for a parse tree produced by RepeatWhileParser.

class RepeatWhileVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by RepeatWhileParser#program.
    def visitProgram(self, ctx:RepeatWhileParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#stmtList.
    def visitStmtList(self, ctx:RepeatWhileParser.StmtListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#stmt.
    def visitStmt(self, ctx:RepeatWhileParser.StmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#assignOp.
    def visitAssignOp(self, ctx:RepeatWhileParser.AssignOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#condition.
    def visitCondition(self, ctx:RepeatWhileParser.ConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#logicOp.
    def visitLogicOp(self, ctx:RepeatWhileParser.LogicOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#relOp.
    def visitRelOp(self, ctx:RepeatWhileParser.RelOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#expr.
    def visitExpr(self, ctx:RepeatWhileParser.ExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by RepeatWhileParser#arithOp.
    def visitArithOp(self, ctx:RepeatWhileParser.ArithOpContext):
        return self.visitChildren(ctx)



del RepeatWhileParser