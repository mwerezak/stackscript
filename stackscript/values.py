from __future__ import annotations

from functools import total_ordering
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar

from typing import Generic, Sequence, MutableSequence  # for generic type declaration
from stackscript.parser import ScriptSymbol
from stackscript.operators.defines import Operand

if TYPE_CHECKING:
    from typing import Any, Iterator, Iterable, ClassVar


_VT = TypeVar('_VT')

class DataValue(ABC, Generic[_VT]):
    __slots__ = '_value'

    @property
    @abstractmethod
    def optype(self) -> Operand: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    value: _VT
    @property
    @abstractmethod
    def value(self) -> _VT: ...

    @abstractmethod
    def format(self) -> str:
        """Format the DataValue in a way that produces valid script code which evalutes to the value."""

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.value!r})>'

    def __str__(self) -> str:
        return self.format()

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: DataValue) -> bool:
        return self.value == other.value


## WIP. Will be used with table lookups, like in Lua
class NilValue(DataValue[None]):
    name = 'nil'
    optype = Operand.Nil

    @property
    def value(self) -> NilValue:
        return None

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    def format(self) -> str:
        return 'nil'

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: DataValue) -> bool:
        return False

NilValue = NilValue()


class BoolValue(DataValue[bool]):
    TRUE: ClassVar[BoolValue]
    FALSE: ClassVar[BoolValue]

    name = 'bool'
    optype = Operand.Bool

    value: bool
    def __init__(self, value: bool):
        self.value = value

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

    value: int
    def __init__(self, value: float):
        self.value = int(value)

    def format(self) -> str:
        return str(self._value)

    def __lt__(self, other: DataValue) -> bool:
        return self._value < other.value

@total_ordering
class FloatValue(DataValue[float]):
    name = 'float'
    optype = Operand.Number

    value: float
    def __init__(self, value: float):
        self.value = float(value)

    def format(self) -> str:
        return str(self._value)

    def __lt__(self, other: DataValue) -> bool:
        return self._value < other.value


class StringValue(DataValue[str]):
    name = 'string'
    optype = Operand.String

    value: str
    def __init__(self, value: str):
        self.value = value

    def format(self) -> str:
        return repr(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __contains__(self, item: DataValue) -> bool:
        if isinstance(item, StringValue):
            return item._value in self._value
        return False

    def __iter__(self) -> Iterator[StringValue]:
        for ch in self._value:
            yield StringValue(ch)

    def __getitem__(self, idx: int) -> StringValue:
        return StringValue(self._value[idx])


class ArrayValue(DataValue[MutableSequence[DataValue]]):
    name = 'array'
    optype = Operand.Array

    value: MutableSequence[DataValue]
    def __init__(self, value: Iterable[DataValue]):
        self.value = list(value)

    def format(self) -> str:
        content = ' '.join(value.format() for value in self.value)
        return '[' + content + ']'

    def __len__(self) -> int:
        return len(self._value)

    def __contains__(self, item: DataValue) -> bool:
        return item in self._value

    def __iter__(self) -> Iterator[DataValue]:
        return iter(self._value)

    def __getitem__(self, idx: int) -> DataValue:
        return self._value[idx]

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


# similar to arrays, but immutable
class TupleValue(DataValue[Sequence[DataValue]]):
    name = 'tuple'
    optype = Operand.Array

    value: Sequence[DataValue]
    def __init__(self, value: Iterable[DataValue]):
        self.value = tuple(value)

    def format(self) -> str:
        content = ' '.join(value.format() for value in self.value)
        return '(' + content + ')'

    def __len__(self) -> int:
        return len(self._value)

    def __contains__(self, item: DataValue) -> bool:
        return item in self._value

    def __iter__(self) -> Iterator[DataValue]:
        return iter(self._value)

    def __getitem__(self, idx: int) -> DataValue:
        return self._value[idx]

    def unpack(self) -> Iterator[Any]:
        for item in self:
            yield item.value


class BlockValue(DataValue[Sequence[ScriptSymbol]]):
    name = 'block'
    optype = Operand.Block

    value: Sequence[ScriptSymbol]
    def __init__(self, value: Iterable[ScriptSymbol]):
        self.value = tuple(value)

    def format(self) -> str:
        content = ' '.join(sym.meta.text for sym in self.value)
        return '{ ' + content + ' }'

    def __iter__(self) -> Iterator[ScriptSymbol]:
        return iter(self.value)


## Pseudo data value
## WIP. Will be used to handle array/table assignment syntax, e.g:
## >>> n: 2;
## >>> somevalue: 42;
## >>> [ 2 3 4 5 6 ]: array;
## >>> somevalue: {array n$};  // will ever only exist in this context
## >>> array
## [2 42 4 5 6]
##
class IndexValue(DataValue[None]):
    name = 'index'

    def __init__(self, container: DataValue, key: DataValue):
        self.container = container
        self.key = key

    @property
    def optype(self) -> Operand:
        return self.value.optype

    @property
    def value(self) -> Any:
        return None

    def format(self) -> str:
        return f'{self.container.format()} {self.key.format()} $'