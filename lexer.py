""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

import re
import string
from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple

from ply import lex

from lang import Operator, DataType

if TYPE_CHECKING:
    from typing import Union, Optional, Iterator, Tuple


class LexerError(Exception): pass


class Token(NamedTuple):
    data: Union[Operator, Literal, Identifier, SpecialToken]
    lineno: int
    lexpos: int

class Literal(NamedTuple):
    type: DataType
    value: Any

class Identifier(NamedTuple):
    name: str

class SpecialToken(Enum):
    StartBlock = auto()
    EndBlock   = auto()
    StartArray = auto()
    EndArray   = auto()

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'


## PLY Rules
class Lexer:
    reserved = {
        'and'   : Operator.And,
        'or'    : Operator.Or,
        'xor'   : Operator.Xor,
        'do'    : Operator.Do,
        'while' : Operator.While,
        'until' : Operator.Until,
        'if'    : Operator.If,
    }

    tokens = [
        'start_block',
        'end_block',
        'start_arr',
        'end_arr',

        ## Operators
        *(op.name for op in Operator),

        ## Literals
        'bool',
        'integer',
        'float',
        'string',

        ## Identifiers
        'identifier',
    ]

    t_ignore = string.whitespace
    t_ignore_comment = r'//.*'

    ## Special Syntax
    
    def t_start_block(self, t):
        r'{'
        t.value = SpecialToken.StartBlock
        return t

    def t_end_block(self, t):
        r'}'
        t.value = SpecialToken.EndBlock
        return t

    def t_start_arr(self, t):
        r'\['
        t.value = SpecialToken.StartArray
        return t

    def t_end_arr(self, t):
        r'\]'
        t.value = SpecialToken.EndArray
        return t

    ## Literals

    def t_bool(self, t):
        r'true|false'
        t.value = Literal(DataType.Bool, t.value == 'true')
        return t

    def t_integer(self, t):
        r'[+-]?[0-9]+[^.]'
        t.value = Literal(DataType.Integer, int(t.value))
        return t

    def t_float(self, t):
        r'[+-]?([0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)'
        t.value = Literal(DataType.Float, float(t.value))
        return t

    def t_string(self, t):
        r'\'.*?\'|".*?"'
        t.value = Literal(DataType.String, t.value[1:-1])
        return t

    ## Other

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # Error handling rule
    def t_error(self, t):
        # raise LexerError(f"Illegal character '{t.value[0]}'")
        t.lexer.skip(1)

    def __init__(self, **kwargs):
        self._lexer = lex.lex(module=self, **kwargs)

    def input(self, text: str) -> None:
        self._lexer.input(text)

    def get_tokens(self) -> Iterator[Token]:
        # yield from self._lexer
        for t in self._lexer:
            yield Token(t.value, t.lineno, t.lexpos)


## Operators
for op in Operator:
    name = f't_{op.name}'

    @lex.TOKEN(op.token)
    def handler(self, t):
        t.value = Operator[t.type]
        return t

    setattr(Lexer, name, handler)


## Identifiers
def t_identifier(self, t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    reserved = self.reserved.get(t.value)
    if reserved:
        t.type = reserved.name
        t.value = reserved
    else:
        t.value = Identifier(t.value)
    return t
Lexer.t_identifier = t_identifier



if __name__ == '__main__':
    import sys

    lexer = Lexer()
    lexer.input(sys.argv[1])
    
    for tok in lexer.get_tokens():
        print(tok)