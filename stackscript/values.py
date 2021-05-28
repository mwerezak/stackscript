from __future__ import annotations

from functools import total_ordering
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Protocol, runtime_checkable

from typing import Generic, Sequence, MutableSequence  # for generic type declaration
from stackscript.parser import ScriptSymbol
from stackscript.operators.defines import Operand
from stackscript.exceptions import ScriptIndexError

if TYPE_CHECKING:
    from typing import Callable, Iterator, Iterable, ClassVar
    from stackscript.runtime import ContextFrame


class ScriptValue(ABC):
    """Abstract base class of all data types."""

    @property
    @abstractmethod
    def optype(self) -> Operand: ...

    @property
    @abstractmethod
    def tpname(self) -> str: ...

    @abstractmethod
    def format(self) -> str:
        """Format the ScriptValue in a way that produces valid script code which evalutes to the value."""

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.format()})>'

    def __str__(self) -> str:
        return self.format()

    def __bool__(self) -> bool:
        return True

    def __eq__(self, other: ScriptValue) -> bool:
        return self is other


###### Primitives

## WIP. May be used with table lookups, like in Lua
## Or maybe not
# class NilValue(ScriptValue):
#     tpname = 'nil'
#     optype = Operand.Nil
#
#     def __repr__(self):
#         return f'<{self.__class__.__name__}>'
#
#     def format(self) -> str:
#         return 'nil'
#
#     def __hash__(self) -> int:
#         return id(self)
#
#     def __bool__(self) -> bool:
#         return False
#
#     def __eq__(self, other) -> bool:
#         return other is self
#
# NilValue = NilValue()


## Value types
_VT = TypeVar('_VT')

class DataValue(ScriptValue, Generic[_VT]):
    __slots__ = 'value'

    value: _VT

    @abstractmethod
    def __init__(self, value: _VT): ...

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: ScriptValue) -> bool:
        if isinstance(other, DataValue):
            return self.value == other.value
        return super().__eq__(other)


class BoolValue(DataValue[bool]):
    TRUE: ClassVar[BoolValue]
    FALSE: ClassVar[BoolValue]

    tpname = 'bool'
    optype = Operand.Bool

    value: bool
    def __init__(self, value: bool):
        self.value = value

    def format(self) -> str:
        return 'true' if self.value else 'false'

    def __bool__(self) -> bool:
        return self.value

    def __eq__(self, other: ScriptValue) -> bool:
        return self.value == bool(other)

    @classmethod
    def get_value(cls, b: bool) -> BoolValue:
        return BoolValue.TRUE if b else BoolValue.FALSE

BoolValue.TRUE  = BoolValue(True)
BoolValue.FALSE = BoolValue(False)


@total_ordering
class IntValue(DataValue[int]):
    tpname = 'int'
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
    tpname = 'float'
    optype = Operand.Number

    value: float
    def __init__(self, value: float):
        self.value = float(value)

    def format(self) -> str:
        return str(self.value)

    def __lt__(self, other: DataValue) -> bool:
        return self.value < other.value

###### Sequences

@runtime_checkable
class SequenceValue(Protocol):
    def __contains__(self, item: ScriptValue) -> bool: ...

    def __iter__(self) -> Iterator[ScriptValue]: ...

    def __getitem__(self, idx: IntValue) -> ScriptValue: ...

class StringValue(DataValue[str], SequenceValue):
    tpname = 'string'
    optype = Operand.String

    value: str
    def __init__(self, value: str):
        self.value = value

    def format(self) -> str:
        return repr(self.value)

    def __len__(self) -> int:
        return len(self.value)

    def __contains__(self, item: ScriptValue) -> bool:
        if isinstance(item, StringValue):
            return item.value in self.value
        return False

    def __iter__(self) -> Iterator[StringValue]:
        for ch in self.value:
            yield StringValue(ch)

    def __getitem__(self, idx: IntValue) -> StringValue:
        if idx.value == 0:
            raise ScriptIndexError('0 is not a valid index', idx, self)
        try:
            return StringValue(self.value[idx.as_index()])
        except IndexError:
            raise ScriptIndexError('index out of range', idx, self) from None


# similar to arrays, but immutable
class TupleValue(DataValue[Sequence[ScriptValue]], SequenceValue):
    tpname = 'tuple'
    optype = Operand.Array

    value: Sequence[ScriptValue]
    def __init__(self, value: Iterable[ScriptValue]):
        self.value = tuple(value)

    def format(self) -> str:
        content = ' '.join(value.format() for value in self.value)
        return '(' + content + ')'

    def __len__(self) -> int:
        return len(self.value)

    def __contains__(self, item: ScriptValue) -> bool:
        return item in self.value

    def __iter__(self) -> Iterator[ScriptValue]:
        return iter(self.value)

    def __getitem__(self, index: IntValue) -> ScriptValue:
        if index.value == 0:
            raise ScriptIndexError('0 is not a valid index', index, self)
        try:
            return self.value[index.as_index()]
        except IndexError:
            raise ScriptIndexError('index out of range', index, self) from None

