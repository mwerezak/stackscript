from __future__ import annotations
from typing import TYPE_CHECKING, cast, Iterable, Sequence

from stackscript.runtime import CtxFlags
from stackscript.values import CtxExecValue, BlockValue, StringValue, TupleValue, SequenceValue, BindingTarget
from stackscript.parser import Identifier, Literal
from stackscript.exceptions import ScriptOperandError, ScriptSyntaxError, ScriptAssignmentError

from stackscript.operators.defines import Operator, Operand
from stackscript.operators.overloading import ophandler_untyped, ophandler_typed, ophandler_permute


if TYPE_CHECKING:
    from stackscript.values import ScriptValue
    from stackscript.runtime import ContextFrame


###### Quote

@ophandler_untyped(Operator.Quote, 1)
def operator_quote(ctx, o) -> Iterable[ScriptValue]:
    yield StringValue(o.format())


###### Dup

@ophandler_untyped(Operator.Dup, 0)
def operator_dup(ctx: ContextFrame) -> Iterable[ScriptValue]:
    if ctx.stack_size() > 0:
        return [ctx.peek_stack()]

    if ctx.parent is None:
        raise ScriptOperandError('not enough operands')
    return [ctx.parent.peek_stack()]


###### Drop

@ophandler_untyped(Operator.Drop, 1)
def operator_drop(ctx, value) -> Iterable[ScriptValue]:
    return ()  # no-op, just drop the value

###### Rotate

# move the ith stack element to top
# @ophandler_typed(Operator.Rotate, Operand.Number)
# def operator_rotate(ctx, index):
#     item = ctx.peek_stack(index.value)
#     ctx.remove_stack(index.value)
#     yield item

###### Break

@ophandler_untyped(Operator.Break, 0)
def operator_break(ctx):
    ctx.clear_stack()
    return ()

###### Evaluate

# "unpack" a block by executing it in the current context
@ophandler_typed(Operator.Eval, Operand.Exec)
def operator_eval(ctx, block: CtxExecValue) -> Iterable[ScriptValue]:
    block.apply_exec(ctx)
    return ()

# execute a block a certain number of times in the current context
@ophandler_permute(Operator.Mul, Operand.Number, Operand.Exec)
def operator_repeat(ctx, repeat, block: CtxExecValue) -> Iterable[ScriptValue]:
    for i in range(repeat.value):
        block.apply_exec(ctx)
    return ()

# evaluate a string directly in the current context
@ophandler_typed(Operator.Eval, Operand.String)
def operator_eval(ctx: ContextFrame, text) -> Iterable[ScriptValue]:
    syms = ctx.runtime.eval_script(text.value)
    ctx.exec(syms)
    return ()


###### Invoke/Call

# invoke a block, giving it the top item on the stack
@ophandler_untyped(Operator.Mod, 2)
def operator_invoke(ctx: ContextFrame, arg, block) -> Iterable[ScriptValue]:
    if not isinstance(block, CtxExecValue):
        raise ScriptOperandError('unsupported operand type', block)
    sub_ctx = ctx.create_child()
    sub_ctx.push_stack(arg)
    block.apply_exec(sub_ctx)
    yield from sub_ctx.iter_stack_result()

# like invoke, but the results are collected into a tuple
@ophandler_untyped(Operator.BitOr, 2)
def operator_compose(ctx: ContextFrame, arg, block) -> Iterable[ScriptValue]:
    if not isinstance(block, CtxExecValue):
        raise ScriptOperandError('unsupported operand type', block)
    sub_ctx = ctx.create_child()
    sub_ctx.push_stack(arg)
    block.apply_exec(sub_ctx)
    yield TupleValue(sub_ctx.iter_stack_result())


###### Assignment

@ophandler_untyped(Operator.Assign, 0)
def operator_assign(ctx: ContextFrame) -> Iterable[ScriptValue]:
    if ctx.stack_size() < 1:
        raise ScriptOperandError('not enough operands')

    try:
        next_sym = next(ctx.get_symbol_iter())
    except StopIteration:
        raise ScriptSyntaxError('invalid syntax')

    value = ctx.peek_stack()
    if isinstance(next_sym, Identifier):
        ctx.namespace_bind_value(next_sym.name, value)
        return ()

    # multiple assignment
    if isinstance(next_sym, Literal):
        target = ctx.eval(next_sym)
        if isinstance(target, BlockValue):
            _do_block_assignment(ctx, value, target)
            return ()

    raise ScriptOperandError('invalid operands for assignment')

def _do_block_assignment(ctx: ContextFrame, value: ScriptValue, block: BlockValue) -> None:
    # first, execute the block in an assignment context and get the result
    sub_ctx = ctx.create_child(CtxFlags.BlockAssignment)
    sub_ctx.exec(block)
    names = list(sub_ctx.iter_stack_result())

    if not all(isinstance(name, BindingTarget) for name in names):
        raise ScriptAssignmentError('cannot assign to a non-identifier')

    names = cast(Sequence[BindingTarget], names)
    len_names = len(names)
    if len_names == 0:
        pass  # no need to do anything
    elif len_names == 1:
        name = names[0]
        name.bind_value(ctx, value)
    else:
        ## multiple assignment
        if not isinstance(value, SequenceValue):
            raise ScriptAssignmentError(f"value '{value}' does not support multiple assignment")

        values = list(value)
        len_values = len(values)
        if len_values != len_names:
            msg = 'not enough' if len_values < len_names else 'too many'
            raise ScriptAssignmentError(f'{msg} values to unpack (expected {len_names}, got {len_values})')

        for name, value in zip(names, values):
            name.bind_value(ctx, value)
