""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from myscript.opcodes import Operator, Operand

from myscript.values import (
    DataValue, BoolValue, IntValue, FloatValue, NumberValue, StringValue, ArrayValue, BlockValue
)

if TYPE_CHECKING:
    from typing import Any, Callable, Iterator, Sequence, MutableMapping, MutableSequence
    from myscript.runtime import ContextFrame
    from myscript.values import DataValue

    Signature = Sequence[Operand]
    OperatorFunc = Callable[[ContextFrame, ...], Iterator[DataValue]]


## TODO simplify this to operator -> signature -> OperatorData
# map operator -> arity -> signature -> operator data
OP_REGISTRY: MutableMapping[Operator, MutableSequence[MutableMapping[Signature, OperatorData]]] = defaultdict(list)

class OperandError(Exception):
    def __init__(self, message: str, *operands: DataValue):
        self.message = message
        self.operands = operands

## TODO better name
class OperatorData(NamedTuple):
    op: Operator
    signature: Sequence[Operand]
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

        sig = tuple(value.optype for value in args)
        if sig in subregistry:
            return subregistry[sig]

    raise OperandError(f"Invalid operands for operator '{op.name}'", *args)

def _register_operator(opdata: OperatorData) -> None:
    registry = OP_REGISTRY[opdata.op]
    nargs = len(opdata.signature)

    while len(registry) <= nargs:
        registry.append({})

    signature = opdata.signature
    if signature in registry[nargs]:
        raise ValueError(f"signature {signature} is already registered for {opdata.op}")
    registry[nargs][signature] = opdata

def operator_func(op: Operator, *signature: Operand):
    def decorator(func: OperatorFunc):
        # print(func.__name__, signature)
        opdata = OperatorData(op, signature, func)
        _register_operator(opdata)
        return func
    return decorator

# register an operator for all possible permutations of args
def operator_permute(op: Operator, primary: Operand, *secondary: Operand):
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
# @operator_func(Operator.Invert, Operand.Array)
# def operator_invert(ctx, o):
#     yield from o.value

# bitwise not
@operator_func(Operator.Invert, Operand.Number)
def operator_invert(ctx, n):
    if not isinstance(n, IntValue):
        raise OperandError('unsupported operand type', n)
    yield IntValue(~n.value)

###### Inspect

@operator_func(Operator.Inspect, Operand.Block)
@operator_func(Operator.Inspect, Operand.Array)
@operator_func(Operator.Inspect, Operand.String)
@operator_func(Operator.Inspect, Operand.Number)
@operator_func(Operator.Inspect, Operand.Bool)
def operator_inspect(ctx, o):
    yield StringValue(o.format())


###### Invoke

# evaluate a block in its own nested context
# @operator_func(Operator.Invoke, Operand.Block)
# def operator_invoke(ctx, block):
#     sub_ctx = ctx.create_child()
#     sub_ctx.exec(block)
#     yield from sub_ctx.iter_stack_result()

# evaluate a string directly in the current context
# @operator_func(Operator.Invoke, Operand.String)
# def operator_invoke(ctx, text):
#     ctx.execs(text.value)
#     return ()

# @operator_func(Operator.Invoke, Operand.Number)
# def operator_invoke(ctx, block):
#     sub_ctx = ctx.create_child()
#     sub_ctx.exec(block)
#     yield from sub_ctx.iter_stack_result()

###### Rotate

# move the ith stack element to top
# @operator_func(Operator.Rotate, Operand.Number)
# def operator_rotate(ctx, index):
#     item = ctx.peek_stack(index.value)
#     ctx.remove_stack(index.value)
#     yield item


###### Index

# copy the ith stack element to top
# @operator_func(Operator.Index, Operand.Number)
# def operator_index(ctx, index):
#     yield ctx.peek_stack(index.value)


###### Dup

@operator_func(Operator.Dup)
def operator_dup(ctx):
    yield ctx.peek_stack(0)

###### Drop

@operator_func(Operator.Drop, Operand.Bool)
@operator_func(Operator.Drop, Operand.Number)
@operator_func(Operator.Drop, Operand.String)
@operator_func(Operator.Drop, Operand.Array)
@operator_func(Operator.Drop, Operand.Block)
def operator_drop(ctx, item):
    return ()  # no-op, just drop the item

###### Break

@operator_func(Operator.Break)
def operator_break(ctx):
    ctx.clear_stack()
    return ()

###### Assignment

## TODO


###### Add

# concatenate arrays
@operator_func(Operator.Add, Operand.Array, Operand.Array)
def operator_add(ctx, a, b):
    a.value.extend(b.value)
    yield a

# concatenate strings
@operator_func(Operator.Add, Operand.String, Operand.String)
def operator_add(ctx, a, b):
    yield StringValue(a.value + b.value)

# add numbers
@operator_func(Operator.Add, Operand.Number, Operand.Number)
def operator_add(ctx, a, b):
    yield NumberValue(a.value + b.value)


