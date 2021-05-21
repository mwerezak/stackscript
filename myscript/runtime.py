""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from typing import Union, Optional, Iterable, Tuple, MutableSequence, MutableMapping
    from myscript.lang import DataType
    from myscript.lexer import Lexer, Token


# Lexer/Tokenizer
class DataValue(NamedTuple):
    type: DataType
    value: Any


class ScriptRuntime:
    stack: MutableSequence[DataValue]
    namespace: MutableMapping[str, DataValue]

    def __init__(self, lexer: Lexer):
        self._lexer = lexer
        
        self.stack = []
        self.namespace = {}

    def eval_primative(expr: Token) -> DataValue:
        pass

    def exec(prog: Iterable[Token]) -> None:
        pass


if __name__ == '__main__':
    from myscript.lexer import Lexer

    tests = [
        """1 1+ """,
    ]

    lexer = Lexer()
    for test in tests:
        print(test)

        lexer.input(test)
        for tok in lexer.get_tokens():
            print(tok)
