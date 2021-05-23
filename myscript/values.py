""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from functools import total_ordering
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, overload

from typing import Generic, Sequence, MutableSequence  # for generic type declaration
from myscript.parser import ScriptSymbol
from myscript.opcodes import Operand

if TYPE_CHECKING:
    from typing import Any, Iterator, Iterable, ClassVar


_VT = TypeVar('_VT')

class DataValue(ABC, Generic[_VT]):
    __slots__ = '_value'

    def __init__(self, value: _VT):
        self._value = value

    @property
    @abstractmethod
    def optype(self) -> Operand: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def value(self) -> _VT:
        return self._value

    @abstractmethod
    def format(self) -> str:
        """Format the DataValue in a way that produces valid script code which evalutes to the value."""

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.value!r})>'

    def __str__(self) -> str:
        return self.format()

    def __hash__(self) -> int:
        return hash(self._value)

    def __eq__(self, other: DataValue) -> bool:
        return self._value == other.value

class BoolValue(DataValue[bool]):
    TRUE: ClassVar[BoolValue]
    FALSE: ClassVar[BoolValue]

    name = 'bool'
    optype = Operand.Bool

    def format(self) -> str:
        return 'true' if self.value else 'false'

    def __bool__(self) -> bool:
        return self._value

    def __eq__(self, other: DataValue) -> bool:
        return self._value == bool(other)

    @classmethod
    def get_value(cls, b: bool) -> BoolValue:
        return BoolValue.TRUE if b else BoolValue.FALSE

BoolValue.TRUE  = BoolValue(True)
BoolValue.FALSE = BoolValue(False)


@total_ordering
class IntValue(DataValue[int]):
    name = 'int'
    optype = Operand.Number

    def format(self) -> str:
        return str(self._value)

    def __lt__(self, other: DataValue) -> bool:
        return self._value < other.value

@total_ordering
class FloatValue(DataValue[float]):
    name = 'float'
    optype = Operand.Number

    def format(self) -> str:
        return str(self._value)

    def __lt__(self, other: DataValue) -> bool:
        return self._value < other.value

@overload
def NumberValue(value: int) -> IntValue: ...

@overload
def NumberValue(value: float) -> FloatValue: ...

def NumberValue(value):
    """overloaded constructor that will create IntValue or FloatValue as appropriate"""
    if isinstance(value, int):
        return IntValue(value)
    return FloatValue(value)


class StringValue(DataValue[str]):
    name = 'string'
    optype = Operand.String

    def format(self) -> str:
        return repr(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __iter__(self) -> Iterator[StringValue]:
        for ch in self._value:
            yield StringValue(ch)

class ArrayValue(DataValue[MutableSequence[DataValue]]):
    name = 'array'
    optype = Operand.Array

    def __init__(self, value: Iterable[DataValue]):
        super().__init__(list(value))

    def format(self) -> str:
        content = ' '.join(value.format() for value in self.value)
        return '[' + content + ']'

    def __len__(self) -> int:
        return len(self._value)

    def __iter__(self) -> Iterator[DataValue]:
        return iter(self._value)

    def __hash__(self) -> int:
        return hash(id(self._value))

    # being mutable, Arrays are only equal if they reference the same sequence instance
    def __eq__(self, other: DataValue) -> bool:
        if isinstance(other, ArrayValue):
            return self._value is other._value
        return False

    def unpack(self) -> Iterator[Any]:
        for item in self:
            yield item.value

class BlockValue(DataValue[Sequence[ScriptSymbol]]):
    name = 'block'
    optype = Operand.Block

    def __init__(self, value: Iterable[ScriptSymbol]):
        super().__init__(tuple(value))

    def format(self) -> str:
        content = ' '.join(sym.meta.text for sym in self.value)
        return '{ ' + content + ' }'

    def __iter__(self) -> Iterator[ScriptSymbol]:
        return iter(self.value)
