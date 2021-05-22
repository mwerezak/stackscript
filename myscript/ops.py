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
def operator_eval(ctx, block):
    sub_ctx = ctx.create_child()
    sub_ctx.exec(block)
    yield from sub_ctx.iter_stack_result()

# evaluate a string directly in the current context
@operator_func(Operator.Eval, DataType.String)
def operator_eval(ctx, text):
    ctx.exec(text.value)
    return ()

@operator_func(Operator.Eval, DataType.Number)
def operator_eval(ctx, block):
    sub_ctx = ctx.create_child()
    sub_ctx.exec(block)
    yield from sub_ctx.iter_stack_result()

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
def operator_index(ctx, index):
    yield ctx.peek_stack(index.value)


###### Dup

@operator_func(Operator.Dup)
def operator_dup(ctx):
    yield ctx.peek_stack(0)

###### Drop

@operator_func(Operator.Drop, DataType.Bool)
@operator_func(Operator.Drop, DataType.Number)
@operator_func(Operator.Drop, DataType.String)
@operator_func(Operator.Drop, DataType.Array)
@operator_func(Operator.Drop, DataType.Block)
def operator_drop(ctx, item):
    return ()  # no-op, just drop the item

###### Break

@operator_func(Operator.Break)
def operator_break(ctx):
    ctx.clear_stack()
    return ()


###### Add

# concatenate arrays
@operator_func(Operator.Add, DataType.Array, DataType.Array)
def operator_add(ctx, a, b):
    a.value.extend(b.value)
    yield a

# append item to end of array
@operator_func(Operator.Add, DataType.Array, DataType.Block)
@operator_func(Operator.Add, DataType.Array, DataType.String)
@operator_func(Operator.Add, DataType.Array, DataType.Number)
@operator_func(Operator.Add, DataType.Array, DataType.Bool)
def operator_add(ctx, array, item):
    array.value.append(item)
    yield array

# insert item at beginning of array
@operator_func(Operator.Add, DataType.Block,  DataType.Array)
@operator_func(Operator.Add, DataType.String, DataType.Array)
@operator_func(Operator.Add, DataType.Number, DataType.Array)
@operator_func(Operator.Add, DataType.Bool,   DataType.Array)
def operator_add(ctx, item, array):
    array.value.insert(0, item)
    yield array

# concatenate strings
@operator_func(Operator.Add, DataType.String, DataType.String)
def operator_add(ctx, a, b):
    yield StringValue(a.value + b.value)

# add numbers
@operator_func(Operator.Add, DataType.Number, DataType.Number)
def operator_add(ctx, a, b):
    yield NumberValue(a.value + b.value)


###### Sub

# array difference
@operator_func(Operator.Sub, DataType.Array, DataType.Array)
def operator_sub(ctx, a, b):
    for item in b:
        try:
            a.value.remove(item)
        except ValueError:
            pass
    yield a

@operator_func(Operator.Sub, DataType.Number, DataType.Number)
def operator_sub(ctx, a, b):
    yield NumberValue(a.value - b.value)

###### Mul

# execute a block a certain number of times in the current context
@operator_permute(Operator.Mul, DataType.Number, DataType.Block)
def operator_mul(ctx, repeat, block):
    for i in range(repeat.value):
        ctx.exec(block)
    return ()


# array/string repeat
@operator_permute(Operator.Mul, DataType.Number, DataType.Array)
def operator_mul(ctx, repeat, array):
    yield ArrayValue([
        data for data in array for i in range(repeat.value)
    ])

# array/string repeat
@operator_permute(Operator.Mul, DataType.Number, DataType.String)
def operator_mul(ctx, repeat, text):
    text = ''.join(text.value for i in range(repeat.value))
    yield StringValue(text)

@operator_func(Operator.Mul, DataType.Number, DataType.Number)
def operator_mul(ctx, a, b):
    yield NumberValue(a.value * b.value)


###### Div

# map. execute a block over all elements.
@operator_permute(Operator.Div, DataType.Block, DataType.Array)
def operator_div(ctx, block, array):
    result = []
    for item in array:
        sub_ctx = ctx.create_child()
        sub_ctx.push_stack(item)
        sub_ctx.exec(block)
        result.extend(sub_ctx.iter_stack_result())
    yield ArrayValue(result)

@operator_permute(Operator.Div, DataType.Block, DataType.String)
def operator_div(ctx, block, string):
    result = []
    for item in string:
        sub_ctx = ctx.create_child()
        sub_ctx.push_stack(item)
        sub_ctx.exec(block)
        result.extend(sub_ctx.iter_stack_result())
    yield ArrayValue(result)

@operator_func(Operator.Div, DataType.Number, DataType.Number)
def operator_div(ctx, a, b):
    yield NumberValue(a.value / b.value)


###### Mod

# execute a block over all elements directly in the current context
@operator_permute(Operator.Mod, DataType.Block, DataType.Array)
def operator_mod(ctx, block, array):
    for item in array:
        ctx.push_stack(item)
        ctx.exec(block)
    return ()

