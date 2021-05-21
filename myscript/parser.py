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

from myscript.lang import DataType, Operator
from myscript.values import DataValue
from myscript.errors import ScriptError

if TYPE_CHECKING:
    from typing import Any, Union, Iterator, Iterable



class Token(NamedTuple):
    text: str
    item: Union[Operator, Literal, Identifier, SpecialToken]
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

    def is_special(self, special: Optional[SpecialToken] = None) -> bool:
        if special is None:
            return isinstance(self.item, SpecialToken)
        return self.item == special


class Literal(NamedTuple):
    type: DataType
    value: Any

    def get_value(self) -> DataValue:
        return DataValue.create(self.type, self.value)

class Identifier(NamedTuple):
    name: str

class SpecialToken(Enum):
    StartBlock = auto()
    EndBlock   = auto()
    StartArray = auto()
    EndArray   = auto()

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'


###### Lexer

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
        ## Specials
        'start_block',
        'end_block',
        'start_array',
        'end_array',

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
        t.value = t.value, SpecialToken.StartBlock
        return t

    def t_end_block(self, t):
        r'}'
        t.value = t.value, SpecialToken.EndBlock
        return t

    def t_start_array(self, t):
        r'\['
        t.value = t.value, SpecialToken.StartArray
        return t

    def t_end_array(self, t):
        r'\]'
        t.value = t.value, SpecialToken.EndArray
        return t

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


    ## Other

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # Error handling rule
    def t_error(self, t):
        raise ScriptError(f"Illegal character '{t.value[0]}'")
        t.lexer.skip(1)

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



###### Parser


class Parser:
    _matching = {
        SpecialToken.StartBlock : SpecialToken.EndBlock,
        SpecialToken.StartArray : SpecialToken.EndArray,
    }
    _literal = {
        SpecialToken.StartBlock : DataType.Block,
        SpecialToken.StartArray : DataType.Array,
    }

    def __init__(self, lexer: Optional[Lexer] = None):
        self.lexer = lexer or Lexer()
        self.tokgen = self.lexer.get_tokens()

    def input(self, text: str) -> None:
        self.lexer.input(text)

    @staticmethod
    def _get_next(tokens: Iterable[Token]) -> Optional[Token]:
        try:
            return next(tokens)
        except StopIteration:
            return None

    def get_tokens(self) -> Iterator[Token]:
        while (token := self._get_next(self.tokgen)) is not None:
            if token.is_special():
                literal = self._parse_recursive(self.tokgen, token.item)
                token = Token(item=literal, text=token.text, lineno=token.lineno, lexpos=token.lexpos)
            yield token

    # parse a nested structure down to a single block or array literal token
    def _parse_recursive(self, tokens: Iteratable[Token], parse_type: SpecialToken) -> Literal:
        matching_end = self._matching[parse_type]

        content = []
        while True:
            token = self._get_next(tokens)
            if token is None:
                raise ScriptError(f"could not find matching {matching_end}")

            if token.is_special(matching_end):
                return Literal(self._literal[parse_type], tuple(content))

            elif token.is_special():
                if token.item not in self._matching:
                    raise ScriptError('mismatched', token)
                literal = self._parse_recursive(tokens, token.item)
                token = Token(item=literal, text=token.text, lineno=token.lineno, lexpos=token.lexpos)
            
            content.append(token)



if __name__ == '__main__':
    tests = [
        "'dsds' +2.4 576 { true} foobar xor \"false\" '?' ++ while [  + -.333 -] if ** ",
        "1 1+ >> > < << not ! ~ ",
        # "1 1+ >> > [ < <<  { not ! ] ~ }",
        "1 [1+ { >> > < } [<<] not ! ~ ",
    ]

    for test in tests:
        print(test)
        lexer = Lexer()
        parser = Parser(lexer)
        parser.input(test)
        for tok in parser.get_tokens():
            print(repr(tok), repr(str(tok)))