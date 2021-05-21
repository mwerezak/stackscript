""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from collections import deque, ChainMap as chainmap
from typing import TYPE_CHECKING, NamedTuple

from myscript.lang import DataType
from myscript.errors import ScriptNameError
from myscript.operator import apply_operator

if TYPE_CHECKING:
    from typing import Any, Optional, Iterable, Sequence, MutableSequence, ChainMap
    from myscript.lexer import Lexer, Token, Literal


class DataValue(NamedTuple):
    type: DataType
    value: Any

    def __repr__(self) -> str:
        return f'<Value({self.type.name}: {self.value!r})>'

    def __str__(self) -> str:
        return str(self.value)


class ContextFrame:
    stack: MutableSequence[DataValue]
    namespace: ChainMap[str, DataValue]
    def __init__(self, parent: Optional[ContextFrame] = None):
        self.parent = parent
        self.stack = deque()
        self.namespace = (
            parent.namespace.new_child() 
            if parent is not None else chainmap()
        )

    def push_stack(self, value: DataValue) -> None:
        self.stack.append(value)

    def pop_stack(self) -> DataValue:
        return self.stack.pop()

    def exec(self, prog: Iterable[Token]) -> None:
        for token in prog:
            if token.is_operator():
                apply_operator(self, token.item)
            else:
                value = self._eval(token)
                self.push_stack(value)

    def eval(self, expr: Token) -> DataValue:
        if expr.is_operator():
            raise ValueError("cannot evaluate operator", expr.item)
        return self._eval(expr)

    def _eval(self, expr: Token) -> DataValue:
        if expr.is_identifier():
            name = expr.item.name
            if name not in self.namespace:
                raise ScriptNameError(f"could not resolve name '{name}'", expr.lineno, expr.lexpos)
            return namespace[name]
        if expr.is_literal():
            if expr.item.type == DataType.Array:
                return self._eval_array(expr.item)
            return DataValue(expr.item.type, expr.item.value)
        raise ScriptError(f"could not evaluate token", expr, expr.lineno, expr.lexpos)

    def _eval_array(self, expr: Literal) -> DataValue:
        # create a new context in which to evaluate the array
        array_ctx = ContextFrame(self)
        array_ctx.exec(expr.value)
        return DataValue(
            DataType.Array,
            list(array_ctx.stack),
        )


class ScriptRuntime:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.root = ContextFrame()

    def exec(self, text: str) -> None:
        self.lexer.input(text)
        self.root.exec(self.lexer.get_tokens())
        
        for i, value in enumerate(self.root.stack):
            print(f"[{i}]: {value!r}")


if __name__ == '__main__':
    from myscript.lexer import Lexer

    tests = [
        """1 1+ """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
    ]

    lexer = Lexer()
    for test in tests:
        print(test)

        runtime = ScriptRuntime(lexer)
        runtime.exec(test)
