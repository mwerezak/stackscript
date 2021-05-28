from enum import Flag, auto

class CtxFlags(Flag):
    ShareNamespace  = auto()
    ShareStack      = auto()
    BlockAssignExpr = auto()