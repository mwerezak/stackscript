from __future__ import annotations
from typing import TYPE_CHECKING

from stackscript.values import IntValue, BoolValue, DataValue
from stackscript.exceptions import ScriptOperandError

from stackscript.operators.defines import Operator, Operand
from stackscript.operators.overloading import ophandler_typed
from stackscript.operators.coercion import coerce_number

if TYPE_CHECKING:
    from typing import Iterable
    from stackscript.values import ScriptValue


###### Basic Arithmetic

@ophandler_typed(Operator.Add, Operand.Number, Operand.Number)
def operator_add(ctx, a, b) -> Iterable[ScriptValue]:
    rtype = coerce_number(a, b)
    yield rtype(a.value + b.value)

@ophandler_typed(Operator.Sub, Operand.Number, Operand.Number)
def operator_sub(ctx, a, b) -> Iterable[ScriptValue]:
    rtype = coerce_number(a, b)
    yield rtype(a.value - b.value)

@ophandler_typed(Operator.Mul, Operand.Number, Operand.Number)
def operator_mul(ctx, a, b) -> Iterable[ScriptValue]:
    rtype = coerce_number(a, b)
    yield rtype(a.value * b.value)

@ophandler_typed(Operator.Div, Operand.Number, Operand.Number)
def operator_div(ctx, a, b) -> Iterable[ScriptValue]:
    rtype = coerce_number(a, b)
    yield rtype(a.value / b.value)

@ophandler_typed(Operator.Pow, Operand.Number, Operand.Number)
def operator_pow(ctx, a, b) -> Iterable[ScriptValue]:
    rtype = coerce_number(a, b)
    yield rtype(a.value ** b.value)

@ophandler_typed(Operator.Mod, Operand.Number, Operand.Number)
def operator_mod(ctx, a, b) -> Iterable[ScriptValue]:
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise ScriptOperandError("unsupported operand types", a, b)
    rtype = coerce_number(a, b)
    yield rtype(a.value % b.value)

###### Numeric Comparison

## Equality

@ophandler_typed(Operator.Equal, Operand.Number, Operand.Number)
def operator_equal(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(_test_numeric_equality(a, b))

@ophandler_typed(Operator.NE, Operand.Number, Operand.Number)
def operator_ne(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(not _test_numeric_equality(a, b))

def _test_numeric_equality(a: DataValue, b: DataValue):
    rtype = coerce_number(a, b)
    if rtype == IntValue:
        return a.value == b.value
    return abs(a.value - b.value) < 10**-9

## Inequalities

@ophandler_typed(Operator.LT, Operand.Number, Operand.Number)
def operator_lt(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a < b)

@ophandler_typed(Operator.LE, Operand.Number, Operand.Number)
def operator_le(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a <= b)

@ophandler_typed(Operator.GT, Operand.Number, Operand.Number)
def operator_gt(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a > b)

@ophandler_typed(Operator.GE, Operand.Number, Operand.Number)
def operator_ge(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a >= b)


###### Bitwise Operations

# bitwise not
@ophandler_typed(Operator.Invert, Operand.Number)
def operator_invert(ctx, a) -> Iterable[ScriptValue]:
    if not isinstance(a, IntValue):
        raise ScriptOperandError('unsupported operand type', a)
    yield IntValue(~a.value)

# bitwise and, or, xor
@ophandler_typed(Operator.BitAnd, Operand.Number, Operand.Number)
def operator_bitand(ctx, a, b) -> Iterable[ScriptValue]:
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise ScriptOperandError("unsupported operand types", a, b)
    yield IntValue(a.value & b.value)

@ophandler_typed(Operator.BitOr, Operand.Number, Operand.Number)
def operator_bitor(ctx, a, b) -> Iterable[ScriptValue]:
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise ScriptOperandError("unsupported operand types", a, b)
    yield IntValue(a.value | b.value)

@ophandler_typed(Operator.BitXor, Operand.Number, Operand.Number)
def operator_bitxor(ctx, a, b) -> Iterable[ScriptValue]:
    if not isinstance(a, IntValue) or not isinstance(b, IntValue):
        raise ScriptOperandError("unsupported operand types", a, b)
    yield IntValue(a.value ^ b.value)