###### Sub

# array difference
@operator_func(Operator.Sub, Operand.Array, Operand.Array)
def operator_sub(ctx, a, b):
    for item in b:
        try:
            a.value.remove(item)
        except ValueError:
            pass
    yield a

@operator_func(Operator.Sub, Operand.Number, Operand.Number)
def operator_sub(ctx, a, b):
    yield NumberValue(a.value - b.value)

###### Mul

# execute a block a certain number of times in the current context
@operator_permute(Operator.Mul, Operand.Number, Operand.Block)
def operator_mul(ctx, repeat, block):
    for i in range(repeat.value):
        ctx.exec(block)
    return ()


# array/string repeat
@operator_permute(Operator.Mul, Operand.Number, Operand.Array)
def operator_mul(ctx, repeat, array):
    yield ArrayValue([
        data for data in array for i in range(repeat.value)
    ])

# array/string repeat
@operator_permute(Operator.Mul, Operand.Number, Operand.String)
def operator_mul(ctx, repeat, text):
    text = ''.join(text.value for i in range(repeat.value))
    yield StringValue(text)

@operator_func(Operator.Mul, Operand.Number, Operand.Number)
def operator_mul(ctx, a, b):
    yield NumberValue(a.value * b.value)


###### Div

# map. execute a block over all elements.
@operator_permute(Operator.Div, Operand.Block, Operand.Array)
def operator_div(ctx, block, array):
    result = []
    for item in array:
        sub_ctx = ctx.create_child()
        sub_ctx.push_stack(item)
        sub_ctx.exec(block)
        result.extend(sub_ctx.iter_stack_result())
    yield ArrayValue(result)

@operator_permute(Operator.Div, Operand.Block, Operand.String)
def operator_div(ctx, block, string):
    result = []
    for item in string:
        sub_ctx = ctx.create_child()
        sub_ctx.push_stack(item)
        sub_ctx.exec(block)
        result.extend(sub_ctx.iter_stack_result())
    yield ArrayValue(result)

@operator_func(Operator.Div, Operand.Number, Operand.Number)
def operator_div(ctx, a, b):
    yield NumberValue(a.value / b.value)


###### Mod

# execute a block over all elements directly in the current context
@operator_permute(Operator.Mod, Operand.Block, Operand.Array)
def operator_mod(ctx, block, array):
    for item in array:
        ctx.push_stack(item)
        ctx.exec(block)
    return ()

@operator_permute(Operator.Mod, Operand.Block, Operand.String)
def operator_mod(ctx, block, string):
    for item in string:
        ctx.push_stack(item)
        ctx.exec(block)
    return ()


@operator_func(Operator.Mod, Operand.Number, Operand.Number)
def operator_mod(ctx, a, b):
    yield NumberValue(a.value % b.value)


###### Pow

@operator_func(Operator.Pow, Operand.Number, Operand.Number)
def operator_pow(ctx, a, b):
    yield NumberValue(a.value ** b.value)


###### Bitwise Or/And/Xor

# setwise or (union)
@operator_func(Operator.BitOr, Operand.Array, Operand.Array)
def operator_bitor(ctx, a, b):
    union = set(a)
    union.update(b)
    yield ArrayValue(union)

# setwise and (intersection)
@operator_func(Operator.BitAnd, Operand.Array, Operand.Array)
def operator_bitand(ctx, a, b):
    intersect = set(a)
    intersect.intersection_update(b)
    yield ArrayValue(intersect)

# setwise xor (symmetric difference)
@operator_func(Operator.BitXor, Operand.Array, Operand.Array)
def operator_bitxor(ctx, a, b):
    symdiff = set(a)
    symdiff.symmetric_difference_update(b)
    yield ArrayValue(symdiff)

