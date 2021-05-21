""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

from warnings import warn
from typing import TYPE_CHECKING

from myscript.lang import Operator, DataType

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
    return decorator


@_operator_func(Operator.Add)
def add(ctx: ContextFrame) -> None:
    args = [
        ctx.pop_stack(),
        ctx.pop_stack(),
    ]
    print(args)
    ctx.push_stack(args[0] + args[1])