from __future__ import annotations

import itertools
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from stackscript.opdefs import Operator, Operand
from stackscript.parser import Identifier

from stackscript.values import (
    DataValue, BoolValue, IntValue, FloatValue, NumberValue, StringValue, ArrayValue, TupleValue, BlockValue
)

if TYPE_CHECKING:
    from typing import Any, Union, Callable, Iterator, Sequence, MutableMapping
    from stackscript.runtime import ContextFrame
    from stackscript.values import DataValue

    Signature = Sequence[Operand]
    OperatorFunc = Callable[[ContextFrame, ...], Iterator[DataValue]]


# map operator -> signature -> operator data
OP_REGISTRY: MutableMapping[Operator, MutableMapping[Union[Signature, int], OpHandler]] = defaultdict(dict)
OP_ARITY: MutableMapping[Operator, int] = defaultdict(int)

class OperandError(Exception):
    def __init__(self, message: str, *operands: DataValue):
        self.message = message
        self.operands = operands


class OpHandler(NamedTuple):
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

def _search_registery(op: Operator, ctx: ContextFrame) -> OpHandler:
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
            raise OperandError("Invalid operands", *args)

    raise OperandError("not enough operands")

def _register_operator(opdata: OpHandler) -> None:
    registry = OP_REGISTRY[opdata.op]

    signature = opdata.signature
    if signature in registry:
        raise ValueError(f"signature {signature} is already registered for {opdata.op}")

    registry[signature] = opdata
    OP_ARITY[opdata.op] = max(OP_ARITY[opdata.op], opdata.arity)

# note: typed ophandlers take precedence over untyped

def ophandler_untyped(op: Operator, arity: int):
    def decorator(func: OperatorFunc):
        opdata = OpHandler(op, arity, arity, func)
        _register_operator(opdata)
        return func
    return decorator

def ophandler_typed(op: Operator, *signature: Operand):
    def decorator(func: OperatorFunc):
        opdata = OpHandler(op, len(signature), signature, func)
        _register_operator(opdata)
        return func
    return decorator

# register an operator for all possible permutations of args
def ophandler_permute(op: Operator, primary: Operand, *secondary: Operand):
    base_sig = [primary, *secondary]

    def decorator(func: OperatorFunc):
        # print(func.__name__, base_sig)
        for permute in itertools.permutations(range(len(base_sig))):
            signature = tuple(base_sig[i] for i in permute)

            reorder = _ReorderFunc(func, permute)
            opdata = OpHandler(op, len(signature), signature, reorder)
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

###### General Operators

###### Invert

# "unpack" the array or string onto the stack
@ophandler_typed(Operator.Invert, Operand.Array)
@ophandler_typed(Operator.Invert, Operand.String)
def operator_unpack(ctx, seq):
    yield from seq

# "unpack" a block by executing it in the current context
@ophandler_typed(Operator.Invert, Operand.Block)
def operator_unpack(ctx, block):
    ctx.exec(block)
    return ()

# bitwise not
@ophandler_typed(Operator.Invert, Operand.Number)
def operator_invert(ctx, n):
    if not isinstance(n, IntValue):
        raise OperandError('unsupported operand type', n)
    return [ IntValue(~n.value) ]

###### Inspect

@ophandler_untyped(Operator.Inspect, 1)
def operator_inspect(ctx, o):
    return [ StringValue(o.format()) ]


###### Invoke

# invoke a block, giving it the top item on the stack
@ophandler_untyped(Operator.Invoke, 2)
def operator_invoke(ctx: ContextFrame, args, block):
    if not isinstance(block, BlockValue):
        raise OperandError('unsupported operand type', args, block)
    sub_ctx = ctx.create_child()
    sub_ctx.push_stack(args)
    sub_ctx.exec(block)
    yield from sub_ctx.iter_stack_result()

# evaluate a string directly in the current context
@ophandler_typed(Operator.Invoke, Operand.String)
def operator_invoke(ctx, text):
    ctx.execs(text.value)
    return ()


###### Rotate

# move the ith stack element to top
# @ophandler_typed(Operator.Rotate, Operand.Number)
# def operator_rotate(ctx, index):
#     item = ctx.peek_stack(index.value)
#     ctx.remove_stack(index.value)
#     yield item


###### Dup

@ophandler_untyped(Operator.Dup, 1)
def operator_dup(ctx, o):
    return [o, o]

###### Drop

@ophandler_untyped(Operator.Drop, 1)
def operator_drop(ctx, value):
    return ()  # no-op, just drop the value

###### Break

@ophandler_untyped(Operator.Break, 0)
def operator_break(ctx):
    ctx.clear_stack()
    return ()

