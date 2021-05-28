from enum import Flag, auto

class CtxFlags(Flag):
    SharedNamespace = auto()
    BlockAssignment = auto()