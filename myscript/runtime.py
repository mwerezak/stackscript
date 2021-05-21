""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from collections import deque, ChainMap as chainmap
from typing import TYPE_CHECKING, NamedTuple

from myscript.lang import DataType
from myscript.values import ArrayValue
from myscript.errors import ScriptError
from myscript.operator import apply_operator

if TYPE_CHECKING:
    from typing import Any, Optional, Iterator, Iterable, Sequence, MutableSequence, ChainMap
    from myscript.parser import Parser, Lexer, Token, Literal
    from myscript.values import DataValue




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
        if len(self.stack) == 0:
            raise ScriptStackError('stack is empty')
        return self.stack.pop()

    def peek_stack(self) -> Iterator[DataValue]:
        return reversed(self.stack)

    def exec(self, prog: Iterable[Token]) -> None:
        for token in prog:
            try:
                if token.is_operator():
                    apply_operator(self, token.item)
                else:
                    value = self._eval(token)
                    self.push_stack(value)
            except ScriptError as e:
                e.token = token
                raise e
            except Exception as e:
                raise ScriptError("error executing program", token) from e

    def eval(self, token: Token) -> DataValue:
        if token.is_operator():
            raise ValueError("cannot evaluate operator", token.item)
        return self._eval(token)

    def _eval(self, token: Token) -> DataValue:
        if token.is_identifier():
            name = token.item.name
            if name not in self.namespace:
                raise ScriptError(f"could not resolve name '{name}'", token)
            return namespace[name]
        if token.is_literal():
            if token.item.type == DataType.Array:
                return self._eval_array(token)
            return token.item.get_value()
        raise ScriptError(f"could not evaluate token", token)

    def _eval_array(self, token: Token) -> DataValue:
        # create a new context in which to evaluate the array
        array_ctx = ContextFrame(self)
        array_ctx.exec(token.item.value)
        return ArrayValue(list(array_ctx.stack))


class ScriptRuntime:
    def __init__(self, parser: Parser):
        self.parser = parser
        self.root = ContextFrame()

    def exec(self, text: str) -> None:
        self.parser.input(text)
        self.root.exec(self.parser.get_tokens())
        
        # print(self.root.stack)
        for i, value in enumerate(reversed(self.root.stack)):
            print(f"[{i}]: {value}")



if __name__ == '__main__':
    from myscript.parser import Parser

    tests = [
        """1 1+ """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] + """,
        """ { -1 5 * [ 'step' ] + }! """,
    ]

    parser = Parser()
    for test in tests:
        print('>>>', test)

        runtime = ScriptRuntime(parser)
        runtime.exec(test)


"""
{ #method 1
    .
    {. 1- factorial*} {;1} if
}:factorial;

{ #method 2
    :x;
    0:i;
    1
    {i x<} {i 1+:i *} while
}:factorial;

{1+,1>{*}*}:factorial; 5 factorial -> 120 #method 3
"""