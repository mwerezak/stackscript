""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

from warnings import warn
from typing import TYPE_CHECKING

from myscript.lang import Operator, DataType, DataValue
from myscript.errors import ScriptTypeError

if TYPE_CHECKING:
    from typing import Any, Callable, MutableMapping
    from myscript.runtime import ContextFrame

    OperatorFunc = Callable[[ContextFrame], None]




_op_handlers: MutableMapping[Operator, OperatorFunc] = {}

def apply_operator(ctx: ContextFrame, op: Operator) -> None:
    func = _op_handlers.get(op)
    if func is not None:
        func(ctx)
    else:
        warn(f"no handler for {op}")

def _operator_func(op: Operator):
    def decorator(func: OperatorFunc):
        if op in _op_handlers:
            warn(f"{op} already has a registered handler, overwriting...")
        _op_handlers[op] = func
        return func
    return decorator


@_operator_func(Operator.Add)
def _operator_add(ctx: ContextFrame) -> None:
    args = [
        ctx.pop_stack(),
        ctx.pop_stack(),
    ]
    ctx.push_stack(_add_values(*args))

def _add_values(a: DataValue, b: DataValue) -> DataValue:
    if a.type == b.type and a.type in (DataType.Number, DataType.Array, DataType.String):
        return DataValue(a.type, a.value + b.value)
    raise ScriptTypeError(f"invalid operands '{a}' and '{b}'")


@_operator_func(Operator.Sub)
def _operator_sub(ctx: ContextFrame) -> None:
    args = [
        ctx.pop_stack(),
        ctx.pop_stack(),
    ]
    ctx.push_stack(_sub_values(*args))

def _sub_values(a: DataValue, b: DataValue) -> DataValue:
    if a.type == b.type:
        if a.type == DataType.Number:
            return DataValue(DataType.Number, b.value - a.value)
        if a.type == DataType.Array:
            return DataValue(DataType.Array, [
                item for item in b if item not in a
            ])
    raise ScriptTypeError(f"invalid operands '{a}' and '{b}'")

