from __future__ import annotations

from functools import total_ordering
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Protocol, runtime_checkable

from typing import Generic, Sequence, MutableSequence  # for generic type declaration
from stackscript.parser import ScriptSymbol
from stackscript.operators.defines import Operand
from stackscript.exceptions import ScriptIndexError

if TYPE_CHECKING:
    from typing import Any, Optional, Iterator, Iterable, ClassVar
    from stackscript.runtime import ContextFrame


_VT = TypeVar('_VT')

class DataValue(ABC, Generic[_VT]):
    __slots__ = 'value'

    @property
    @abstractmethod
    def optype(self) -> Operand: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    value: _VT

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

@runtime_checkable
class ContainerValue(Protocol):
    def __contains__(self, item: DataValue) -> bool: ...

    def __iter__(self) -> Iterator[DataValue]: ...

    def __getitem__(self, idx: int) -> DataValue: ...

## WIP. Will be used with table lookups, like in Lua
class NilValue(DataValue[None]):
    name = 'nil'
    optype = Operand.Nil
    value = None

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
        return self.value

    def __eq__(self, other: DataValue) -> bool:
        return self.value == bool(other)

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
        return str(self.value)

    def __lt__(self, other: DataValue) -> bool:
        return self.value < other.value

    def as_index(self) -> int:
        """convert from 1-indexing to 0-indexing."""
        if self.value < 0:
            return self.value
        if self.value > 0:
            return self.value - 1
        raise ValueError('invalid index value')

@total_ordering
class FloatValue(DataValue[float]):
    name = 'float'
    optype = Operand.Number

    value: float
    def __init__(self, value: float):
        self.value = float(value)

    def format(self) -> str:
        return str(self.value)

    def __lt__(self, other: DataValue) -> bool:
        return self.value < other.value


class StringValue(DataValue[str]):
    name = 'string'
    optype = Operand.String

    value: str
    def __init__(self, value: str):
        self.value = value

    def format(self) -> str:
        return repr(self.value)

    def __len__(self) -> int:
        return len(self.value)

    def __contains__(self, item: DataValue) -> bool:
        if isinstance(item, StringValue):
            return item.value in self.value
        return False

    def __iter__(self) -> Iterator[StringValue]:
        for ch in self.value:
            yield StringValue(ch)

    def __getitem__(self, idx: int) -> StringValue:
        return StringValue(self.value[idx])


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
        return len(self.value)

    def __contains__(self, item: DataValue) -> bool:
        return item in self.value

    def __iter__(self) -> Iterator[DataValue]:
        return iter(self.value)

    def __hash__(self) -> int:
        return hash(id(self.value))

    # being mutable, Arrays are only equal if they reference the same sequence instance
    def __eq__(self, other: DataValue) -> bool:
        if isinstance(other, ArrayValue):
            return self.value is other.value
        return False

    def __getitem__(self, index: IntValue) -> DataValue:
        if index.value == 0:
            raise ScriptIndexError('0 is not a valid index', self, index)
        try:
            return self.value[index.as_index()]
        except IndexError:
            raise ScriptIndexError('index out of range', self, index) from None

    def __setitem__(self, index: IntValue, value: DataValue) -> None:
        if index.value == 0:
            raise ScriptIndexError('0 is not a valid index', self, index)
        try:
            self.value[index.as_index()] = value
        except IndexError:
            raise ScriptIndexError('index out of range', self, index) from None

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
        return len(self.value)

    def __contains__(self, item: DataValue) -> bool:
        return item in self.value

    def __iter__(self) -> Iterator[DataValue]:
        return iter(self.value)

    def __getitem__(self, index: IntValue) -> DataValue:
        if index.value == 0:
            raise ScriptIndexError('0 is not a valid index', self, index)
        try:
            return self.value[index.as_index()]
        except IndexError:
            raise ScriptIndexError('index out of range', self, index) from None


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


###### Pseudo Data Values - these should only ever appear inside a block assignment context

@runtime_checkable
class BindingTarget(Protocol):
    def bind_value(self, ctx: ContextFrame, value: DataValue) -> None: ...
    def resolve_value(self) -> DataValue: ...

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
    optype = Operand.Name
    value = None

    def __init__(self, array: ArrayValue, index: IntValue):
        self.array = array
        self.index = index

    def format(self) -> str:
        return f'{self.array.format()} {self.index.format()} $'

    def bind_value(self, ctx: ContextFrame, value: DataValue) -> None:
        self.array[self.index] = value

    def resolve_value(self) -> DataValue:
        return self.array[self.index]

## Another pseudo data value, also used for block assignment
class NameValue(DataValue[str]):
    name = 'name'
    optype = Operand.Name
    value = None

    def __init__(self, ctx: ContextFrame, value: str):
        self.ctx = ctx
        self.value = value

    def format(self) -> str:
        return self.value

    def bind_value(self, ctx: ContextFrame, dvalue: DataValue) -> None:
        ctx.namespace_bind_value(self.value, dvalue)

    def resolve_value(self) -> DataValue:
        return self.ctx.namespace_lookup(self.value)