from __future__ import annotations

import argparse
from argparse import ArgumentParser
from typing import TYPE_CHECKING

from stackscript.runtime import ScriptRuntime
from stackscript.repl import REPL
from stackscript.values import TupleValue, StringValue

if TYPE_CHECKING:
    pass

cli = ArgumentParser(
    description = 'Stack-based script interpreter.',
)

cli.add_argument(
    '-i',
    action = 'store_true',
    help = 'enter interactive mode after running script',
    dest = 'interactive',
)

cli.add_argument(
    'file',
    nargs = '?',
    default = None,
    help = 'read program from script file',
)

cli.add_argument(
    'args',
    nargs = argparse.REMAINDER,
    help = 'arguments passed to program in argv',
)

def _load_script(path: str) -> str:
    with open(path, 'rt') as file:
        return file.read()

if __name__ == '__main__':
    args = cli.parse_args()

    runtime = ScriptRuntime()

    argv = TupleValue(StringValue(str(o)) for o in args.args)
    runtime.get_globals()['argv'] = argv

    if args.file is None:
        repl = REPL(runtime)
        repl.run()
    else:
        script = _load_script(args.file)
        if not args.interactive:
            runtime.run_script(script)
        else:
            repl = REPL(runtime)
            repl.run(script)