@operator_permute(Operator.Mod, DataType.Block, DataType.String)
def operator_mod(ctx, block, string):
    for item in string:
        ctx.push_stack(item)
        ctx.exec(block)
    return ()


@operator_func(Operator.Mod, DataType.Number, DataType.Number)
def operator_mod(ctx, a, b):
    yield NumberValue(a.value % b.value)


###### Pow

@operator_func(Operator.Pow, DataType.Number, DataType.Number)
def operator_pow(ctx, a, b):
    yield NumberValue(a.value ** b.value)


###### Size

@operator_func(Operator.Size, DataType.Array)
@operator_func(Operator.Size, DataType.String)
def operator_size(ctx, item):
    yield NumberValue(len(item))


###### Bitwise Or/And/Xor

# setwise or (union)
@operator_func(Operator.BitOr, DataType.Array, DataType.Array)
def operator_bitor(ctx, a, b):
    union = set(a)
    union.update(b)
    yield ArrayValue(union)

# bitwise or
@operator_func(Operator.BitOr, DataType.Number, DataType.Number)
def operator_bitor(ctx, a, b):
    yield NumberValue(a.value | b.value)

# setwise and (intersection)
@operator_func(Operator.BitAnd, DataType.Array, DataType.Array)
def operator_bitand(ctx, a, b):
    intersect = set(a)
    intersect.intersection_update(b)
    yield ArrayValue(intersect)

# bitwise and
@operator_func(Operator.BitAnd, DataType.Number, DataType.Number)
def operator_bitand(ctx, a, b):
    yield NumberValue(a.value & b.value)

# setwise xor (symmetric difference)
@operator_func(Operator.BitXor, DataType.Array, DataType.Array)
def operator_bitxor(ctx, a, b):
    symdiff = set(a)
    symdiff.symmetric_difference_update(b)
    yield ArrayValue(symdiff)

# bitwise and
@operator_func(Operator.BitXor, DataType.Number, DataType.Number)
def operator_bitxor(ctx, a, b):
    yield NumberValue(a.value ^ b.value)


###### Logical Comparison

@operator_func(Operator.LT, DataType.Number, DataType.Number)
def operator_lt(ctx, a, b):
    yield BoolValue(a < b)

@operator_func(Operator.LE, DataType.Number, DataType.Number)
def operator_le(ctx, a, b):
    yield BoolValue(a <= b)

@operator_func(Operator.GT, DataType.Number, DataType.Number)
def operator_gt(ctx, a, b):
    yield BoolValue(a > b)

@operator_func(Operator.GE, DataType.Number, DataType.Number)
def operator_ge(ctx, a, b):
    yield BoolValue(a >= b)

###### Equality

@operator_func(Operator.Equal,    DataType.Array,  DataType.Array)
@operator_func(Operator.Equal,    DataType.String, DataType.String)
@operator_permute(Operator.Equal, DataType.String, DataType.Number)
@operator_permute(Operator.Equal, DataType.String, DataType.Bool)
@operator_permute(Operator.Equal, DataType.Number, DataType.Bool)
@operator_func(Operator.Equal,    DataType.Bool,   DataType.Bool)
def operator_equal(ctx, a, b):
    yield BoolValue(a == b)

@operator_func(Operator.Equal, DataType.Number, DataType.Number)
def operator_equal(ctx, a, b):
    if isinstance(a.value, int) and isinstance(b.value, int):
        yield BoolValue(a.value == b.value)
    else:
        yield BoolValue( abs(a.value - b.value) < 10**-9 )


if __name__ == '__main__':
    from myscript.parser import Parser
    from myscript.runtime import ScriptRuntime

    # from pprint import pprint
    # pprint(OP_REGISTRY)

    tests = [
        """ [ 3 2]  [ 1 'b' { 'c' 'd' } ] ~ """,
        """ [ 1 'b' [ 3 2 ]`  { 'c' 'd' } ]`  """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] + """,
        """ { -1 5 * [ 'step' ] + }! """,
        """ [ 1 '2 3 -'! 4 5 6 7 + ] """,
        """ 1 2 3 4 5 6 2$ """,
        """ 1 2 3 4 5 6 2@ """,
        """ 'str' 3 * 2 ['a' 'b' 'c'] *""",
        """ 1 2 3 4 5 6 ,,, [] { 1@ + } 3* . # """,
        """ [ 1 2 3 ] {2*}/ ~ """,
        """ [] [ 1 2 3 ] {2* 1@ +}% """,
        """ [1 2 3 4 5 6] [2 4 5] -""",
        """ [7 6; 5 4 3 2 1] {3 <=}/ 0 false = """,
        """ [ 1 2 3 ] {2*}/ . [ 2 4 6 ] = """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] | """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] & """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] ^ """,

    ]

    for test in tests:
        print('>>>', test)

        parser = Parser()
        runtime = ScriptRuntime(parser)
        runtime.exec(test)