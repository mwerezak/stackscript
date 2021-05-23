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
    from typing import Any, Union, Optional, Callable, Iterator, Sequence, MutableMapping, MutableSequence
    from myscript.runtime import ContextFrame
    from myscript.values import DataValue

    Signature = Sequence[Operand]
    OperatorFunc = Callable[[ContextFrame, ...], Iterator[DataValue]]


# map operator -> signature -> operator data
OP_REGISTRY: MutableMapping[Operator, MutableMapping[Union[Signature, int], OperatorData]] = defaultdict(dict)
OP_ARITY: MutableMapping[Operator, int] = defaultdict(int)

class OperandError(Exception):
    def __init__(self, message: str, *operands: DataValue):
        self.message = message
        self.operands = operands

## TODO better name
class OperatorData(NamedTuple):
    op: Operator
    arity: int
    signature: Union[Signature, int]
    func: OperatorFunc


def apply_operator(ctx: ContextFrame, op: Operator) -> None:
    opdata = _search_registery(op, ctx)

    args = [ ctx.pop_stack() for i in range(opdata.arity) ]

    for value in opdata.func(ctx, *reversed(args)):
        if not isinstance(value, DataValue):
            raise TypeError(f"invalid object type yielded from operator {opdata}: {type(value)}", value)
        ctx.push_stack(value)

def _search_registery(op: Operator, ctx: ContextFrame) -> OperatorData:
    registry = OP_REGISTRY[op]
    arity = OP_ARITY[op]

    # nargs == 0
    opdata = registry.get(()) or registry.get(0)
    if opdata is not None:
        return opdata

    args = []
    for next_arg in ctx.iter_stack():
        args.append(next_arg)
        signature = tuple(value.optype for value in reversed(args))
        nargs = len(args)

        opdata = registry.get(signature)
        if opdata is not None:
            return opdata

        opdata = registry.get(nargs)
        if opdata is not None:
            return opdata

        if nargs >= arity:
            raise OperandError(f"Invalid operands for operator '{op.name}'", *args)

    raise OperandError(f"not enough operands for operator '{op.name}'")

def _register_operator(opdata: OperatorData) -> None:
    registry = OP_REGISTRY[opdata.op]

    signature = opdata.signature
    if signature in registry:
        raise ValueError(f"signature {signature} is already registered for {opdata.op}")

    registry[signature] = opdata
    OP_ARITY[opdata.op] = max(OP_ARITY[opdata.op], opdata.arity)

# note: typed ophandlers take precedence over untyped

def operator_untyped(op: Operator, arity: int):
    def decorator(func: OperatorFunc):
        opdata = OperatorData(op, arity, arity, func)
        _register_operator(opdata)
        return func
    return decorator

def operator_typed(op: Operator, *signature: Operand):
    def decorator(func: OperatorFunc):
        opdata = OperatorData(op, len(signature), signature, func)
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
            opdata = OperatorData(op, len(signature), signature, reorder)
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
# @operator_typed(Operator.Invert, Operand.Array)
# def operator_invert(ctx, o):
#     yield from o.value

# bitwise not
@operator_typed(Operator.Invert, Operand.Number)
def operator_invert(ctx, n):
    if not isinstance(n, IntValue):
        raise OperandError('unsupported operand type', n)
    yield IntValue(~n.value)

###### Inspect

@operator_untyped(Operator.Inspect, 1)
def operator_inspect(ctx, o):
    yield StringValue(o.format())


###### Invoke

# evaluate a block in its own nested context
# @operator_typed(Operator.Invoke, Operand.Block)
# def operator_invoke(ctx, block):
#     sub_ctx = ctx.create_child()
#     sub_ctx.exec(block)
#     yield from sub_ctx.iter_stack_result()

# evaluate a string directly in the current context
# @operator_typed(Operator.Invoke, Operand.String)
# def operator_invoke(ctx, text):
#     ctx.execs(text.value)
#     return ()

# @operator_typed(Operator.Invoke, Operand.Number)
# def operator_invoke(ctx, block):
#     sub_ctx = ctx.create_child()
#     sub_ctx.exec(block)
#     yield from sub_ctx.iter_stack_result()

###### Rotate

# move the ith stack element to top
# @operator_typed(Operator.Rotate, Operand.Number)
# def operator_rotate(ctx, index):
#     item = ctx.peek_stack(index.value)
#     ctx.remove_stack(index.value)
#     yield item


###### Index

# copy the ith stack element to top
# @operator_typed(Operator.Index, Operand.Number)
# def operator_index(ctx, index):
#     yield ctx.peek_stack(index.value)


###### Dup

@operator_untyped(Operator.Dup, 0)
def operator_dup(ctx):
    yield ctx.peek_stack(0)

###### Drop

@operator_untyped(Operator.Drop, 1)
def operator_drop(ctx, value):
    return ()  # no-op, just drop the value

