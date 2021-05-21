""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    pass


class DataType(Enum):
    """Data are things that can be pushed onto the stack."""
    Bool        = auto()
    Number      = auto()
    String      = auto()
    Array       = auto()
    Block       = auto()
    Error       = auto()

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

class DataValue(NamedTuple):
    type: DataType
    value: Any

    def __repr__(self) -> str:
        return f'<Value({self.type.name}: {self.value!r})>'

    def __str__(self) -> str:
        return str(self.value)



class OperatorDef(NamedTuple):
    token: str

class Operator(Enum):
    Invert  = OperatorDef(r'~')    # bitwise not, array dump
    Inspect = OperatorDef(r'`')
    Call    = OperatorDef(r'!')    # evaluate a block or string and push results onto the stack
    Rotate  = OperatorDef(r'@')    # move the ith stack element to top
    Index   = OperatorDef(r'\$')   # copy the ith stack element to top
    Add     = OperatorDef(r'\+(?!\+)')   # add, concat
    Sub     = OperatorDef(r'-')    # subtract, set diff
    Mul     = OperatorDef(r'\*(?!\*)')   # mult, block execute times, array repeat, join, fold
    Div     = OperatorDef(r'/')    # div, split, split in groups of size, unfold, each
    Mod     = OperatorDef(r'%')    # mod, map, every ith element, clean split
    BitOr   = OperatorDef(r'\|')   # bitwise/setwise or
    BitAnd  = OperatorDef(r'&')    # bitwise/setwise and
    BitXor  = OperatorDef(r'\^')   # bitwise/setwise xor
    Swap    = OperatorDef(r'\\')
    Assign  = OperatorDef(r':')
    Less    = OperatorDef(r'<')    # less than, elements less than index
    Greater = OperatorDef(r'>')    # greater than, elements greater than or equal to index
    Equal   = OperatorDef(r'=')    # equal to, element at index
    Size    = OperatorDef(r'\#')
    Dup     = OperatorDef(r'\.')
    Pow     = OperatorDef(r'\*\*')
    Dec     = OperatorDef(r'--')   # deincrement, left uncons
    Inc     = OperatorDef(r'\+\+') # increment, right uncons
    Not     = OperatorDef(r'not')
    And     = OperatorDef(r'and')
    Or      = OperatorDef(r'or')
    Xor     = OperatorDef(r'xor')
    Do      = OperatorDef(r'do')
    While   = OperatorDef(r'while')
    Until   = OperatorDef(r'until')
    If      = OperatorDef(r'if')

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

    @property
    def token(self) -> str:
        return self.value.token


COERCION_PRIORITY = [
    DataType.Bool   : 0,
    DataType.Number : 1,
    DataType.String : 2,
    DataType.Array  : 3,
    DataType.Block  : 4,
    DataType.Error  : 5,  # errors turn everything they touch into an error
]
