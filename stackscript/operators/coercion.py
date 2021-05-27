from __future__ import annotations
from typing import TYPE_CHECKING

from stackscript.values import IntValue, FloatValue, ArrayValue, TupleValue
from stackscript.operators.defines import Operand

if TYPE_CHECKING:
    from typing import Type
    from stackscript.values import DataValue



COERCION_RULES = {
    Operand.Number : [ FloatValue, IntValue ],
    Operand.Array  : [ ArrayValue, TupleValue ],
}

def coerce_operands(optype: Operand, *operands: DataValue) -> Type[DataValue]:
    for priority_type in COERCION_RULES[optype]:
        if any(isinstance(o, priority_type) for o in operands):
            return priority_type

    msg = ', '.join(str(o) for o in operands)
    raise ValueError(f'incorrect operands for optype {optype}: ' + msg)


def coerce_array(*operands: DataValue) -> Type[DataValue]:
    return coerce_operands(Operand.Array, *operands)

def coerce_number(*operands: DataValue) -> Type[DataValue]:
    return coerce_operands(Operand.Number, *operands)