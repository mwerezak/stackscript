from __future__ import annotations
from typing import TYPE_CHECKING

from stackscript import CtxFlags
from stackscript.values import BoolValue, CtxExecValue
from stackscript.exceptions import  ScriptOperandError

from stackscript.operators.defines import Operator, Operand
from stackscript.operators.overloading import ophandler_typed, ophandler_untyped

if TYPE_CHECKING:
    from typing import Iterable
    from stackscript.values import ScriptValue
    from stackscript.runtime import ContextFrame


###### Logical Operators

## Equality

@ophandler_untyped(Operator.Equal, 2)
def operator_equal(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a == b)

@ophandler_untyped(Operator.NE, 2)
def operator_ne(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a != b)

# logical not
@ophandler_untyped(Operator.Not, 1)
def operator_not(ctx, a) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(not bool(a))

# logical and, or, xor
@ophandler_typed(Operator.BitAnd, Operand.Bool, Operand.Bool)
def operator_bitand(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a.value & b.value)

@ophandler_typed(Operator.BitOr, Operand.Bool, Operand.Bool)
def operator_bitor(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a.value | b.value)

@ophandler_typed(Operator.BitXor, Operand.Bool, Operand.Bool)
def operator_bitxor(ctx, a, b) -> Iterable[ScriptValue]:
    yield BoolValue.get_value(a.value ^ b.value)


###### Control Flow / Short-circuiting logic

# helper
def _shortcircuit_eval(ctx: ContextFrame, o: ScriptValue, name: str) -> ScriptValue:
    if isinstance(o, CtxExecValue):
        sub_ctx = ctx.create_child(CtxFlags.ShareNamespace)
        o.apply_exec(sub_ctx)
        if sub_ctx.stack_size() != 1:
            raise ScriptOperandError(name + ' did not evaluate to a single value', o)
        o = sub_ctx.peek_stack()

    return o

## Short-Circuiting And

@ophandler_untyped(Operator.And, 2)
def operator_and(ctx: ContextFrame, a, b) -> Iterable[ScriptValue]:
    a = _shortcircuit_eval(ctx, a, 'left expression')

    if not bool(a):
        return [a]  # short-circuit!

    # right expression
    b = _shortcircuit_eval(ctx, b, 'right expression')

    return [b]


## Short-Circuiting Or

@ophandler_untyped(Operator.Or, 2)
def operator_or(ctx: ContextFrame, a, b) -> Iterable[ScriptValue]:
    a = _shortcircuit_eval(ctx, a, 'left expression')

    if bool(a):
        return [a]  # short-circuit!

    # right expression
    b = _shortcircuit_eval(ctx, b, 'right expression')

    return [b]


## Short-Circuiting Ternary-If

@ophandler_untyped(Operator.If, 3)
def operator_if(ctx: ContextFrame, cond, if_true, if_false) -> Iterable[ScriptValue]:
    cond = _shortcircuit_eval(ctx, cond, 'conditional expression')

    result = if_true if bool(cond) else if_false
    if isinstance(result, CtxExecValue):
        result.apply_exec(ctx)
        return ()
    return [result]


## While

@ophandler_typed(Operator.While, Operand.Exec, Operand.Exec)
def operator_while(ctx: ContextFrame, cond, body) -> Iterable[ScriptValue]:
    while bool(_shortcircuit_eval(ctx, cond, 'conditional expression')):
        ctx.exec(body)
    return ()


## Do / While

# keep executing a block in the current context as long as the top item is true
@ophandler_typed(Operator.Do, Operand.Exec)
def operator_do(ctx: ContextFrame, block) -> Iterable[ScriptValue]:
    ctx.exec(block)
    while bool(ctx.pop_stack()):
        ctx.exec(block)
    return ()

