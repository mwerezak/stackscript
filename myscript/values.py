""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from enum import Enum, auto
from functools import total_ordering
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, NamedTuple, TypeVar, Generic, Protocol, runtime_checkable

from typing import Union, Sequence, MutableSequence

from myscript.lang import DataType

if TYPE_CHECKING:
    from typing import Any, Callable
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



@_data(DataType.Bool)
class BoolValue(DataValue[bool]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        return 'true' if self.value else 'false'

@_data(DataType.Number)
class NumberValue(DataValue[Union[int, float]]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        return str(self.value)

@_data(DataType.String)
class StringValue(DataValue[str]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        return repr(self.value)

@_data(DataType.Array)
class ArrayValue(DataValue[MutableSequence[DataValue]]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        content = ' '.join(value.format() for value in self.value)
        return '[' + content + ']'

@_data(DataType.Block)
class BlockValue(DataValue[Sequence['Token']]):
    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self.value!r})'

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        content = ' '.join(token.text for token in self.value)
        return '{ ' + content + ' }'

