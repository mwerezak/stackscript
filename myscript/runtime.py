""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from collections import deque, ChainMap as chainmap
from typing import TYPE_CHECKING

from myscript.parser import SymbolType, LiteralType, Lexer, Parser
from myscript.exceptions import ScriptError
from myscript.opimpl import apply_operator, OperandError

from myscript.values import (
    BoolValue, IntValue, FloatValue, StringValue, ArrayValue, BlockValue
)

if TYPE_CHECKING:
    from typing import Any, Optional, Callable, Iterator, Iterable, Mapping, ChainMap, Deque
    from myscript.parser import ScriptSymbol, Identifier, Literal, OperatorSym
    from myscript.values import DataValue, BoolValue


def _eval_bool(value: bool) -> BoolValue:
    return BoolValue.TRUE if value else BoolValue.FALSE

_simple_literals: Mapping[LiteralType, Callable[[Any], DataValue]] = {
    LiteralType.Bool    : _eval_bool,
    LiteralType.Integer : IntValue,
    LiteralType.Float   : FloatValue,
    LiteralType.String  : StringValue,
    LiteralType.Block   : BlockValue,
}

class ContextFrame:
    _stack: Deque[DataValue]
    _namespace: ChainMap[str, DataValue]
    def __init__(self, runtime: ScriptRuntime, parent: Optional[ContextFrame], contents: Iterable[DataValue] = ()):
        self.runtime = runtime
        self.parent = parent
        self._stack = deque(contents)  # index 0 is the TOP

        if parent is None:
            self._namespace = chainmap()
        else:
            self._namespace = parent._namespace.new_child()

    def create_child(self, contents: Iterable[DataValue] = ()) -> ContextFrame:
        """Create a new child frame from this one."""
        return ContextFrame(self.runtime, self, contents)

    def get_namespace(self) -> Mapping[str, DataValue]:
        return self._namespace

    def exec(self, prog: Iterable[ScriptSymbol]) -> None:
        for sym in prog:
            if sym.get_type() == SymbolType.Operator:
                sym: OperatorSym
                try:
                    apply_operator(self, sym.operator)
                except OperandError as err:
                    message = ' '.join(str(o) for o in err.args)
                    raise ScriptError(message, sym.meta)

            else:
                value = self.eval(sym)
                self.push_stack(value)

    def execs(self, text: str) -> None:
        parser = self.runtime.create_parser()
        self.exec(parser.parse(text))

    ## Stack Operations
    ## TODO move these to EvalStack class?
    def push_stack(self, value: DataValue) -> None:
        self._stack.appendleft(value)

    def pop_stack(self) -> DataValue:
        if len(self._stack) == 0:
            raise ScriptError('stack is empty')
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

    def remove_stack(self, idx: int) -> None:
        del self._stack[idx]

    def clear_stack(self) -> None:
        self._stack.clear()

    ## Symbol Evaluation
    def eval(self, sym: ScriptSymbol) -> DataValue:
        sym_type = sym.get_type()
        if sym_type == SymbolType.Identifier:
            sym: Identifier
            value = self._namespace.get(sym.name)
            if value is None:
                raise ScriptError(f"could not resolve identifier '{sym.name}'", sym.meta)
            return value

        if sym_type == SymbolType.Literal:
            sym: Literal
            return self.eval_literal(sym)

        raise ValueError('cannot evaluate symbol', sym)

    def eval_literal(self, literal: Literal) -> DataValue:
        ctor = _simple_literals.get(literal.type)
        if ctor is not None:
            return ctor(literal.value)

        if literal.type == LiteralType.Array:
            return self._eval_array(literal)

        raise ValueError('could not evaluate literal', literal)

    def _eval_array(self, literal: Literal) -> DataValue:
        # create a new context in which to evaluate the array
        array_ctx = self.create_child()
        array_ctx.exec(literal.value)
        return ArrayValue(array_ctx.iter_stack_result())

    def __str__(self) -> str:
        return ' '.join(
            str(value) for value in self.iter_stack_result()
        )

    def format_stack(self) -> str:
        return '\n'.join(
            f"[{i}]: {value!r}"
            for i, value in enumerate(self.iter_stack())
        )



class ScriptParser:
    """Parse a block of code text into script symbols.

    This class encapsulates the Lexer held by the ScriptRuntime.
    It allows new ScriptParsers to be created on the fly in a somewhat more efficient manner."""

    _text: str
    def __init__(self, runtime: ScriptRuntime, lexer: Lexer):
        self.runtime = runtime
        self._lexer = lexer

    def parse(self, text: str) -> Iterator[ScriptSymbol]:
        self._text = text
        self._lexer.input(text)
        tokens = self._lexer.get_tokens()
        parser = Parser(tokens)
        yield from parser.get_symbols()

class ScriptRuntime:
    def __init__(self, lexer: Optional[Lexer] = None):
        self._lexer = lexer or Lexer()
        self.root = ContextFrame(self, None)

    def create_parser(self) -> ScriptParser:
        return ScriptParser(self, self._lexer.clone())

    def get_globals(self) -> Mapping[str, DataValue]:
        return self.root.get_namespace()

    def run_script(self, text: str) -> None:
        parser = ScriptParser(self, self._lexer)
        sym = parser.parse(text)
        self.root.exec(sym)

        print(self.root.format_stack())


if __name__ == '__main__':
    tests = [
        """1 1+ """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] + """,
        """ { -1 5 * [ 'step' ] + }! """,
    ]

    for test in tests:
        print('>>>', test)
        rt = ScriptRuntime()
        rt.run_script(test)


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