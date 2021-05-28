from __future__ import annotations
from typing import TYPE_CHECKING, cast, Iterable, Sequence

from stackscript.runtime import ContextFlags
from stackscript.values import BlockValue, StringValue, TupleValue, ContainerValue, BindingTarget
from stackscript.parser import Identifier, Literal
from stackscript.exceptions import ScriptOperandError, ScriptSyntaxError, ScriptAssignmentError

from stackscript.operators.defines import Operator, Operand
from stackscript.operators.overloading import ophandler_untyped, ophandler_typed, ophandler_permute


if TYPE_CHECKING:
    from stackscript.values import DataValue
    from stackscript.runtime import ContextFrame


###### Quote

@ophandler_untyped(Operator.Inspect, 1)
def operator_inspect(ctx, o) -> Iterable[DataValue]:
    yield StringValue(o.format())


###### Dup

@ophandler_untyped(Operator.Dup, 0)
def operator_dup(ctx: ContextFrame) -> Iterable[DataValue]:
    if ctx.stack_size() > 0:
        return [ctx.peek_stack()]

    if ctx.parent is None:
        raise ScriptOperandError('not enough operands')
    return [ctx.parent.peek_stack()]


###### Drop

@ophandler_untyped(Operator.Drop, 1)
def operator_drop(ctx, value) -> Iterable[DataValue]:
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
@ophandler_typed(Operator.Eval, Operand.Block)
def operator_eval(ctx, block) -> Iterable[DataValue]:
    ctx.exec(block)
    return ()

# execute a block a certain number of times in the current context
@ophandler_permute(Operator.Mul, Operand.Number, Operand.Block)
def operator_repeat(ctx, repeat, block) -> Iterable[DataValue]:
    for i in range(repeat.value):
        ctx.exec(block)
    return ()

# evaluate a string directly in the current context
@ophandler_typed(Operator.Eval, Operand.String)
def operator_eval(ctx, text) -> Iterable[DataValue]:
    ctx.execs(text.value)
    return ()


###### Invoke/Call

# invoke a block, giving it the top item on the stack
@ophandler_untyped(Operator.Mod, 2)
def operator_invoke(ctx: ContextFrame, arg, block) -> Iterable[DataValue]:
    if not isinstance(block, BlockValue):
        raise ScriptOperandError('unsupported operand type', block)
    sub_ctx = ctx.create_child()
    sub_ctx.push_stack(arg)
    sub_ctx.exec(block)
    yield from sub_ctx.iter_stack_result()

# like invoke, but the results are collected into a tuple
@ophandler_untyped(Operator.BitOr, 2)
def operator_compose(ctx: ContextFrame, arg, block) -> Iterable[DataValue]:
    if not isinstance(block, BlockValue):
        raise ScriptOperandError('unsupported operand type', block)
    sub_ctx = ctx.create_child()
    sub_ctx.push_stack(arg)
    sub_ctx.exec(block)
    yield TupleValue(sub_ctx.iter_stack_result())


###### Assignment

@ophandler_untyped(Operator.Assign, 0)
def operator_assign(ctx: ContextFrame) -> Iterable[DataValue]:
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

def _do_block_assignment(ctx: ContextFrame, value: DataValue, block: BlockValue) -> None:
    # first, execute the block in an assignment context and get the result
    sub_ctx = ctx.create_child(ContextFlags.BlockAssignment)
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
        if not isinstance(value, ContainerValue):
            raise ScriptAssignmentError(f"value '{value}' does not support multiple assignment")

        values = list(value)
        len_values = len(values)
        if len_values != len_names:
            msg = 'not enough' if len_values < len_names else 'too many'
            raise ScriptAssignmentError(f'{msg} values to unpack (expected {len_names}, got {len_values})')

        for name, value in zip(names, values):
            name.bind_value(ctx, value)
