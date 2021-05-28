from enum import Flag, auto

class ContextFlags(Flag):
    SharedNamespace = auto()
    BlockAssignment = auto()