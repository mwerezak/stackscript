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
from myscript.values import DataValue, BoolValue, NumberValue, StringValue, ArrayValue, BlockValue
from myscript.errors import ScriptError

if TYPE_CHECKING:
    from typing import Any, Callable, Iterator, Sequence, MutableMapping, MutableSequence
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
    opdata = _search_registery(op, ctx.iter_stack())

    args = [ ctx.pop_stack() for i in range(len(opdata.signature)) ]
    args.reverse()

    for value in opdata.func(ctx, *args):
        if not isinstance(value, DataValue):
            raise TypeError(f"invalid object type yielded from operator {opdata}: {type(value)}", value)
        ctx.push_stack(value)

def _search_registery(op: Operator, peek: Iterator[DataValue]) -> OperatorData:
    registry = OP_REGISTRY[op]

    args = []
    for nargs, subregistry in enumerate(registry):
        try:
            while len(args) < nargs:
                args.insert(0, next(peek))
        except StopIteration:
            break

        sig = tuple(value.type for value in args)
        if sig in subregistry:
            return subregistry[sig]

    message = "Invalid operands for operator '{op.name}':\n"
    if len(args):
        args_msg = ' '.join(data.format() for data in args)
        types_msg = ', '.join(data.type.name for data in args)
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
            opdata = OperatorData(op, signature, reorder)
            _register_operator(opdata)
        return func
    return decorator

class _ReorderFunc(NamedTuple):
    func: Callable
    permute: Sequence[int]

    def __call__(self, ctx: ContextFrame, *args: Any) -> Any:
        # print(self.permute, args)
        # print(*( args[i].type for i in self.permute ))
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

# evaluate a block in its own nested context
@operator_func(Operator.Eval, DataType.Block)
def operator_eval(ctx, o):
    sub_ctx = ctx.create_child()
    sub_ctx.exec(o.value)
    yield from sub_ctx.iter_stack_result()

# evaluate a string directly in the current context
@operator_func(Operator.Eval, DataType.String)
def operator_eval(ctx, text):
    ctx.exec(text.value)
    return ()


###### Rotate

# move the ith stack element to top
@operator_func(Operator.Rotate, DataType.Number)
def operator_rotate(ctx, index):
    item = ctx.peek_stack(index.value)
    ctx.remove_stack(index.value)
    yield item


###### Index

# copy the ith stack element to top
@operator_func(Operator.Index, DataType.Number)
def operator_rotate(ctx, index):
    yield ctx.peek_stack(index.value)


###### Drop

@operator_func(Operator.Drop, DataType.Bool)
@operator_func(Operator.Drop, DataType.Number)
@operator_func(Operator.Drop, DataType.String)
@operator_func(Operator.Drop, DataType.Array)
@operator_func(Operator.Drop, DataType.Block)
def operator_rotate(ctx, item):
    return ()  # no-op, just drop the item


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

@operator_permute(Operator.Mul, DataType.Number, DataType.Array)
def operator_mul(ctx, repeat, array):
    yield ArrayValue([
        data for data in array.value for i in range(repeat.value)
    ])

# array/string repeat
# @operator_permute(Operator.Mul, DataType.Number, DataType.Array)
@operator_permute(Operator.Mul, DataType.Number, DataType.String)
def operator_mul(ctx, repeat, text):
    text = ''.join(text.value for i in range(repeat.value))
    yield StringValue(text)

@operator_func(Operator.Mul, DataType.Number, DataType.Number)
def operator_mul(ctx, a, b):
    yield NumberValue(a.value * b.value)



if __name__ == '__main__':
    from myscript.parser import Parser
    from myscript.runtime import ScriptRuntime

    from pprint import pprint
    pprint(OP_REGISTRY)
    
    tests = [
        """ [ 3 2]  [ 1 'b' { 'c' 'd' } ] ~ """,
        """ [ 1 'b' [ 3 2]`  { 'c' 'd' } ]`  """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] + """,
        """ { -1 5 * [ 'step' ] + }! """,
        """ [ 1 '2 3 -'! 4 5 6 7 + ] """,
        """ 1 2 3 4 5 6 2$ """,
        """ 1 2 3 4 5 6 2@ """,
        """ 'str' 3 * 2 ['a' 'b' 'c'] *""",
        """ 1 2 3 4 5 6 ... [] 3 { 1@ + } * """,
    ]

    for test in tests:
        print('>>>', test)

        parser = Parser()
        runtime = ScriptRuntime(parser)
        runtime.exec(test)