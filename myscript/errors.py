""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class ScriptError(Exception):
    """Raised when there is a problem with an executing script (not the runtime!)"""

    def __init__(self, message: str, lineno: int, lexpos: int):
        self.lineno = lineno
        self.lexpos = lexpos
        super().__init__(message)

    def __str__(self) -> str:
        return '\n'.join([
            super().__str__(),
            f"lineno: {self.lineno}", 
            f"pos: {self.lexpos}",
        ])

class ScriptSyntaxError(ScriptError): pass

class ScriptNameError(ScriptError): pass

class ScriptTypeError(ScriptError): pass