# arrays cannot be a DataValue because they are mutable
class ArrayValue(ScriptValue, SequenceValue):
    __slots__ = '_contents'

    tpname = 'array'
    optype = Operand.Array

    def __init__(self, contents: Iterable[ScriptValue]):
        self._contents = list(contents)

    def format(self) -> str:
        content = ' '.join(value.format() for value in self._contents)
        return '[' + content + ']'

    def __len__(self) -> int:
        return len(self._contents)

    def __contains__(self, item: ScriptValue) -> bool:
        return item in self._contents

    def __iter__(self) -> Iterator[ScriptValue]:
        return iter(self._contents)

    def __getitem__(self, index: IntValue) -> ScriptValue:
        if index.value == 0:
            raise ScriptIndexError('0 is not a valid index', index, self)
        try:
            return self._contents[index.as_index()]
        except IndexError:
            raise ScriptIndexError('index out of range', index, self) from None

    def __setitem__(self, index: IntValue, value: ScriptValue) -> None:
        if index.value == 0:
            raise ScriptIndexError('0 is not a valid index', index, self)

        # assignment to the end of array
        idx = index.as_index()
        if idx == len(self):
            self._contents.append(value)
            return

        try:
            self._contents[idx] = value
        except IndexError:
            raise ScriptIndexError('index out of range', index, self) from None

    def remove(self, value: ScriptValue) -> bool:
        try:
            self._contents.remove(value)
        except ValueError:
            return False
        return True


###### Executable Values

@runtime_checkable
class CtxExecValue(Protocol):
    def apply_exec(self, ctx: ContextFrame) -> None: ...

class BlockValue(DataValue[Sequence[ScriptSymbol]], CtxExecValue):
    tpname = 'block'
    optype = Operand.Exec

    value: Sequence[ScriptSymbol]
    def __init__(self, value: Iterable[ScriptSymbol]):
        self.value = tuple(value)

    def format(self) -> str:
        content = ' '.join(sym.meta.text for sym in self.value)
        return '{ ' + content + ' }'

    def __iter__(self) -> Iterator[ScriptSymbol]:
        return iter(self.value)

    def apply_exec(self, ctx: ContextFrame) -> None:
        ctx.exec(self)


class BuiltinValue(ScriptValue, CtxExecValue):
    tpname = 'builtin'
    optype = Operand.Exec

    def __init__(self, name: str, exec_func: Callable[[ContextFrame], None]):
        self.name = name
        self.exec_func = exec_func

    def format(self) -> str:
        return f'<{self.tpname}: {self.name}>'

    def apply_exec(self, ctx: ContextFrame) -> None:
        self.exec_func(ctx)



###### Pseudo Data Values - these should only ever appear inside a block assignment context

@runtime_checkable
class BindingTarget(Protocol):
    def bind_value(self, ctx: ContextFrame, value: ScriptValue) -> None: ...
    def resolve_value(self) -> ScriptValue: ...

## Pseudo data value
## WIP. Will be used to handle array/table assignment syntax, e.g:
## >>> n: 2;
## >>> somevalue: 42;
## >>> [ 2 3 4 5 6 ]: array;
## >>> somevalue: {array n$};  // will ever only exist in this context
## >>> array
## [2 42 4 5 6]
##
class IndexValue(ScriptValue, BindingTarget):
    tpname = '_index'
    optype = Operand.Name

    def __init__(self, array: ArrayValue, index: IntValue):
        if index.value == 0:
            raise ScriptIndexError('0 is not a valid index', index, array)
        self.array = array
        self.index = index

    def format(self) -> str:
        return f'{self.array.format()} {self.index.format()} $'

    def bind_value(self, ctx: ContextFrame, value: ScriptValue) -> None:
        self.array[self.index] = value

    def resolve_value(self) -> ScriptValue:
        return self.array[self.index]

## Another pseudo data value, also used for block assignment
class NameValue(ScriptValue, BindingTarget):
    tpname = '_name'
    optype = Operand.Name

    def __init__(self, ctx: ContextFrame, name: str):
        self.ctx = ctx
        self.name = name

    def format(self) -> str:
        return self.name

    def bind_value(self, ctx: ContextFrame, dvalue: ScriptValue) -> None:
        ctx.namespace_bind_value(self.name, dvalue)

    def resolve_value(self) -> ScriptValue:
        return self.ctx.namespace_lookup(self.name)