###### Break

@operator_untyped(Operator.Break, 0)
def operator_break(ctx):
    ctx.clear_stack()
    return ()

###### Assignment

## TODO


###### Add

# concatenate arrays
@operator_typed(Operator.Add, Operand.Array, Operand.Array)
def operator_add(ctx, a, b):
    a.value.extend(b.value)
    yield a

# concatenate strings
@operator_typed(Operator.Add, Operand.String, Operand.String)
def operator_add(ctx, a, b):
    yield StringValue(a.value + b.value)

# add numbers
@operator_typed(Operator.Add, Operand.Number, Operand.Number)
def operator_add(ctx, a, b):
    yield NumberValue(a.value + b.value)


###### Sub

# array difference
@operator_typed(Operator.Sub, Operand.Array, Operand.Array)
def operator_sub(ctx, a, b):
    for item in b:
        try:
            a.value.remove(item)
        except ValueError:
            pass
    yield a

@operator_typed(Operator.Sub, Operand.Number, Operand.Number)
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

@operator_typed(Operator.Mul, Operand.Number, Operand.Number)
def operator_mul(ctx, a, b):
    yield NumberValue(a.value * b.value)


###### Div

# map. execute a block over all elements.
# @operator_permute(Operator.Div, Operand.Block, Operand.Array)
# def operator_div(ctx, block, array):
#     result = []
#     for item in array:
#         sub_ctx = ctx.create_child()
#         sub_ctx.push_stack(item)
#         sub_ctx.exec(block)
#         result.extend(sub_ctx.iter_stack_result())
#     yield ArrayValue(result)

# @operator_permute(Operator.Div, Operand.Block, Operand.String)
# def operator_div(ctx, block, string):
#     result = []
#     for item in string:
#         sub_ctx = ctx.create_child()
#         sub_ctx.push_stack(item)
#         sub_ctx.exec(block)
#         result.extend(sub_ctx.iter_stack_result())
#     yield ArrayValue(result)

@operator_typed(Operator.Div, Operand.Number, Operand.Number)
def operator_div(ctx, a, b):
    yield NumberValue(a.value / b.value)


###### Mod

# execute a block over all elements directly in the current context
# @operator_permute(Operator.Mod, Operand.Block, Operand.Array)
# def operator_mod(ctx, block, array):
#     for item in array:
#         ctx.push_stack(item)
#         ctx.exec(block)
#     return ()

# @operator_permute(Operator.Mod, Operand.Block, Operand.String)
# def operator_mod(ctx, block, string):
#     for item in string:
#         ctx.push_stack(item)
#         ctx.exec(block)
#     return ()


@operator_typed(Operator.Mod, Operand.Number, Operand.Number)
def operator_mod(ctx, a, b):
    yield NumberValue(a.value % b.value)


###### Pow

@operator_typed(Operator.Pow, Operand.Number, Operand.Number)
def operator_pow(ctx, a, b):
    yield NumberValue(a.value ** b.value)


###### Bitwise Or/And/Xor

# setwise or (union), and (intersection), xor (symmetric difference)
@operator_typed(Operator.BitOr, Operand.Array, Operand.Array)
def operator_bitor(ctx, a, b):
    union = set(a)
    union.update(b)
    yield ArrayValue(union)

@operator_typed(Operator.BitAnd, Operand.Array, Operand.Array)
def operator_bitand(ctx, a, b):
    intersect = set(a)
    intersect.intersection_update(b)
    yield ArrayValue(intersect)

@operator_typed(Operator.BitXor, Operand.Array, Operand.Array)
def operator_bitxor(ctx, a, b):
    symdiff = set(a)
    symdiff.symmetric_difference_update(b)
    yield ArrayValue(symdiff)

