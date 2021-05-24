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
    '-d',
    action = 'store_true',
    help = 'print contents of stack on exit',
    dest = 'dump_stack',
)

input_group = cli.add_mutually_exclusive_group()
input_group.add_argument(
    '-c',
    help = 'program passed in as string at command line',
    metavar = 'cmd',
    dest = 'cmd',
)
input_group.add_argument(
    'file',
    nargs = '?',
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

    script = None
    if args.cmd is not None:
        script = args.cmd
    elif args.file is not None:
        script = _load_script(args.file)

    if script is None:
        repl = REPL(runtime)
        repl.run()
    elif args.interactive:
        repl = REPL(runtime)
        repl.run(script)
    else:
        runtime.run_script(script)

    if args.dump_stack:
        dump = '\n'.join(runtime.format_stack())
        print(dump)
