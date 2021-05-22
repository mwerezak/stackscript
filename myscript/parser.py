""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

import string
from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple, Protocol, runtime_checkable

from ply import lex

from myscript.lang import DataType, Operator
from myscript.errors import ScriptError

if TYPE_CHECKING:
    from typing import Any, Union, Type, Iterator,  Callable



# class Token(NamedTuple):
#     text: str
#     item: Union[Operator, Literal, Identifier, SpecialToken]
#     lineno: int
#     lexpos: int
#
#     def __repr__(self) -> str:
#         return f'{self.__class__.__qualname__}({self.item!r})'
#
#     def __str__(self) -> str:
#         return self.text
#
#     def is_operator(self) -> bool:
#         return isinstance(self.item, Operator)
#
#     def is_literal(self) -> bool:
#         return isinstance(self.item, Literal)
#
#     def is_identifier(self) -> bool:
#         return isinstance(self.item, Identifier)
#
#     def is_special(self, special: Optional[SpecialToken] = None) -> bool:
#         if special is None:
#             return isinstance(self.item, SpecialToken)
#         return self.item == special
#
#
# class Literal(NamedTuple):
#     type: DataType
#     value: Any
#
#     def get_value(self) -> DataValue:
#         return DataValue.create(self.type, self.value)
#
# class Identifier(NamedTuple):
#     name: str
#
# class SpecialToken(Enum):
#     StartBlock = auto()
#     EndBlock   = auto()
#     StartArray = auto()
#     EndArray   = auto()
#
#     def __repr__(self) -> str:
#         return f'<{self.__class__.__qualname__}.{self.name}>'


###### Lexer

@runtime_checkable
class Token(Protocol):
    text: str

class Delimiter(Enum):
    StartBlock = r'{'
    EndBlock   = r'}'
    StartArray = r'\['
    EndArray   = r'\]'

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

    @property
    def pattern(self) -> str:
        return self.value

class DelimiterToken(NamedTuple):
    text: str
    delim: Delimiter

class OperatorToken(NamedTuple):
    text: str
    operator: Operator

class Literal(Enum):
    Bool    = r'true|false'
    Integer = r'[+-]?[0-9]+(?!\.)'
    Float   = r'[+-]?([0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)'
    String  = r'\'.*?\'|".*?"'

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

    @property
    def pattern(self) -> str:
        return self.value

class LiteralToken(NamedTuple):
    text: str
    literal: Literal

class IdentifierToken(NamedTuple):
    text: str

class TokenData(NamedTuple):
    """Output data type from the Lexer."""
    token: Token
    lineno: int
    lexpos: int

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

    tokens = (
        ## Specials
        *(delim.name for delim in Delimiter),

        ## Literals
        *(lit.name for lit in Literal),

        ## Operators
        *(op.name for op in Operator),

        ## Identifiers
        'Identifier',
    )

    t_ignore = string.whitespace
    t_ignore_comment = r'//.*'

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # Error handling rule
    def t_error(self, t):
        # raise ScriptError(f"Illegal character '{t.value[0]}'")
        print(f"Illegal character '{t.value[0]}'")
        t.lexer.skip(1)

    def __init__(self, _copy = None, **kwargs):
        if _copy is not None:
            self._lexer = _copy.clone()
        else:
            self._lexer = lex.lex(object=self, **kwargs)

    def clone(self) -> Lexer:
        return Lexer(self._lexer)

    def input(self, text: str) -> None:
        self._lexer.input(text)

    def get_tokens(self) -> Iterator[TokenData]:
        """Iterate through (token, lineno, lexpos) tuples."""
        for t in self._lexer:
            yield TokenData(t.value, t.lineno, t.lexpos)

## Lexing rules
## The order here is important, it defines the rule precedence

