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

from myscript.lang import Operator, DataType

if TYPE_CHECKING:
    from typing import Any, Union, Iterator, Iterable


class LexerError(Exception): pass


class Token(NamedTuple):
    text: str
    item: Union[Operator, Literal, Identifier]
    lineno: int
    lexpos: int

    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.item!r})'

    def __str__(self) -> str:
        return self.text

    def is_operator(self) -> bool:
        return isinstance(self.item, Operator)

    def is_literal(self) -> bool:
        return isinstance(self.item, Literal)

    def is_identifier(self) -> bool:
        return isinstance(self.item, Identifier)


class Literal(NamedTuple):
    type: DataType
    value: Any

class Identifier(NamedTuple):
    name: str


## PLY Rules
class Lexer:
    reserved = {
        'not'   : Operator.Not,
        'and'   : Operator.And,
        'or'    : Operator.Or,
        'xor'   : Operator.Xor,
        'do'    : Operator.Do,
        'while' : Operator.While,
        'until' : Operator.Until,
        'if'    : Operator.If,
    }

    tokens = [
        ## Operators
        *(op.name for op in Operator),

        ## Literals
        'bool',
        'integer',
        'float',
        'array',
        'string',
        'block',

        ## Identifiers
        'identifier',
    ]

    t_ignore = string.whitespace
    t_ignore_comment = r'//.*'

    ## Literals

    def t_bool(self, t):
        r'true|false'
        t.value = t.value, Literal(DataType.Bool, t.value == 'true')
        return t

    def t_integer(self, t):
        r'[+-]?[0-9]+(?!\.)'
        t.value = t.value, Literal(DataType.Number, int(t.value))
        return t

    def t_float(self, t):
        r'[+-]?([0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)'
        t.value = t.value, Literal(DataType.Number, float(t.value))
        return t

    def t_string(self, t):
        r'\'.*?\'|".*?"'
        t.value = t.value, Literal(DataType.String, t.value[1:-1])
        return t

    def t_array(self, t):
        r'\[.*?\]'

        sublexer = self._lexer.clone()
        sublexer.input(t.value[1:-1])
        content = tuple(self._emit_tokens(sublexer))

        t.value = t.value, Literal(DataType.Array, content)
        return t

    def t_block(self, t):
        r'\{.*?\}'

        sublexer = self._lexer.clone()
        sublexer.input(t.value[1:-1])
        content = tuple(self._emit_tokens(sublexer))

        t.value = t.value, Literal(DataType.Block, content)
        return t

    ## Other

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # Error handling rule
    def t_error(self, t):
        raise LexerError(f"Illegal character '{t.value[0]}'")
        # t.lexer.skip(1)

    def __init__(self, **kwargs):
        self._lexer = lex.lex(object=self, **kwargs)

    def input(self, text: str) -> None:
        self._lexer.input(text)

    def get_tokens(self) -> Iterable[Token]:
        return self._emit_tokens(self._lexer)

    @classmethod
    def _emit_tokens(cls, lexer) -> Iterator[Token]:
        for t in lexer:
            text, value = t.value
            yield Token(text, value, t.lineno, t.lexpos)


## Operators
for op in Operator:
    name = f't_{op.name}'

    @lex.TOKEN(op.token)
    def handler(self, t):
        t.value = t.value, Operator[t.type]
        return t

    setattr(Lexer, name, handler)


## Identifiers
def t_identifier(self, t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    reserved = self.reserved.get(t.value)
    if reserved:
        t.type = reserved.name
        t.value = t.value, reserved
    else:
        t.value = t.value, Identifier(t.value)
    return t
Lexer.t_identifier = t_identifier



if __name__ == '__main__':
    tests = [
        "'dsds' +2.4 576 { true} foobar xor \"false\" '?' ++ while [  + -.333 -] if ** ",
        "1 1+ >> > < << not ! ~ ",
    ]

    for test in tests:
        print(test)
        lexer = Lexer()
        lexer.input(test)
        for tok in lexer.get_tokens():
            print(repr(tok))