###### Assignment

@ophandler_untyped(Operator.Assign, 0)
def operator_assign(ctx: ContextFrame):
    if ctx.stack_size() < 1:
        raise OperandError('not enough operands')

    try:
        identifier = next(ctx.get_symbol_iter())
    except StopIteration:
        raise OperandError('identifier not found')

    if not isinstance(identifier, Identifier):
        raise OperandError('cannot assign to a non-identifier')

    namespace = ctx.get_namespace()
    namespace[identifier.name] = ctx.peek_stack()
    return ()


###### Add

# concatenate blocks
@ophandler_typed(Operator.Add, Operand.Block, Operand.Block)
def operator_add(ctx, a, b):
    return [BlockValue([*a.value, *b.value])]

# concatenate arrays
@ophandler_typed(Operator.Add, Operand.Array, Operand.Array)
def operator_add(ctx, a, b):
    if isinstance(a, TupleValue):
        return[TupleValue(*a, *b)]

    if isinstance(a, ArrayValue):
        a.value.extend(b.value)
        return [a]

    raise OperandError('unsupported operand types', a, b)

# concatenate strings
@ophandler_typed(Operator.Add, Operand.String, Operand.String)
def operator_add(ctx, a, b):
    return [StringValue(a.value + b.value)]

# add numbers
@ophandler_typed(Operator.Add, Operand.Number, Operand.Number)
def operator_add(ctx, a, b):
    return [NumberValue(a.value + b.value)]


###### Sub

# array difference
@ophandler_typed(Operator.Sub, Operand.Array, Operand.Array)
def operator_sub(ctx, a, b):
    if isinstance(a, TupleValue):
        return [TupleValue(item for item in a if item not in b)]

    if isinstance(a, ArrayValue):
        for item in b:
            try:
                a.value.remove(item)
            except ValueError:
                pass
        return [a]

    raise OperandError('unsupported operand types', a, b)

@ophandler_typed(Operator.Sub, Operand.Number, Operand.Number)
def operator_sub(ctx, a, b):
    yield NumberValue(a.value - b.value)

###### Mul

# execute a block a certain number of times in the current context
@ophandler_permute(Operator.Mul, Operand.Number, Operand.Block)
def operator_mul(ctx, repeat, block):
    for i in range(repeat.value):
        ctx.exec(block)
    return ()

# array/string repeat
@ophandler_permute(Operator.Mul, Operand.Number, Operand.Array)
def operator_mul(ctx, repeat, array):
    ctor = type(array)
    return [ctor( data for data in array for i in range(repeat.value) )]

# array/string repeat
@ophandler_permute(Operator.Mul, Operand.Number, Operand.String)
def operator_mul(ctx, repeat, text):
    text = ''.join(text.value for i in range(repeat.value))
    yield StringValue(text)

@ophandler_typed(Operator.Mul, Operand.Number, Operand.Number)
def operator_mul(ctx, a, b):
    yield NumberValue(a.value * b.value)


###### Div

@ophandler_typed(Operator.Div, Operand.Number, Operand.Number)
def operator_div(ctx, a, b):
    yield NumberValue(a.value / b.value)

# map. execute a block over all elements, producing an array.
@ophandler_permute(Operator.Div, Operand.Block, Operand.Array)
@ophandler_permute(Operator.Div, Operand.Block, Operand.String)
def operator_div(ctx: ContextFrame, block, seq):
    ctor = TupleValue if isinstance(seq, TupleValue) else ArrayValue

    result = []
    for item in seq:
        sub_ctx = ctx.create_child()
        sub_ctx.push_stack(item)
        sub_ctx.exec(block)
        result.extend(sub_ctx.iter_stack_result())
    return [ctor(result)]


###### Mod

@ophandler_typed(Operator.Mod, Operand.Number, Operand.Number)
def operator_mod(ctx, a, b):
    yield NumberValue(a.value % b.value)

# execute a block over all elements directly in the current context
@ophandler_permute(Operator.Mod, Operand.Block, Operand.Array)
@ophandler_permute(Operator.Mod, Operand.Block, Operand.String)
def operator_mod(ctx: ContextFrame, block, seq):
    for item in seq:
        ctx.push_stack(item)
        ctx.exec(block)
    return ()


###### Pow

@ophandler_typed(Operator.Pow, Operand.Number, Operand.Number)
def operator_pow(ctx, a, b):
    yield NumberValue(a.value ** b.value)


###### Bitwise Or/And/Xor

def _array_ctor(*operands):
    for o in operands:
        if isinstance(o, ArrayValue):
            return ArrayValue
    return TupleValue

