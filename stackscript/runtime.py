from __future__ import annotations

from collections import deque, ChainMap as chainmap
from typing import TYPE_CHECKING

from stackscript.parser import LiteralType, Lexer, Parser, Identifier, Literal, OperatorSym
from stackscript.exceptions import ScriptError
from stackscript.ophandlers import apply_operator, OperandError

from stackscript.values import (
    BoolValue, IntValue, FloatValue, StringValue, ArrayValue, BlockValue
)

if TYPE_CHECKING:
    from typing import Any, Optional, Callable, Iterator, Iterable, Mapping, MutableMapping, ChainMap, Deque
    from stackscript.parser import ScriptSymbol
    from stackscript.values import DataValue, BoolValue


_simple_literals: Mapping[LiteralType, Callable[[Any], DataValue]] = {
    LiteralType.Bool    : BoolValue.get_value,
    LiteralType.Integer : IntValue,
    LiteralType.Float   : FloatValue,
    LiteralType.String  : StringValue,
    LiteralType.Block   : BlockValue,
}

class ContextFrame:
    _stack: Deque[DataValue]
    _namespace: ChainMap[str, DataValue]
    _block: Iterator[ScriptSymbol] = None
    def __init__(self, runtime: ScriptRuntime, parent: Optional[ContextFrame], share_namespace: bool = False):
        self.runtime = runtime
        self.parent = parent
        self._stack = deque()  # index 0 is the TOP

        if parent is None:
            self._namespace = chainmap()
        elif share_namespace:
            self._namespace = parent._namespace
        else:
            self._namespace = parent._namespace.new_child()

    def create_child(self, *, share_namespace: bool = False) -> ContextFrame:
        """Create a new child frame from this one."""
        return ContextFrame(self.runtime, self, share_namespace)

    def get_namespace(self) -> MutableMapping[str, DataValue]:
        return self._namespace

    def get_symbol_iter(self) -> Iterator[ScriptSymbol]:
        return self._block

    def execs(self, text: str) -> None:
        parser = self.runtime.create_parser()
        self.exec(parser.parse(text))

    def exec(self, prog: Iterable[ScriptSymbol]) -> None:
        self._block = iter(prog)
        for sym in self._block:
            if isinstance(sym, OperatorSym):
                self._apply_operator(sym)
            else:
                value = self.eval(sym)
                self.push_stack(value)

    def _apply_operator(self, opsym: OperatorSym) -> None:
        try:
            apply_operator(self, opsym.operator)
        except OperandError as err:
            operands = ', '.join(value.name for value in err.operands)
            message = f"{err.message}: {operands}"
            raise ScriptError(message, opsym.meta) from None

    ## Symbol Evaluation
    def eval(self, sym: ScriptSymbol) -> DataValue:
        if isinstance(sym, Identifier):
            value = self._namespace.get(sym.name)
            if value is None:
                raise ScriptError(f"could not resolve identifier '{sym.name}'", sym.meta)
            return value

        if isinstance(sym, Literal):
            if sym.type == LiteralType.Array:
                array_ctx = self.create_child()
                array_ctx.exec(sym.value)
                return ArrayValue(array_ctx.iter_stack_result())

            ctor = _simple_literals.get(sym.type)
            if ctor is not None:
                return ctor(sym.value)

        raise ValueError('cannot evaluate symbol', sym)

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

    def peek_stack(self, idx: int = 0) -> DataValue:
        return self._stack[idx]

    def insert_stack(self, idx: int, value: DataValue) -> None:
        self._stack.insert(idx, value)

    def remove_stack(self, idx: int) -> None:
        del self._stack[idx]

    def clear_stack(self) -> None:
        self._stack.clear()

    def stack_size(self) -> int:
        return len(self._stack)

    def __str__(self) -> str:
        return ' '.join(
            str(value) for value in self.iter_stack_result()
        )

    def format_stack(self) -> str:
        return '\n'.join(
            f"[{i}]: {value.format()}"
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
        """ 'c' ['a' 'b'] ++ """,
        """ -1 5 * { [ 'step' ] ++ }! """,
        """ [ 3 2]  [ 1 'b' { 'c' 'd' } ] """,
        """ [ 1 'b' [ 3 2 ]`  { 'c' 'd' } ]`  """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] ++ """,
        """ [] { -1 5 * [ 'step' ] ++ }! """,
        """ [ 1 '2 3 -'! 4 5 6 7 + ] """,
        """ [1 2 3 4 5 6] 2$ """,
        # """ 1 2 3 4 5 6 2@ """,
        """ 'str' 3 * 2 ['a' 'b' 'c'] *""",
        # """ 1 2 3 4 5 6 ,,, [] { 1@ + } 3* . # """,
        """ [ 1 2 3 ] {2*}/ ~ """,
        # """ [] [ 1 2 3 ] {2* 1@ +}% """,
        """ [1 2 3 4 5 6] [2 4 5] -""",
        """ [7 6; 5 4 3 2 1] {3 <=}/ 0 false = """,
        """ [ 1 2 3 ] {2*}/ . [ 2 4 6 ] = """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] | """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] & """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] ^ """,
        """ 'a' not """,
        """ 'abc': mystr; [mystr mystr mystr] """,
        """
        {
            :n;  // assign the argument to "n"
            n 0 <=
            1
            { n 1- factorial! n * } if
        }: factorial;
        
        5 factorial!
        """,
        """
        {
            . 0 ~= {. 1- factorial! *} {;1} if
        }: factorial;
        5 factorial!
        """,
        """ 5 { 1- .. 0 > } do, """,
        """ 5:n; { n 1- :n 0 >= } { n` } while """,
        """ { 'a' 'b' + } { 1 - 3 } + """  # concat blocks
    ]

    for test in tests:
        print('>>>', test)
        rt = ScriptRuntime()
        rt.run_script(test)
