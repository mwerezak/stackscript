from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    pass


class Operand(Enum):
    """Each data value has an Operand type that is used to resolve operator overloading."""
    Nil         = auto()
    Bool        = auto()
    Number      = auto()
    String      = auto()
    Array       = auto()
    Block       = auto()

    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'


class OperatorInfo(NamedTuple):
    operator: str
    pattern: str

class Operator(Enum):
    value: OperatorInfo

    Invert  = OperatorInfo('~', r'~')    # bitwise not, array dump
    Inspect = OperatorInfo('`', r'`')
    Eval    = OperatorInfo('!', r'!')

    # Rotate  = OperatorInfo(r'@')    # move the ith stack element to top
    Dup     = OperatorInfo('..', r'\.\.')   # copy the top element.
    Drop    = OperatorInfo(',', r',')    # remove the top element from the stack
    Break   = OperatorInfo(';', r';')    # empty the stack (should this even be an operator?)

    Assign  = OperatorInfo(':', r':')

    Add     = OperatorInfo('+',  r'\+(?!\+)')   # add, concat
    Sub     = OperatorInfo('-',  r'-')    # subtract, set diff
    Mul     = OperatorInfo('*',  r'\*(?!\*)')   # mult, block execute times, array repeat
    Div     = OperatorInfo('/',  r'/')    # div, compose
    Mod     = OperatorInfo('%',  r'%')    # mod, eval
    Pow     = OperatorInfo('**', r'\*\*')

    BitOr   = OperatorInfo('|',  r'\|')   # bitwise/setwise or
    BitAnd  = OperatorInfo('&',  r'&')    # bitwise/setwise and
    BitXor  = OperatorInfo('^',  r'\^')   # bitwise/setwise xor
    LShift  = OperatorInfo('<<', r'<<')
    RShift  = OperatorInfo('>>', r'>>')

    LT      = OperatorInfo('<',  r'<(?![<=])') # less than, elements less than index
    LE      = OperatorInfo('<=', r'<=')     # less than or equal to
    GT      = OperatorInfo('>',  r'>(?![>=])') # greater than, elements greater than or equal to index
    GE      = OperatorInfo('>=', r'>=')     # greater than or equal to
    NE      = OperatorInfo('~=', r'~=')
    Equal   = OperatorInfo('=',  r'=')      # equal to, element at index

    # Append  = OperatorInfo('++', r'\+\+')   # insert element into array
    # Decons  = OperatorInfo('--', r'--')     #
    Index   = OperatorInfo('$',  r'\$')     # take the i-th element from an array or string
    Size    = OperatorInfo('#',  r'\#')
    Collect = OperatorInfo('<<', r'<<')

    Not     = OperatorInfo('not', r'not')
    And     = OperatorInfo('and', r'and')
    Or      = OperatorInfo('or',  r'or')

    If      = OperatorInfo('if',    r'if')
    Do      = OperatorInfo('do',    r'do')
    While   = OperatorInfo('while', r'while')


    def __repr__(self) -> str:
        return f'<{self.__class__.__qualname__}.{self.name}>'

    def __str__(self) -> str:
        return self.value.operator

    @property
    def pattern(self) -> str:
        return self.value.pattern


