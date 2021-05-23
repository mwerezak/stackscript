""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    pass


class Operand(Enum):
    """Each data value has an Operand type that is used to resolve operator overloading."""
    Bool        = auto()
    Number      = auto()
    String      = auto()
    Array       = auto()
    Block       = auto()

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'


class OperatorInfo(NamedTuple):
    pattern: str

class Operator(Enum):
    Invert  = OperatorInfo(r'~')    # bitwise not, array dump
    Inspect = OperatorInfo(r'`')
    Invoke  = OperatorInfo(r'!')    # evaluate a block or string and push results onto the stack

    # Rotate  = OperatorInfo(r'@')    # move the ith stack element to top
    Dup     = OperatorInfo(r'\.')   # copy the top element. equivalent to 0$
    Drop    = OperatorInfo(r',')    # remove the top element from the stack
    Break   = OperatorInfo(r';')    # empty the stack (should this even be an operator?)

    Assign  = OperatorInfo(r':')

    Add     = OperatorInfo(r'\+(?!\+)')   # add, concat
    Sub     = OperatorInfo(r'-')    # subtract, set diff
    Mul     = OperatorInfo(r'\*(?!\*)')   # mult, block execute times, array repeat
    Div     = OperatorInfo(r'/')    # div, split, split in groups of size, unfold, each
    Mod     = OperatorInfo(r'%')    # mod, map, every ith element, clean split
    Pow     = OperatorInfo(r'\*\*')

    BitOr   = OperatorInfo(r'\|')   # bitwise/setwise or
    BitAnd  = OperatorInfo(r'&')    # bitwise/setwise and
    BitXor  = OperatorInfo(r'\^')   # bitwise/setwise xor
    LShift  = OperatorInfo(r'<<')
    RShift  = OperatorInfo(r'>>')

    LT      = OperatorInfo(r'<(?![<=])') # less than, elements less than index
    LE      = OperatorInfo(r'<=')     # less than or equal to
    GT      = OperatorInfo(r'>(?![>=])') # greater than, elements greater than or equal to index
    GE      = OperatorInfo(r'>=')     # greater than or equal to
    NE      = OperatorInfo(r'~=')
    Equal   = OperatorInfo(r'=')      # equal to, element at index

    Append  = OperatorInfo(r'\+\+')   # array add/concat
    Decons  = OperatorInfo(r'--')     # array remove/diff
    Index   = OperatorInfo(r'\$')     # take the i-th element from an array or string
    Size    = OperatorInfo(r'\#')

    Not     = OperatorInfo(r'not')
    And     = OperatorInfo(r'and')
    Or      = OperatorInfo(r'or')

    If      = OperatorInfo(r'if')
    Do      = OperatorInfo(r'do')
    While   = OperatorInfo(r'while')


    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

    @property
    def pattern(self) -> str:
        return self.value.pattern


