""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

import itertools
from functools import wraps
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
OP_REGISTRY: MutableMapping[Operator, MutableSequence[MutableMapping[Signature, OperatorData]]] = defaultdict(list)


class OperatorData(NamedTuple):
    op: Operator
    signature: Sequence[DataType]
    func: OperatorFunc


def apply_operator(ctx: ContextFrame, op: Operator) -> None:
    opdata = _search_registery(op, ctx.iter_stack_reversed())

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
            args.insert(0, next(peek))
        except StopIteration:
            break

    message = "Invalid operands for operator '{op.name}':\n"
    if len(args):
        args_msg = ' '.join(data.format() for data in reversed(args))
        types_msg = ', '.join(data.type.name for data in reversed(args))
        message += f"{{{types_msg}}}: {args_msg}"
    else:
        message += "[]"
    raise ScriptError(message)

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
    def decorator(func: OperatorFunc):
        # print(func.__name__, signature)
        opdata = OperatorData(op, signature, func)
        _register_operator(opdata)
        return func
    return decorator

# register an operator for all possible permutations of args
def operator_permute(op: Operator, primary: DataType, *secondary: DataType):
    base_sig = [primary, *secondary]

    def decorator(func: OperatorFunc):
        # print(func.__name__, base_sig)
        for permute in itertools.permutations(range(len(base_sig))):
            signature = tuple(base_sig[i] for i in permute)
            
            reorder = _ReorderFunc(func, permute)
            @wraps(func)
            def wrapper(*args):
                return reorder(*args)

            opdata = OperatorData(op, signature, wrapper)
            _register_operator(opdata)
        return func
    return decorator

class _ReorderFunc(NamedTuple):
    func: Callable
    permute: Sequence[int]

    def __call__(self, ctx: ContextFrame, *args: Any) -> Any:
        # print(self.permute, args)
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


###### Eval

@operator_func(Operator.Eval, DataType.Block)
def operator_eval(ctx, o):
    sub_ctx = ctx.create_child()
    sub_ctx.exec(o.value)
    yield from sub_ctx.iter_stack()

# TODO eval strings

###### Add

# concatenate arrays
@operator_func(Operator.Add, DataType.Array, DataType.Array)
def operator_add(ctx, a, b):
    yield ArrayValue([*a.value, *b.value])

# append item to end of array
@operator_func(Operator.Add, DataType.Array, DataType.String)
@operator_func(Operator.Add, DataType.Array, DataType.Number)
@operator_func(Operator.Add, DataType.Array, DataType.Bool)
def operator_add(ctx, arr, item):
    arr.value.append(item)
    yield arr

# insert item at beginning of array
@operator_func(Operator.Add, DataType.String, DataType.Array)
@operator_func(Operator.Add, DataType.Number, DataType.Array)
@operator_func(Operator.Add, DataType.Bool,   DataType.Array)
def operator_add(ctx, item, arr):
    arr.value.insert(0, item)
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

###### Mul

@operator_func(Operator.Mul, DataType.Number, DataType.Number)
def operator_mul(ctx, a, b):
    yield NumberValue(a.value * b.value)



if __name__ == '__main__':
    from myscript.parser import Parser
    from myscript.runtime import ScriptRuntime

    # print(OP_REGISTRY)
    
    tests = [
        """ [ 3 2]  [ 1 'b' { 'c' 'd' } ] ~ """,
        """ [ 1 'b' [ 3 2]`  { 'c' 'd' } ]`  """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] + """,
        """ { -1 5 * [ 'step' ] + }! """,
    ]

    for test in tests:
        print('>>>', test)

        parser = Parser()
        runtime = ScriptRuntime(parser)
        runtime.exec(test)