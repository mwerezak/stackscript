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
    from typing import Any, Union, Optional, Type, Iterator, Iterable, Callable, Mapping


###### Lexer

if TYPE_CHECKING:
    TokenData = Union['DelimiterToken', 'OperatorToken', 'PrimitiveLiteralToken', 'IdentifierToken']

# @runtime_checkable
# class TokenData(Protocol):
#     text: str

class Token(NamedTuple):
    data: TokenData
    lineno: int
    lexpos: int

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

class PrimitiveLiteral(Enum):
    Bool    = r'true|false'
    Integer = r'[+-]?[0-9]+(?!\.)'
    Float   = r'[+-]?([0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)'
    String  = r'\'.*?\'|".*?"'

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

    @property
    def pattern(self) -> str:
        return self.value

## Primitive Literals
class PrimitiveToken(NamedTuple):
    text: str
    literal: PrimitiveLiteral

class IdentifierToken(NamedTuple):
    text: str


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
        *(lit.name for lit in PrimitiveLiteral),

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

    def get_tokens(self) -> Iterator[Token]:
        for t in self._lexer:
            yield Token(t.value, t.lineno, t.lexpos)

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
for lit in PrimitiveLiteral:
    handler = TokenHandler(lit.name, lit.pattern, PrimitiveToken, lit)
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
        # noinspection PyTypeChecker
        t.value = OperatorToken(t.value, reserved)
    else:
        # noinspection PyTypeChecker
        t.value = IdentifierToken(t.value)
    return t
Lexer.t_Identifier = t_Identifier



###### Parser

# Note: all ScriptSymbol types must be IMMUTABLE!

@runtime_checkable
class ScriptSymbol(Protocol):
    meta: SymbolMeta

@dataclass
class SymbolMeta:
    text: str
    pos: int
    lineno: int

    # if this is part of a opening/closing delimiter pair
    opening: Optional[SymbolMeta] = None
    closing: Optional[SymbolMeta] = None

class Identifier(NamedTuple):
    name: str
    meta: SymbolMeta

# closely related to but distinct from the set of data types
class LiteralType(Enum):
    Bool   = auto()
    Number = auto()
    String = auto()
    Array  = auto()
    Block  = auto()

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

class Literal(NamedTuple):
    type: LiteralType
    value: Any  ## MUST BE IMMUTABLE
    meta: SymbolMeta

class OperatorSym(NamedTuple):
    operator: Operator
    meta: SymbolMeta

_SYM_TYPES = (
    Identifier,
    Literal,
    OperatorSym,
)

class Parser:
    _delimiters = {
        Delimiter.StartBlock : Delimiter.EndBlock,
        Delimiter.StartArray : Delimiter.EndArray,
    }

    _parse_tokens: Mapping[Type[TokenData], Callable[[Iterator[Token], TokenData, SymbolMeta], ScriptSymbol]]
    _parse_primitives: Mapping[PrimitiveLiteral, Callable[[TokenData, SymbolMeta], Literal]]

    def __init__(self):
        self._parse_tokens = {
            DelimiterToken  : self._parse_delimiter,
            OperatorToken   : self._parse_operator,
            PrimitiveToken  : self._parse_primitive,
            IdentifierToken : self._parse_identifier,
        }

        self._parse_primitives = {
            PrimitiveLiteral.Bool    : self._parse_bool,
            PrimitiveLiteral.Float   : self._parse_float,
            PrimitiveLiteral.Integer : self._parse_int,
            PrimitiveLiteral.String  : self._parse_string,
        }

    _tokens: Iterator[Token]
    def input(self, tokens: Iterable[Token]) -> None:
        self._tokens = iter(tokens)

    def get_symbols(self) -> Iterator[ScriptSymbol]:
        for token in self._tokens:
            yield self._parse_token(token)

    def _create_meta(self, token: Token) -> SymbolMeta:
        return SymbolMeta(
            text = token.data.text,
            pos = token.lexpos,
            lineno = token.lineno,
        )

    def _parse_token(self, token: Token) -> ScriptSymbol:
        meta = self._create_meta(token)
        for toktype, fparse in self._parse_tokens.items():
            if isinstance(token.data, toktype):
                return fparse(self._tokens, token.data, meta)
        raise NotImplementedError('no method to parse token: ' + repr(token))

    def _parse_operator(self, tokens: Iterator[Token], tokdata: OperatorToken, meta: SymbolMeta) -> OperatorSym:
        return OperatorSym(tokdata.operator, meta)

    def _parse_identifier(self, tokens: Iterator[Token], tokdata: IdentifierToken, meta: SymbolMeta) -> Identifier:
        return Identifier(tokdata.text, meta)

    def _parse_primitive(self, tokens: Iterator[Token], tokdata: PrimitiveToken, meta: SymbolMeta) -> Literal:
        return self._parse_primitives[tokdata.literal](tokdata, meta)

    _bool_values = {
        'true'  : True,
        'false' : False,
    }
    def _parse_bool(self, tokdata: PrimitiveToken, meta: SymbolMeta) -> Literal:
        return Literal(LiteralType.Bool, self._bool_values[tokdata.text], meta)

    # todo HEX, OCT, BIN literals
    def _parse_int(self, tokdata: PrimitiveToken, meta: SymbolMeta) -> Literal:
        return Literal(LiteralType.Number, int(tokdata.text), meta)

    def _parse_float(self, tokdata: PrimitiveToken, meta: SymbolMeta) -> Literal:
        return Literal(LiteralType.Number, float(tokdata.text), meta)

    _str_delim = ("'", '"')
    def _parse_string(self, tokdata: PrimitiveToken, meta: SymbolMeta) -> Literal:
        text = tokdata.text
        if text[0] != text[-1] or text[0] not in self._str_delim:
            raise ScriptError('malformed string')
        return Literal(LiteralType.String, text[1:-1], meta)

    _structured_literals = {
        Delimiter.StartArray : LiteralType.Array,
        Delimiter.StartBlock : LiteralType.Block,
    }
    def _parse_delimiter(self, tokens: Iterator[Token], tokdata: DelimiterToken, meta: SymbolMeta) -> ScriptSymbol:
        end_delim = self._delimiters.get(tokdata.delim)
        if end_delim is None:
            raise ScriptError(f"found closing delimiter '{tokdata.delim}' without matching start")

        contents = []
        for token in tokens:
            if not (isinstance(token.data, DelimiterToken) and token.data.delim == end_delim):
                contents.append(self._parse_token(token))
                continue

            closing_meta = self._create_meta(token)
            closing_meta.opening = meta
            meta.closing = closing_meta

            ## for now, all delimiter pairs result in a literal
            literal = self._structured_literals.get(tokdata.delim)
            if literal is not None:
                return Literal(literal, tuple(contents), meta)
            raise NotImplementedError('no method to parse token: ' + repr(token))

        raise ScriptError(f"could not find closing delimiter for '{tokdata.delim}'")


if __name__ == '__main__':
    import traceback

    tests = [
        "'dsds' +2.4 576 { true} foobar xor \"false\" '?' ++ while [  + -.333 -] if ** ",
        "1 1+ > > > <<< not ! ~ ",
        "1 1+ >> > [ < <<  { not ! ] ~ }",
        "1 [1+ { >> > < } [< <] not ! ~ ",
    ]

    for test in tests:
        try:
            print(test)
            lexer = Lexer()
            lexer.input(test)
            tokens = list(lexer.get_tokens())
            # for token in tokens:
            #     print(token)

            parser = Parser()
            parser.input(tokens)
            for sym in parser.get_symbols():
                print(sym)
        except:
            traceback.print_exc()