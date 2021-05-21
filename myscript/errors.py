""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional
    from myscript.lexer import Token


class ScriptError(Exception):
    """Raised when there is a problem with an executing script (not the runtime!)"""

    def __init__(self, message: str, token: Optional[Token] = None):
        self.token = token
        super().__init__(message)

    def __str__(self) -> str:
        message = [ super().__str__() ]
        if self.token is not None:
            message.extend([
                f"token: {self.token}",
                f"lineno: {self.token.lineno}", 
                f"pos: {self.token.lexpos}",
            ])
        return '\n'.join(message)

        