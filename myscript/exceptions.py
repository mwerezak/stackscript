""" An interpreter for a GolfScript-like language.
| Author: Mike Werezak <mwerezak@gmail.com>
| Created: 2021/05/21
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional
    from myscript.parser import SymbolMeta


class ScriptError(Exception):
    """Raised when there is a problem with an executing script (not the runtime!)"""

    def __init__(self, message: str, meta: Optional[SymbolMeta] = None):
        self.meta = meta
        super().__init__(message)

    def __str__(self) -> str:
        message = [ super().__str__(), str(self.meta) ]
        return '\n'.join(message)

        