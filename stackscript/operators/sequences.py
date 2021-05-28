from __future__ import annotations
from typing import TYPE_CHECKING

from stackscript.values import ArrayValue, TupleValue, StringValue, IntValue
from stackscript.exceptions import  ScriptOperandError, ScriptIndexError

from stackscript.operators.defines import Operator, Operand
from stackscript.operators.overloading import ophandler_typed, ophandler_permute
from stackscript.operators.coercion import coerce_array

if TYPE_CHECKING:
    from typing import Type, Iterable
    from stackscript.values import DataValue
    from stackscript.runtime import ContextFrame


###### Unpacking

# "unpack" the array or string onto the stack
@ophandler_typed(Operator.Invert, Operand.Array)
@ophandler_typed(Operator.Invert, Operand.String)
def operator_unpack(ctx, seq) -> Iterable[DataValue]:
    yield from seq

###### Collection (Packing)

@ophandler_typed(Operator.Collect, Operand.Number)
def operator_collect(ctx: ContextFrame, n) -> Iterable[DataValue]:
    if not isinstance(n, IntValue):
        raise ScriptOperandError("unsupported operand type", n)

    result = [ctx.pop_stack() for i in range(n.value)]
    yield TupleValue(reversed(result))


###### Index

# replace the array or string with the i-th element
@ophandler_typed(Operator.Index, Operand.Array, Operand.Number)
@ophandler_typed(Operator.Index, Operand.String, Operand.Number)
def operator_index(ctx, seq, index) -> Iterable[DataValue]:
    if not isinstance(index, IntValue):
        raise ScriptOperandError("unsupported operand type", index)

    if index.value == 0:
        raise ScriptIndexError('0 is not a valid index', seq, index)

    ## convert from 1-indexing
    if index.value < 0:
        i = index.value
    else:
        i = index.value - 1

    try:
        item = seq.value[i]
    except IndexError:
        raise ScriptIndexError('index out of range', seq, index) from None
    return [item]


###### Size

@ophandler_typed(Operator.Size, Operand.Array)
@ophandler_typed(Operator.Size, Operand.String)
def operator_size(ctx, seq) -> Iterable[DataValue]:
    yield IntValue(len(seq))


###### Concatenation

# concatenate arrays/tuples
@ophandler_typed(Operator.Add, Operand.Array, Operand.Array)
def operator_concat(ctx, a, b) -> Iterable[DataValue]:
    rtype = coerce_array(a, b)
    return [rtype(*a, *b)]

# concatenate strings
@ophandler_typed(Operator.Add, Operand.String, Operand.String)
def operator_concat(ctx, a, b) -> Iterable[DataValue]:
    yield StringValue(a.value + b.value)


###### Array/String Repeat

# array/string repeat
@ophandler_permute(Operator.Mul, Operand.Number, Operand.Array)
def operator_repeat(ctx, repeat, array) -> Iterable[DataValue]:
    ctor = type(array)
    yield ctor( data for data in array for i in range(repeat.value) )

# array/string repeat
@ophandler_permute(Operator.Mul, Operand.Number, Operand.String)
def operator_repeat(ctx, repeat, text) -> Iterable[DataValue]:
    text = ''.join(text.value for i in range(repeat.value))
    yield StringValue(text)


###### Array difference

# array difference
@ophandler_typed(Operator.Sub, Operand.Array, Operand.Array)
def operator_diff(ctx, a, b) -> Iterable[DataValue]:
    if isinstance(a, TupleValue):
        return [TupleValue(item for item in a if item not in b)]

    if isinstance(a, ArrayValue):
        for item in b:
            try:
                a.value.remove(item)
            except ValueError:
                pass
        return [a]

    raise ScriptOperandError('unsupported operand types', a, b)

###### Setwise Operations

# setwise or (union), and (intersection), xor (symmetric difference)
@ophandler_typed(Operator.BitOr, Operand.Array, Operand.Array)
def operator_bitor(ctx, a, b) -> Iterable[DataValue]:
    union = set(a)
    union.update(b)

    rtype = coerce_array(a, b)
    yield rtype(union)

@ophandler_typed(Operator.BitAnd, Operand.Array, Operand.Array)
def operator_bitand(ctx, a, b) -> Iterable[DataValue]:
    intersect = set(a)
    intersect.intersection_update(b)

    rtype = coerce_array(a, b)
    yield rtype(intersect)

@ophandler_typed(Operator.BitXor, Operand.Array, Operand.Array)
def operator_bitxor(ctx, a, b) -> Iterable[DataValue]:
    symdiff = set(a)
    symdiff.symmetric_difference_update(b)

    rtype = coerce_array(a, b)
    yield rtype(symdiff)