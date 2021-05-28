from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional
    from stackscript.parser import SymbolMeta
    from stackscript.runtime import ContextFrame
    from stackscript.values import DataValue


class ScriptError(Exception):
    """Raised when there is a problem with an executing script (not the runtime!)"""

    def __init__(self, message: str, meta: Optional[SymbolMeta] = None, ctx: Optional[ContextFrame] = None):
        self.meta = meta
        self.ctx = ctx
        super().__init__(message)

    def __str__(self) -> str:
        message = [ super().__str__(), str(self.meta) ]
        return '\n'.join(message)

class ScriptSyntaxError(ScriptError):
    pass

class ScriptAssignmentError(ScriptError):
    pass

class ScriptOperandError(ScriptError):
    def __init__(self, message: str, *operands: DataValue, meta: Optional[SymbolMeta] = None, ctx: Optional[ContextFrame] = None):
        self.operands = operands
        super().__init__(message, meta, ctx)

    def __str__(self) -> str:
        message = [ super().__str__(), ', '.join(str(type(o)) for o in self.operands),  str(self.meta) ]
        return '\n'.join(message)

class ScriptIndexError(ScriptError):
    def __init__(self, message: str, container: DataValue, index: DataValue, meta: Optional[SymbolMeta] = None, ctx: Optional[ContextFrame] = None):
        self.container = container
        self.index = index
        super().__init__(message, meta, ctx)

class ScriptNameError(ScriptError):
    def __init__(self, message: str, name: str, meta: Optional[SymbolMeta] = None, ctx: Optional[ContextFrame] = None):
        self.name = name
        super().__init__(message, meta, ctx)