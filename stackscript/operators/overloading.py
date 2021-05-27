from __future__ import annotations

import itertools
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple, Iterable

from stackscript.values import DataValue
from stackscript.exceptions import ScriptOperandError
from stackscript.operators.defines import Operator, Operand

if TYPE_CHECKING:
    from typing import Any, Union, Callable, Sequence, MutableMapping
    from stackscript.runtime import ContextFrame

    Signature = Sequence[Operand]
    OperatorFunc = Callable[[ContextFrame, ...], Iterable[DataValue]]


# map operator -> signature -> operator data
OP_REGISTRY: MutableMapping[Operator, MutableMapping[Union[Signature, int], OperatorOverload]] = defaultdict(dict)
OP_ARITY: MutableMapping[Operator, int] = defaultdict(int)


class OperatorOverload(NamedTuple):
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

def _search_registery(op: Operator, ctx: ContextFrame) -> OperatorOverload:
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
            raise ScriptOperandError("invalid operands", *args)

    raise ScriptOperandError("not enough operands")

def _register_operator(opdata: OperatorOverload) -> None:
    registry = OP_REGISTRY[opdata.op]

    signature = opdata.signature
    if signature in registry:
        raise ValueError(f"signature {signature} is already registered for {opdata.op}")

    registry[signature] = opdata
    OP_ARITY[opdata.op] = max(OP_ARITY[opdata.op], opdata.arity)


###### Overload Decorators
# note: typed ophandlers take precedence over untyped

def ophandler_untyped(op: Operator, arity: int):
    def decorator(func: OperatorFunc):
        opdata = OperatorOverload(op, arity, arity, func)
        _register_operator(opdata)
        return func
    return decorator

def ophandler_typed(op: Operator, *signature: Operand):
    def decorator(func: OperatorFunc):
        opdata = OperatorOverload(op, len(signature), signature, func)
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
            opdata = OperatorOverload(op, len(signature), signature, reorder)
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