# bitwise and, or, xor
@operator_typed(Operator.BitAnd, Operand.Number, Operand.Number)
def operator_bitand(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type", a, b)
    yield IntValue(a.value & b.value)

@operator_typed(Operator.BitOr, Operand.Number, Operand.Number)
def operator_bitor(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type", a, b)
    yield IntValue(a.value | b.value)

@operator_typed(Operator.BitXor, Operand.Number, Operand.Number)
def operator_bitxor(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type", a, b)
    yield IntValue(a.value ^ b.value)

# logical and, or, xor
@operator_typed(Operator.BitAnd, Operand.Bool, Operand.Bool)
def operator_bitand(ctx, a, b):
    yield BoolValue.get_value(a.value & b.value)

@operator_typed(Operator.BitOr, Operand.Bool, Operand.Bool)
def operator_bitor(ctx, a, b):
    yield BoolValue.get_value(a.value | b.value)

@operator_typed(Operator.BitXor, Operand.Bool, Operand.Bool)
def operator_bitxor(ctx, a, b):
    yield BoolValue.get_value(a.value ^ b.value)


# left shift
@operator_typed(Operator.LShift, Operand.Number, Operand.Number)
def operator_lshift(ctx, a, shift):
    if not isinstance(a, IntValue) or not isinstance(shift, IntValue):
        raise OperandError("unsupported operand type", a)
    yield IntValue(a.value << shift.value)

# right shift
@operator_typed(Operator.RShift, Operand.Number, Operand.Number)
def operator_rshift(ctx, a, shift):
    if not isinstance(a, IntValue) or not isinstance(shift, IntValue):
        raise OperandError("unsupported operand type", a)
    yield IntValue(a.value >> shift.value)


###### Logical Comparison

@operator_typed(Operator.LT, Operand.Number, Operand.Number)
def operator_lt(ctx, a, b):
    yield BoolValue.get_value(a < b)

@operator_typed(Operator.LE, Operand.Number, Operand.Number)
def operator_le(ctx, a, b):
    yield BoolValue.get_value(a <= b)

@operator_typed(Operator.GT, Operand.Number, Operand.Number)
def operator_gt(ctx, a, b):
    yield BoolValue.get_value(a > b)

@operator_typed(Operator.GE, Operand.Number, Operand.Number)
def operator_ge(ctx, a, b):
    yield BoolValue.get_value(a >= b)

###### Equality

@operator_untyped(Operator.Equal, 2)
def operator_equal(ctx, a, b):
    yield BoolValue.get_value(a == b)

@operator_typed(Operator.Equal, Operand.Number, Operand.Number)
def operator_equal(ctx, a, b):
    if isinstance(a, IntValue) and isinstance(b, IntValue):
        yield BoolValue.get_value(a.value == b.value)
    else:
        yield BoolValue.get_value( abs(a.value - b.value) < 10**-9 )


###### Array Append

# append item to beginning or end of array
# if both operands are arrays, append the second to the end of the first
@operator_untyped(Operator.Append, 2)
def operator_append(ctx, a, b):
    if isinstance(a, ArrayValue):
        a.value.append(b)
        yield a
    elif isinstance(b, ArrayValue):
        b.value.insert(0, a)
        yield b
    else:
        raise OperandError("unsupported operand type", a, b)


###### Array Decons/Pop

@operator_typed(Operator.Decons, Operand.Array)
def operator_decons(ctx, array):
    item = array.value.pop()
    yield array
    yield item

@operator_typed(Operator.Decons, Operand.String)
def operator_decons(ctx, string):
    yield StringValue(string.value[:-1])
    yield StringValue(string.value[-1])

###### Size

@operator_typed(Operator.Size, Operand.Array)
@operator_typed(Operator.Size, Operand.String)
def operator_size(ctx, seq):
    yield IntValue(len(seq))

###### Logical Not

@operator_untyped(Operator.Not, 1)
def operator_not(ctx, a):
    yield BoolValue.get_value(not bool(a))

###### Short-Circuiting And

@operator_untyped(Operator.And, 2)
def operator_and(ctx: ContextFrame, a, b):
    # left expression
    if isinstance(a, BlockValue):
        sub_ctx = ctx.create_child()
        sub_ctx.exec(a)
        if sub_ctx.stack_size() != 1:
            raise OperandError('left expression did not evaluate to a single value', a, b)
        a = sub_ctx.peek_stack(0)

    if not bool(a):
        return [a]  # short-circuit!

    # right expression
    if isinstance(b, BlockValue):
        sub_ctx = ctx.create_child()
        sub_ctx.exec(b)
        if sub_ctx.stack_size() != 1:
            raise OperandError('right expression did not evaluate to a single value', a, b)
        b = sub_ctx.peek_stack(0)

    return [b]


###### Short-Circuiting Or

@operator_untyped(Operator.Or, 2)
def operator_or(ctx: ContextFrame, a, b):
    # left expression
    if isinstance(a, BlockValue):
        sub_ctx = ctx.create_child()
        sub_ctx.exec(a)
        if sub_ctx.stack_size() != 1:
            raise OperandError('left expression did not evaluate to a single value', a, b)
        a = sub_ctx.peek_stack(0)


    if bool(a):
        return [a]  # short-circuit!

    # right expression
    if isinstance(b, BlockValue):
        sub_ctx = ctx.create_child()
        sub_ctx.exec(b)
        if sub_ctx.stack_size() != 1:
            raise OperandError('right expression did not evaluate to a single value', a, b)
        b = sub_ctx.peek_stack(0)

    return [b]


if __name__ == '__main__':
    from myscript.runtime import ScriptRuntime

    from pprint import pprint
    pprint(OP_REGISTRY)

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
        """ 'a' not """,
    ]

    for test in tests:
        print('>>>', test)
        rt = ScriptRuntime()
        rt.run_script(test)
