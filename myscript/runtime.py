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
    from typing import Any, Union, Optional, Iterator, Iterable, Sequence, MutableSequence, ChainMap
    from myscript.parser import Parser, Lexer, Token, Literal
    from myscript.values import DataValue




class ContextFrame:
    _stack: MutableSequence[DataValue]
    _namespace: ChainMap[str, DataValue]
    def __init__(self, runtime: ScriptRuntime, parent: Optional[ContextFrame]):
        self.runtime = runtime
        self.parent = parent
        self._stack = deque()  # index 0 is the TOP

        if parent is None:
            self._namespace = chainmap()
        else:
            self._namespace = parent._namespace.new_child()

    def create_child(self) -> ContextFrame:
        """Create a new child frame from this one."""
        return ContextFrame(self.runtime, self)

    def get_namespace(self) -> Mapping[str, DataValue]:
        return self._namespace

    def push_stack(self, value: DataValue) -> None:
        self._stack.appendleft(value)

    def pop_stack(self) -> DataValue:
        if len(self._stack) == 0:
            raise ScriptStackError('stack is empty')
        return self._stack.popleft()

    def iter_stack(self) -> Iterator[DataValue]:
        """Iterate starting from the top and moving down."""
        return iter(self._stack)

    def iter_stack_result(self) -> Iterator[DataValue]:
        """Iterate the stack contents as if copying results to another context."""
        return reversed(self._stack)

    def peek_stack(self, idx: int) -> DataValue:
        return self._stack[idx]

    def insert_stack(self, idx: int, value: DataValue) -> None:
        self._stack.insert(idx, value)

    def delete_stack(self, idx: int) -> None:
        del self._stack[idx]

    def exec(self, prog: Union[str, Iterable[Token]]) -> None:
        if isinstance(prog, str):
            parser = self.runtime.parser.clone()
            parser.input(prog)
            prog = parser.get_tokens()
        self._exec(prog)

    def _exec(self, prog: Iterable[Token]) -> None:
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
            if name not in self._namespace:
                raise ScriptError(f"could not resolve name '{name}'", token)
            return _namespace[name]
        if token.is_literal():
            if token.item.type == DataType.Array:
                return self._eval_array(token)
            return token.item.get_value()
        raise ScriptError(f"could not evaluate token", token)

    def _eval_array(self, token: Token) -> DataValue:
        # create a new context in which to evaluate the array
        array_ctx = self.create_child()
        array_ctx.exec(token.item.value)
        return ArrayValue(list(array_ctx.iter_stack_result()))


class ScriptRuntime:
    def __init__(self, parser: Parser):
        self.parser = parser
        self.root = ContextFrame(self, None)

    def exec(self, text: str) -> None:
        self.parser.input(text)
        self.root.exec(self.parser.get_tokens())
        
        for i, value in enumerate(self.root.iter_stack()):
            print(f"[{i}]: {value}")

    def get_globals() -> Mapping[str, DataValue]:
        return self.root.get_namespace()


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