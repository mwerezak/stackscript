""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from enum import Enum, auto
from functools import total_ordering
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from typing import Any, Union, Callable, Sequence, MutableSequence
    from myscript.parser import Token


def _format_bool(b: bool) -> str:
    return 'true' if b else 'false'

def _format_array(array: MutableSequence['DataValue']) -> str:
    return '['+ ' '.join(v.format_value() for v in array) + ']'

def _format_block(block: Sequence[Token]) -> str:
    return '{ '+ ' '.join(t.text for t in block) + ' }'


class DataDef(NamedTuple):
    pass

class DataType(Enum):
    """Data are things that can be pushed onto the stack."""
    Bool        = auto()
    Number      = auto()
    String      = auto()
    Array       = auto()
    Block       = auto()

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

    @property
    def format(self) -> Callable[[Any], str]:
        return self.value.format


class OperatorDef(NamedTuple):
    pattern: str

class Operator(Enum):
    Invert  = OperatorDef(r'~')    # bitwise not, array dump
    Inspect = OperatorDef(r'`')
    Eval    = OperatorDef(r'!')    # evaluate a block or string and push results onto the stack
    Rotate  = OperatorDef(r'@')    # move the ith stack element to top
    Index   = OperatorDef(r'\$')   # copy the ith stack element to top
    Dup     = OperatorDef(r'\.')   # copy the top element. equivalent to 0$
    Drop    = OperatorDef(r',')    # remove the top element from the stack
    Break   = OperatorDef(r';')    # empty the stack

    Assign  = OperatorDef(r':')

    Add     = OperatorDef(r'\+(?!\+)')   # add, concat
    Sub     = OperatorDef(r'-')    # subtract, set diff
    Mul     = OperatorDef(r'\*(?!\*)')   # mult, block execute times, array repeat
    Div     = OperatorDef(r'/')    # div, split, split in groups of size, unfold, each
    Mod     = OperatorDef(r'%')    # mod, map, every ith element, clean split

    Pow     = OperatorDef(r'\*\*')

    BitOr   = OperatorDef(r'\|')   # bitwise/setwise or
    BitAnd  = OperatorDef(r'&')    # bitwise/setwise and
    BitXor  = OperatorDef(r'\^')   # bitwise/setwise xor
    # LShift  = OperatorDef(r'<<')
    # RShift  = OperatorDef(r'>>')

    Size    = OperatorDef(r'\#')

    LT      = OperatorDef(r'<(?!<)') # less than, elements less than index
    LE      = OperatorDef(r'<=')     # less than or equal to
    GT      = OperatorDef(r'>(?!>)') # greater than, elements greater than or equal to index
    GE      = OperatorDef(r'>=')     # greater than or equal to
    Equal   = OperatorDef(r'=')      # equal to, element at index
    # Dec     = OperatorDef(r'--')   # deincrement, left uncons
    # Inc     = OperatorDef(r'\+\+') # increment, right uncons

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
    def pattern(self) -> str:
        return self.value.pattern


