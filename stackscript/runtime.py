from __future__ import annotations

from collections import deque, ChainMap as chainmap
from typing import TYPE_CHECKING

from stackscript.parser import LiteralType, Lexer, Parser, Identifier, Literal, OperatorSym
from stackscript.exceptions import ScriptError, ScriptNameError
from stackscript.ophandlers import apply_operator

from stackscript.values import (
    BoolValue, IntValue, FloatValue, StringValue, ArrayValue, TupleValue, BlockValue
)

if TYPE_CHECKING:
    from typing import (
        Any, Optional, Callable, Iterator, Iterable, Mapping, MutableMapping, ChainMap, Deque
    )
    from stackscript.parser import ScriptSymbol
    from stackscript.values import DataValue, BoolValue


_simple_literals: Mapping[LiteralType, Callable[[Any], DataValue]] = {
    LiteralType.Bool    : BoolValue.get_value,
    LiteralType.Integer : IntValue,
    LiteralType.Float   : FloatValue,
    LiteralType.String  : StringValue,
    LiteralType.Block   : BlockValue,
}

_compound_literals: Mapping[LiteralType, Callable[[Any], DataValue]] = {
    LiteralType.Array : ArrayValue,
    LiteralType.Tuple : TupleValue,
}

class ContextFrame:
    _stack: Deque[DataValue]  # index 0 is the TOP
    _namespace: ChainMap[str, DataValue]
    _block: Iterator[ScriptSymbol] = None
    def __init__(self, runtime: ScriptRuntime, parent: Optional[ContextFrame], share_namespace: bool = False):
        self.runtime = runtime
        self.parent = parent
        self._stack = deque()

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
            try:
                if isinstance(sym, OperatorSym):
                    apply_operator(self, sym.operator)
                else:
                    value = self.eval(sym)
                    self.push_stack(value)

            except ScriptError as err:
                if err.meta is None:
                    err.meta = sym.meta
                if err.ctx is None:
                    err.ctx = self
                raise

    ## Symbol Evaluation
    def eval(self, sym: ScriptSymbol) -> DataValue:
        if isinstance(sym, Identifier):
            value = self._namespace.get(sym.name)
            if value is None:
                raise ScriptNameError(f"could not resolve identifier '{sym.name}'", sym.name, meta=sym.meta)
            return value

        if isinstance(sym, Literal):
            # simple literals
            ctor = _simple_literals.get(sym.type)
            if ctor is not None:
                return ctor(sym.value)

            # compound literals
            ctor = _compound_literals.get(sym.type)
            if ctor is not None:
                array_ctx = self.create_child(share_namespace=True)
                array_ctx.exec(sym.value)
                return ctor(array_ctx.iter_stack_result())

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

    def format_stack(self, *,
                     fmt: str = '{{idx:0{idxlen}}}: {{value}}',
                     fmt_single: Optional[str] = None) -> Iterator[str]:

        values = list(self.iter_stack())
        numvalues = len(values)
        if numvalues == 1 and fmt_single is not None:
            fmt = fmt_single

        idxlen = len(str(numvalues))
        fmt = fmt.format(idxlen=idxlen)
        for idx, value in enumerate(values):
            yield fmt.format(idx=idx+1, value=value)


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

    def get_globals(self) -> MutableMapping[str, DataValue]:
        return self.root.get_namespace()

    def iter_stack(self) -> Iterator[DataValue]:
        return self.root.iter_stack()

    def clear_stack(self) -> None:
        self.root.clear_stack()

    def run_script(self, text: str) -> None:
        parser = ScriptParser(self, self._lexer)
        try:
            sym = parser.parse(text)
            self.root.exec(sym)
        except ScriptError as err:
            # TODO return an error data container and let the caller deal with it
            # from traceback import print_exc
            # print_exc()
            raise

    def format_stack(self, **kwargs: Any) -> Iterator[str]:
        return self.root.format_stack(**kwargs)

if __name__ == '__main__':
    tests = [
        """1 1+ """,
        """ [ 1 2 3 - 4 5 6 7 + ] """,
        """ 'c' ['a' 'b'] ++ """,
        """ -1 5 * { [ 'step' ] ++ }!! """,
        """ [ 3 2]  [ 1 'b' { 'c' 'd' } ] """,
        """ [ 1 'b' [ 3 2 ]`  { 'c' 'd' } ]`  """,
        """ [] { -1 5 * [ 'step' ] ++ }!! """,
        """ [ 1 '2 3 -'!! 4 5 6 7 + ] """,
        """ [1 2 3 4 5 6] 2$ """,
        # """ 1 2 3 4 5 6 2@ """,
        """ 'str' 3 * 2 ['a' 'b' 'c'] *""",
        # """ 1 2 3 4 5 6 ,,, [] { 1@ + } 3* . # """,
        """ [ 1 2 3 ] {2*}! ~ """,
        # """ [] [ 1 2 3 ] {2* 1@ +}% """,
        """ [1 2 3 4 5 6] [2 4 5] -""",
        # """ [7 6; 5 4 3 2 1] {3 <=} map 0 false = """,
        """ [ 1 2 3 ] {2*}! .. [ 2 4 6 ] = """,
        """ [ 1 3 4 ] [ 7 3 1 2 ] | """,
        """ [ 1 3 4 ] ( 7 3 1 2 ) & """,
        """ ( 1 3 4 ) ( 7 3 1 2 ) ^ """,
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
            .. 0 = 
            {;1}
            {.. 1- factorial! *} if
        }: factorial;
        5 factorial!
        """,
        """ 5 { 1- .. 0 > } do, """,
        """ 5:n; { n 1- :n 0 >= } { n` } while """,
        """ { 'a' 'b' + } { 1 - 3 } + """  # concat blocks
        
        """ ( 1 2 3 - 4 5 6 7 + ) """,
        """ 'c' ('a' 'b') ++ """,
        """ () { -1 5 * [ 'step' ] ++ }! """,
        """ ( 1 '2 3 -'! 4 5 6 7 + ) """,
        """ (1 2 3 4 5 6) 2$ """,
        # """ 1 2 3 4 5 6 2@ """,
        """ 'str' 3 * 2 ('a' 'b' 'c') *""",
        # """ 1 2 3 4 5 6 ,,, [] { 1@ + } 3* . # """,
        """ ( 1 2 3 ) {2*}! ~ """,
        # """ [] [ 1 2 3 ] {2* 1@ +}% """,
        """ (1 2 3 4 5 6) [2 4 5] -""",
        # """ ( 1 2 3 ) {2*} map!! .. [ 2 4 6 ] = """,
    ]

    tests = [
        """
        {~ .. * 1 -}: sqrsub1;
        
        {
            ~ .. 0 <= 
            {; 1}
            {.. 1- 1<< factorial! *} if
        }: factorial;
        (5)factorial|sqrsub1!
        """,
        """ 2 4 'a' 8 [2] 'c' 5<< """,
    ]

    for test in tests:
        print('>>>', test)
        rt = ScriptRuntime()
        rt.run_script(test)
        print('\n'.join(rt.format_stack()))

