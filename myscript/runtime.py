""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/20
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from lang import DataType
from lexer import Lexer, Token, SpecialToken

if TYPE_CHECKING:
    from typing import Union, Optional, Iterable, Tuple


# Lexer/Tokenizer

class ScriptRuntime:
    def __init__(self):
        self.stack = []

    def exec(prog: Iterable[Token]) -> None:
        pass


if __name__ == '__main__':

    tests = [
        """1 1+ """,
    ]

    for test in tests:
        print(test)

        lex = Lexer()
        lex.input(test)
        for tok in lex.get_tokens():
            print(tok)