# bitwise and
@operator_func(Operator.BitXor, Operand.Number, Operand.Number)
def operator_bitxor(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type")
    yield IntValue(a.value ^ b.value)

# bitwise or
@operator_func(Operator.BitOr, Operand.Number, Operand.Number)
def operator_bitor(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type")
    yield IntValue(a.value | b.value)

# bitwise and
@operator_func(Operator.BitAnd, Operand.Number, Operand.Number)
def operator_bitand(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type")
    yield IntValue(a.value & b.value)

# left shift
@operator_func(Operator.LShift, Operand.Number, Operand.Number)
def operator_lshift(ctx, a, shift):
    if not isinstance(a, IntValue) or not isinstance(shift, IntValue):
        raise OperandError("unsupported operand type")
    yield IntValue(a.value << shift.value)

# right shift
@operator_func(Operator.RShift, Operand.Number, Operand.Number)
def operator_rshift(ctx, a, shift):
    if not isinstance(a, IntValue) or not isinstance(shift, IntValue):
        raise OperandError("unsupported operand type")
    yield IntValue(a.value >> shift.value)


###### Logical Comparison

@operator_func(Operator.LT, Operand.Number, Operand.Number)
def operator_lt(ctx, a, b):
    yield BoolValue(a < b)

@operator_func(Operator.LE, Operand.Number, Operand.Number)
def operator_le(ctx, a, b):
    yield BoolValue(a <= b)

@operator_func(Operator.GT, Operand.Number, Operand.Number)
def operator_gt(ctx, a, b):
    yield BoolValue(a > b)

@operator_func(Operator.GE, Operand.Number, Operand.Number)
def operator_ge(ctx, a, b):
    yield BoolValue(a >= b)

###### Equality

@operator_func(Operator.Equal, Operand.Array,  Operand.Array)
@operator_func(Operator.Equal, Operand.String, Operand.String)
@operator_func(Operator.Equal, Operand.Bool,   Operand.Bool)
@operator_permute(Operator.Equal, Operand.Bool, Operand.Block)
@operator_permute(Operator.Equal, Operand.Bool, Operand.Array)
@operator_permute(Operator.Equal, Operand.Bool, Operand.String)
@operator_permute(Operator.Equal, Operand.Bool, Operand.Number)
def operator_equal(ctx, a, b):
    yield BoolValue(a == b)

@operator_func(Operator.Equal, Operand.Number, Operand.Number)
def operator_equal(ctx, a, b):
    if isinstance(a, IntValue) and isinstance(b, IntValue):
        yield BoolValue(a.value == b.value)
    else:
        yield BoolValue( abs(a.value - b.value) < 10**-9 )


###### Array Append

# append item to end of array
@operator_func(Operator.Append, Operand.Array, Operand.Block)
@operator_func(Operator.Append, Operand.Array, Operand.String)
@operator_func(Operator.Append, Operand.Array, Operand.Number)
@operator_func(Operator.Append, Operand.Array, Operand.Bool)
def operator_append(ctx, array, item):
    array.value.append(item)
    yield array

# insert item at beginning of array
@operator_func(Operator.Append, Operand.Block,  Operand.Array)
@operator_func(Operator.Append, Operand.String, Operand.Array)
@operator_func(Operator.Append, Operand.Number, Operand.Array)
@operator_func(Operator.Append, Operand.Bool,   Operand.Array)
def operator_append(ctx, item, array):
    array.value.insert(0, item)
    yield array

###### Array Decons/Pop

@operator_func(Operator.Decons, Operand.Array)
def operator_decons(ctx, array):
    item = array.value.pop()
    yield array
    yield item

@operator_func(Operator.Decons, Operand.String)
def operator_decons(ctx, string):
    yield StringValue(string.value[:-1])
    yield StringValue(string.value[-1])

###### Size

@operator_func(Operator.Size, Operand.Array)
@operator_func(Operator.Size, Operand.String)
def operator_size(ctx, seq):
    yield IntValue(len(seq))


###### Logical Not

@operator_func(Operator.Not, Operand.Block)
@operator_func(Operator.Not, Operand.Array)
@operator_func(Operator.Not, Operand.String)
@operator_func(Operator.Not, Operand.Number)
@operator_func(Operator.Not, Operand.Bool)
def operator_not(ctx, a):
    yield not bool(a)

###### Logical And

# @operator_func(Operator.Not, Operand.Block)
# @operator_func(Operator.Not, Operand.Array)
# @operator_func(Operator.Not, Operand.String)
# @operator_func(Operator.Not, Operand.Number)
# @operator_func(Operator.Not, Operand.Bool)
# def operator_and(ctx, a):
#     yield not bool(a)

if __name__ == '__main__':
    from myscript.runtime import ScriptRuntime

    # from pprint import pprint
    # pprint(OP_REGISTRY)

    tests = [
        """ [ 3 2]  [ 1 'b' { 'c' 'd' } ] """,
        """ [ 1 'b' [ 3 2 ]`  { 'c' 'd' } ]`  """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] ++ """,
        # """ { -1 5 * [ 'step' ] + }! """,
        # """ [ 1 '2 3 -'! 4 5 6 7 + ] """,
        # """ 1 2 3 4 5 6 2$ """,
        # """ 1 2 3 4 5 6 2@ """,
        """ 'str' 3 * 2 ['a' 'b' 'c'] *""",
        # """ 1 2 3 4 5 6 ,,, [] { 1@ + } 3* . # """,
        # """ [ 1 2 3 ] {2*}/ ~ """,
        # """ [] [ 1 2 3 ] {2* 1@ +}% """,
        """ [1 2 3 4 5 6] [2 4 5] -""",
        # """ [7 6; 5 4 3 2 1] {3 <=}/ 0 false = """,
        # """ [ 1 2 3 ] {2*}/ . [ 2 4 6 ] = """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] | """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] & """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] ^ """,

    ]

    for test in tests:
        print('>>>', test)
        rt = ScriptRuntime()
        rt.run_script(test)
