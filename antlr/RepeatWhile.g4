grammar RepeatWhile;

program
    : REPEAT LBRACE stmtList? RBRACE WHILE condition SEMI EOF
    ;

stmtList
    : stmt+
    ;

stmt
    : IDENTIFIER assignOp expr SEMI?
    ;

assignOp
    : ASSIGN
    | ADD_ASSIGN
    | SUB_ASSIGN
    | MUL_ASSIGN
    | DIV_ASSIGN
    ;

condition
    : expr relOp expr (logicOp condition)?
    ;

logicOp
    : AND
    | OR
    ;

relOp
    : EQ
    | NEQ
    | LT
    | GT
    | LE
    | GE
    ;

expr
    : IDENTIFIER
    | NUMBER
    | LPAREN expr arithOp expr RPAREN
    ;

arithOp
    : ADD
    | SUB
    | MUL
    | DIV
    ;

REPEAT: 'repeat';
WHILE: 'while';
AND: 'and';
OR: 'or';

LBRACE: '{';
RBRACE: '}';
LPAREN: '(';
RPAREN: ')';
SEMI: ';';

ADD_ASSIGN: '+=';
SUB_ASSIGN: '-=';
MUL_ASSIGN: '*=';
DIV_ASSIGN: '/=';
ASSIGN: '=';

EQ: '==';
NEQ: '!=';
LE: '<=';
GE: '>=';
LT: '<';
GT: '>';

ADD: '+';
SUB: '-';
MUL: '*';
DIV: '/';

IDENTIFIER: [a-zA-Z] [a-zA-Z0-9]*;
NUMBER: [0-9]+;

WS: [ \t\r\n]+ -> skip;

ERROR_CHAR: .;