# creating a class for this avoids issues with closures
class TokenHandler:
    def __init__(self, name: str, pattern: str, ctor: Callable, *data: Any):
        self.name = name
        self.pattern = pattern
        self.ctor = ctor
        self.data = data

    def __call__(self, t):
        return self.ctor(t.value, *self.data)

    def add_handler(self, lex_cls: Type[Lexer]) -> None:
        @lex.TOKEN(self.pattern)
        def wrapped(lexer, t):
            t.value = self(t)
            return t
        setattr(lex_cls, 't_' + self.name, wrapped)

## Delimiters
for delim in Delimiter:
    handler = TokenHandler(delim.name, delim.pattern, DelimiterToken, delim)
    handler.add_handler(Lexer)

## Literals
for lit in Literal:
    handler = TokenHandler(lit.name, lit.pattern, LiteralToken, lit)
    handler.add_handler(Lexer)

## Operators
for op in Operator:
    handler = TokenHandler(op.name, op.pattern, OperatorToken, op)
    handler.add_handler(Lexer)

## Identifiers
@lex.TOKEN(r'[a-zA-Z_][a-zA-Z0-9_]*')
def t_Identifier(self, t):
    reserved = self.reserved.get(t.value)
    if reserved is not None:
        t.value = OperatorToken(t.value, reserved)
    else:
        t.value = IdentifierToken(t.value)
    return t
Lexer.t_Identifier = t_Identifier



###### Parser


# class Parser:
#     _matching = {
#         SpecialToken.StartBlock : SpecialToken.EndBlock,
#         SpecialToken.StartArray : SpecialToken.EndArray,
#     }
#     _literal = {
#         SpecialToken.StartBlock : DataType.Block,
#         SpecialToken.StartArray : DataType.Array,
#     }
#
#     def __init__(self, lexer: Optional[Lexer] = None):
#         self.lexer = lexer or Lexer()
#
#     def clone(self) -> Parser:
#         return Parser(self.lexer.clone())
#
#     def input(self, text: str) -> None:
#         self.lexer.input(text)
#
#     @staticmethod
#     def _get_next(tokens: Iterable[Token]) -> Optional[Token]:
#         try:
#             return next(tokens)
#         except StopIteration:
#             return None
#
#     def get_tokens(self) -> Iterator[Token]:
#         tokens = self.lexer.get_tokens()
#         while (token := self._get_next(tokens)) is not None:
#             if token.is_special():
#                 literal = self._parse_recursive(tokens, token.item)
#                 token = Token(item=literal, text=token.text, lineno=token.lineno, lexpos=token.lexpos)
#             yield token
#
#     # parse a nested structure down to a single block or array literal token
#     def _parse_recursive(self, tokens: Iteratable[Token], parse_type: SpecialToken) -> Literal:
#         matching_end = self._matching[parse_type]
#
#         content = []
#         while True:
#             token = self._get_next(tokens)
#             if token is None:
#                 raise ScriptError(f"could not find matching {matching_end}")
#
#             if token.is_special(matching_end):
#                 return Literal(self._literal[parse_type], tuple(content))
#
#             elif token.is_special():
#                 if token.item not in self._matching:
#                     raise ScriptError('mismatched', token)
#                 literal = self._parse_recursive(tokens, token.item)
#                 token = Token(item=literal, text=token.text, lineno=token.lineno, lexpos=token.lexpos)
#
#             content.append(token)



if __name__ == '__main__':
    tests = [
        "'dsds' +2.4 576 { true} foobar xor \"false\" '?' + + while [  + -.333 -] if ** ",
        "1 1+ > > > < < < not ! ~ ",
        # "1 1+ >> > [ < <<  { not ! ] ~ }",
        "1 [1+ { >> > < } [< <] not ! ~ ",
    ]

    for test in tests:
        print(test)
        lexer = Lexer()
        lexer.input(test)
        tokens = list(lexer.get_tokens())
        for token in tokens:
            print(token)

        # parser = Parser(lexer)
        # parser.input(test)
        # for tok in parser.get_tokens():
        #     print(repr(tok), repr(str(tok)))