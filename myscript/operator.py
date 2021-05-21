""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from myscript.lang import Operator, DataType
from myscript.values import BoolValue, NumberValue, StringValue, ArrayValue, BlockValue
from myscript.errors import ScriptError

if TYPE_CHECKING:
    from typing import Any, Callable, Iterator, Sequence, MutableMapping, MutableSequence
    from myscript.values import DataValue
    from myscript.runtime import ContextFrame

    Signature = Sequence[DataType]
    OperatorFunc = Callable[[ContextFrame, ...], Iterator[DataValue]]



# map operator -> arity -> signature -> operator data
OP_REGISTRY: MutableMapping[Operator, MutableSequence[MutableMapping[Signature, 'OperatorData']]] = defaultdict(list)


class OperatorData(NamedTuple):
    op: Operator
    signature: Sequence[DataType]
    func: OperatorFunc


def apply_operator(ctx: ContextFrame, op: Operator) -> None:
    opdata = _search_registery(op, ctx.peek_stack())
    
    args = [ ctx.pop_stack() for i in range(len(opdata.signature)) ]
    args.reverse()

    for value in opdata.func(ctx, *args):
        # print(value)
        ctx.push_stack(value)

def _search_registery(op: Operator, peek: Iterator[DataValue]) -> OperatorData:
    registry = OP_REGISTRY[op]

    args = []
    for nargs, subregistry in enumerate(registry):
        sig = tuple(value.type for value in args)
        if sig in subregistry:
            return subregistry[sig]

        try:
            args.append(next(peek))
        except StopIteration:
            break

    args_msg = '\n'.join(f'[{i}]: {data}' for i, data in enumerate(args)) if len(args) else '[]'
    raise ScriptError(f"Invalid operands for operator '{op.name}':\n{args_msg}")

def _register_operator(opdata: OperatorData) -> None:
    registry = OP_REGISTRY[opdata.op]
    nargs = len(opdata.signature)

    while len(registry) <= nargs:
        registry.append({})

    signature = opdata.signature
    if signature in registry[nargs]:
        raise ValueError(f"signature {signature} is already registered for {opdata.op}")
    registry[nargs][signature] = opdata

def operator_func(op: Operator, *signature: DataType):
    signature = tuple(reversed(signature))

    def decorator(func: OperatorFunc):
        opdata = OperatorData(op, signature, func)
        _register_operator(opdata)
        return func
    return decorator

# register an operator for all possible permutations of args
def operator_coerce(op: Operator, primary: DataType, *secondary: DataType):
    base_sig = [primary, *secondary]
    base_sig.reverse()

    def decorator(func: OperatorFunc):
        for permute in itertools.permutations(range(len(base_sig))):
            signature = tuple(base_sig[i] for i in permute)
            func = _ReorderFunc(func, permute)
            opdata = OperatorData(op, signature, func)
            _register_operator(opdata)
        return func
    return decorator

class _ReorderFunc(NamedTuple):
    func: Callable
    permute: Sequence[int]

    def __call__(self, ctx: ContextFrame, *args: Any) -> Any:
        return self.func(ctx, *( args[i] for i in self.permute ))


## Operator Definitions

###### Invert

# "dump" the array onto the stack
@operator_func(Operator.Invert, DataType.Array)
def operator_invert(ctx, o):
    yield from o.value 

# bitwise not
@operator_func(Operator.Invert, DataType.Number)
def operator_invert(ctx, x):
    yield NumberValue(~x.value)

###### Inspect
@operator_func(Operator.Inspect, DataType.Block)
@operator_func(Operator.Inspect, DataType.Array)
@operator_func(Operator.Inspect, DataType.String)
@operator_func(Operator.Inspect, DataType.Number)
@operator_func(Operator.Inspect, DataType.Bool)
def operator_inspect(ctx, o):
    yield StringValue(o.format())

###### Add

# concatenate arrays
@operator_func(Operator.Add, DataType.Array, DataType.Array)
def operator_add(ctx, a, b):
    yield ArrayValue([*a.value, *b.value])

# append item to end of array
@operator_coerce(Operator.Add, DataType.Array, DataType.String)
@operator_coerce(Operator.Add, DataType.Array, DataType.Number)
@operator_coerce(Operator.Add, DataType.Array, DataType.Bool)
def operator_add(ctx, arr, item):
    arr.value.append(item)
    yield arr

# concatenate strings
@operator_func(Operator.Add, DataType.String, DataType.String)
def operator_add(ctx, a, b):
    yield StringValue(a.value + b.value)

# add numbers
@operator_func(Operator.Add, DataType.Number, DataType.Number)
def operator_add(ctx, a, b):
    yield NumberValue(a.value + b.value)


###### Sub

@operator_func(Operator.Sub, DataType.Number, DataType.Number)
def operator_sub(ctx, a, b):
    yield NumberValue(a.value - b.value)

# print(OP_REGISTRY)