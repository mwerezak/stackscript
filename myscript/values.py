""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from functools import total_ordering
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Generic

from typing import Union, Iterator, Iterable, Sequence

from myscript.lang import DataType

if TYPE_CHECKING:
    from typing import Any
    from myscript.parser import Token
    

_DATA_TYPES = {}

def _data(type: DataType):
    def decorator(cls):
        cls._type = type
        _DATA_TYPES[type] = cls
        return cls
    return decorator


_VT = TypeVar('_VT')

class DataValue(ABC, Generic[_VT]):
    _type: DataType

    def __init__(self, value: _VT):
        self._value = value

    @property
    def type(self) -> DataType:
        return self._type

    @property
    def value(self) -> _VT:
        return self._value

    @abstractmethod
    def format(self) -> str:
        ...

    def __repr__(self) -> str:
        return f'<Value({self.type.name}: {self._value!r})>'

    def __str__(self) -> str:
        return self.format()

    @staticmethod
    def create(type: DataType, value: Any) -> DataValue:
        return _DATA_TYPES[type](value)

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: DataValue) -> bool:
        return self.value == other.value


@_data(DataType.Bool)
class BoolValue(DataValue[bool]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        return 'true' if self.value else 'false'

    def __bool__(self) -> bool:
        return self.value

    def __eq__(self, other: DataValue) -> bool:
        return self.value == bool(other)

@total_ordering
@_data(DataType.Number)
class NumberValue(DataValue[Union[int, float]]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        return str(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __lt__(self, other: DataValue) -> bool:
        return self.value < other.value


@_data(DataType.String)
class StringValue(DataValue[str]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        return repr(self.value)

    def __len__(self) -> int:
        return len(self.value)

    def __iter__(self) -> Iterator[StringValue]:
        for ch in self.value:
            yield StringValue(ch)

    def __hash__(self) -> int:
        return hash(self.value)


@_data(DataType.Array)
class ArrayValue(DataValue[Sequence[DataValue]]):
    def __init__(self, value: Iterable[DataValue]):
        super().__init__(tuple(value))

    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        content = ' '.join(value.format() for value in self.value)
        return '[' + content + ']'

    def __len__(self) -> int:
        return len(self.value)

    def __iter__(self) -> Iterator[DataValue]:
        return iter(self.value)

    def unpack(self) -> Iterator[Any]:
        for item in self:
            yield item.value

@_data(DataType.Block)
class BlockValue(DataValue[Sequence['Token']]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        content = ' '.join(token.text for token in self.value)
        return '{ ' + content + ' }'

    def __iter__(self) -> Iterator['Token']:
        return iter(self.value)