# setwise or (union), and (intersection), xor (symmetric difference)
@ophandler_typed(Operator.BitOr, Operand.Array, Operand.Array)
def operator_bitor(ctx, a, b):
    union = set(a)
    union.update(b)

    ctor = _array_ctor(a, b)
    yield ctor(union)

@ophandler_typed(Operator.BitAnd, Operand.Array, Operand.Array)
def operator_bitand(ctx, a, b):
    intersect = set(a)
    intersect.intersection_update(b)

    ctor = _array_ctor(a, b)
    yield ctor(intersect)

@ophandler_typed(Operator.BitXor, Operand.Array, Operand.Array)
def operator_bitxor(ctx, a, b):
    symdiff = set(a)
    symdiff.symmetric_difference_update(b)

    ctor = _array_ctor(a, b)
    yield ctor(symdiff)

# bitwise and, or, xor
@ophandler_typed(Operator.BitAnd, Operand.Number, Operand.Number)
def operator_bitand(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type", a, b)
    yield IntValue(a.value & b.value)

@ophandler_typed(Operator.BitOr, Operand.Number, Operand.Number)
def operator_bitor(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type", a, b)
    yield IntValue(a.value | b.value)

@ophandler_typed(Operator.BitXor, Operand.Number, Operand.Number)
def operator_bitxor(ctx, a, b):
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise OperandError("unsupported operand type", a, b)
    yield IntValue(a.value ^ b.value)

# logical and, or, xor
@ophandler_typed(Operator.BitAnd, Operand.Bool, Operand.Bool)
def operator_bitand(ctx, a, b):
    yield BoolValue.get_value(a.value & b.value)

@ophandler_typed(Operator.BitOr, Operand.Bool, Operand.Bool)
def operator_bitor(ctx, a, b):
    yield BoolValue.get_value(a.value | b.value)

@ophandler_typed(Operator.BitXor, Operand.Bool, Operand.Bool)
def operator_bitxor(ctx, a, b):
    yield BoolValue.get_value(a.value ^ b.value)


# left shift
@ophandler_typed(Operator.LShift, Operand.Number, Operand.Number)
def operator_lshift(ctx, a, shift):
    if not isinstance(a, IntValue) or not isinstance(shift, IntValue):
        raise OperandError("unsupported operand type", a)
    yield IntValue(a.value << shift.value)

# right shift
@ophandler_typed(Operator.RShift, Operand.Number, Operand.Number)
def operator_rshift(ctx, a, shift):
    if not isinstance(a, IntValue) or not isinstance(shift, IntValue):
        raise OperandError("unsupported operand type", a)
    yield IntValue(a.value >> shift.value)


###### Logical Comparison

@ophandler_typed(Operator.LT, Operand.Number, Operand.Number)
def operator_lt(ctx, a, b):
    yield BoolValue.get_value(a < b)

@ophandler_typed(Operator.LE, Operand.Number, Operand.Number)
def operator_le(ctx, a, b):
    yield BoolValue.get_value(a <= b)

@ophandler_typed(Operator.GT, Operand.Number, Operand.Number)
def operator_gt(ctx, a, b):
    yield BoolValue.get_value(a > b)

@ophandler_typed(Operator.GE, Operand.Number, Operand.Number)
def operator_ge(ctx, a, b):
    yield BoolValue.get_value(a >= b)

###### Equality

@ophandler_untyped(Operator.Equal, 2)
def operator_equal(ctx, a, b):
    return [BoolValue.get_value(a == b)]

@ophandler_untyped(Operator.NE, 2)
def operator_ne(ctx, a, b):
    return [BoolValue.get_value(a != b)]

@ophandler_typed(Operator.Equal, Operand.Number, Operand.Number)
def operator_equal(ctx, a, b):
    return [BoolValue.get_value(_number_equality(a, b))]

@ophandler_typed(Operator.NE, Operand.Number, Operand.Number)
def operator_ne(ctx, a, b):
    return [BoolValue.get_value(not _number_equality(a, b))]

def _number_equality(a: DataValue, b: DataValue):
    if isinstance(a, IntValue) and isinstance(b, IntValue):
        return a.value == b.value
    return abs(a.value - b.value) < 10**-9

###### Array Cons/Append

# append item to beginning or end of array
# if both operands are arrays, append the second to the end of the first
@ophandler_untyped(Operator.Append, 2)
def operator_append(ctx, a, b):
    if isinstance(a, TupleValue):
        return [TupleValue([*a, b])]
    if isinstance(a, ArrayValue):
        a.value.append(b)
        return [a]

    if isinstance(b, TupleValue):
        return [TupleValue([a, *b])]
    if isinstance(b, ArrayValue):
        b.value.insert(0, a)
        return [b]

    raise OperandError("unsupported operand type", a, b)


###### Array Decons/Pop

@ophandler_typed(Operator.Decons, Operand.Array)
def operator_decons(ctx, array):
    if isinstance(array, TupleValue):
        values = list(array)
        return [TupleValue(values[:-1]), values[-1]]
    if isinstance(array, ArrayValue):
        item = array.value.pop()
        return [array, item]

    raise OperandError("unsupported operand type", array)


@ophandler_typed(Operator.Decons, Operand.String)
def operator_decons(ctx, string):
    return [
        StringValue(string.value[:-1]),
        StringValue(string.value[-1]),
    ]

###### Index

# replace the array or string with the i-th element
@ophandler_typed(Operator.Index, Operand.Array, Operand.Number)
@ophandler_typed(Operator.Index, Operand.String, Operand.Number)
def operator_index(ctx, seq, index):
    return [seq[index.value]]

###### Size

@ophandler_typed(Operator.Size, Operand.Array)
@ophandler_typed(Operator.Size, Operand.String)
def operator_size(ctx, seq):
    yield IntValue(len(seq))

###### Logical Not

@ophandler_untyped(Operator.Not, 1)
def operator_not(ctx, a):
    yield BoolValue.get_value(not bool(a))

###### Short-Circuiting And

@ophandler_untyped(Operator.And, 2)
def operator_and(ctx: ContextFrame, a, b):
    # left expression
    if isinstance(a, BlockValue):
        sub_ctx = ctx.create_child(share_namespace=True)
        sub_ctx.exec(a)
        if sub_ctx.stack_size() != 1:
            raise OperandError('left expression did not evaluate to a single value', a, b)
        a = sub_ctx.peek_stack()

    if not bool(a):
        return [a]  # short-circuit!

    # right expression
    if isinstance(b, BlockValue):
        sub_ctx = ctx.create_child(share_namespace=True)
        sub_ctx.exec(b)
        if sub_ctx.stack_size() != 1:
            raise OperandError('right expression did not evaluate to a single value', a, b)
        b = sub_ctx.peek_stack()

    return [b]


###### Short-Circuiting Or

@ophandler_untyped(Operator.Or, 2)
def operator_or(ctx: ContextFrame, a, b):
    # left expression
    if isinstance(a, BlockValue):
        sub_ctx = ctx.create_child(share_namespace=True)
        sub_ctx.exec(a)
        if sub_ctx.stack_size() != 1:
            raise OperandError('left expression did not evaluate to a single value', a, b)
        a = sub_ctx.peek_stack()


    if bool(a):
        return [a]  # short-circuit!

    # right expression
    if isinstance(b, BlockValue):
        sub_ctx = ctx.create_child(share_namespace=True)
        sub_ctx.exec(b)
        if sub_ctx.stack_size() != 1:
            raise OperandError('right expression did not evaluate to a single value', a, b)
        b = sub_ctx.peek_stack()

    return [b]

###### Short-Circuiting Ternary-If

@ophandler_untyped(Operator.If, 3)
def operator_if(ctx: ContextFrame, cond, if_true, if_false):
    if isinstance(cond, BlockValue):
        sub_ctx = ctx.create_child(share_namespace=True)
        sub_ctx.exec(cond)
        if sub_ctx.stack_size() != 1:
            raise OperandError('condition did not evaluate to a single value', cond, if_true, if_false)
        cond = sub_ctx.peek_stack()

    result = if_true if bool(cond) else if_false
    if isinstance(result, BlockValue):
        ctx.exec(result)
        return ()
    return [result]

###### Do / While

# keep executing a block in the current context as long as the top item is true
@ophandler_typed(Operator.Do, Operand.Block)
def operator_do(ctx: ContextFrame, block):
    ctx.exec(block)
    while bool(ctx.pop_stack()):
        ctx.exec(block)
    return ()

@ophandler_typed(Operator.While, Operand.Block, Operand.Block)
def operator_while(ctx: ContextFrame, cond, body):
    while _eval_cond(ctx, cond):
        ctx.exec(body)
    return ()

def _eval_cond(ctx: ContextFrame, cond: BlockValue) -> bool:
    sub_ctx = ctx.create_child(share_namespace=True)
    sub_ctx.exec(cond)
    if sub_ctx.stack_size() != 1:
        raise OperandError('condition did not evaluate to a single value', cond)
    return bool(sub_ctx.peek_stack())

if __name__ == '__main__':
    from stackscript.runtime import ScriptRuntime

    from pprint import pprint
    pprint(OP_REGISTRY)


