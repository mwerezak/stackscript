from __future__ import annotations

import sys
import readline
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Optional, Iterator, Iterable, MutableSequence
    from stackscript.runtime import ScriptRuntime
    from stackscript.values import DataValue

class REPL:
    """Provide Read-Evaluate-Print-Loop functionality."""

    intro = (
        'Script interpreter interactive mode.\n'
        'Type /help or /? to list metacommands.\n'
    )
    prompt_default   = '>>> '
    prompt_multiline = '... '
    input_term = ';'
    cmd_prefix = '/' # prefix for REPL metacommands

    _inputlines: MutableSequence[str]
    def __init__(self, runtime: ScriptRuntime, *, stdout: Any = None):
        self.runtime = runtime
        self._exit = False
        self._stdout = stdout or sys.stdout

    def run(self, intro: Optional[str] = None) -> None:
        self._print(intro or self.intro)

        while not self._exit:
            ## Read
            stmt = self._read_statement()
            if not stmt:
                continue

            ## Evaluate
            runtime.clear_stack()
            runtime.run_script(stmt)

            ## Print
            output = self._format_stack(runtime.iter_stack())
            output = '\n'.join(output)
            if output:
                self._print(output)

    @staticmethod
    def _format_stack(values: Iterable[DataValue]) -> Iterator[str]:
        values = list(values)
        numvalues = len(values)
        if numvalues == 1:
            yield '] ' + values[0].format()
        elif numvalues > 1:
            fmt_len = len(str(numvalues-1))
            idxformat = f'[{{:0{fmt_len}}}] '
            for i, value in enumerate(values):
                yield idxformat.format(i) + value.format()

    def _read_statement(self) -> str:
        """ Read lines from input until a line that ends with the input terminator suffix is read (ignoring whitespace)."""
        inputlines = []

        while not self._exit:
            prompt = self.prompt_default if not len(inputlines) else self.prompt_multiline
            line = self._read_input(prompt)
            if line is None:
                continue

            if line.endswith(self.input_term):
                inputlines.append(line[:-len(self.input_term)])
                return '\n'.join(inputlines)

            inputlines.append(line)

    def _read_input(self, prompt: str) -> Optional[str]:
        try:
            line = input(prompt).rstrip()
        except EOFError:
            self._exit = True
            return None

        if line.startswith(self.cmd_prefix):
            cmd = line[len(self.cmd_prefix):].split(maxsplit=1)
            return self._dispatch_metacommand(cmd[0], cmd[1:])
        return line


    def _dispatch_metacommand(self, command, args) -> Optional[str]:
        # shortcut for help
        if command == '?':
            command = 'help'

        name = '_cmd_' + command
        cmdfunc = getattr(self, name, None)
        if cmdfunc is None:
            self._print(f"*** Unrecognized command '{command}'")
            return None
        return cmdfunc(args)

    def _print(self, *objects: Any) -> None:
        print(*objects, file=self._stdout)

    def _cmd_help(self, args) -> None:
        """List available commands with '/help' or detailed help with '/help <cmd>'."""
        if len(args):
            name = args[0]
            fname = '_cmd_' + args[0]
            cmdfunc = getattr(self, fname, None)
            if cmdfunc is None or cmdfunc.__doc__ is None:
                self._print(f"*** No help on '{name}'")
            else:
                self._print(cmdfunc.__doc__)
            return

        names = [
            name[len('_cmd_'):]
            for name in dir(self.__class__)
            if name.startswith('_cmd_')
        ]
        self._print("Available metacommands (type '/help cmd' for details):")
        for name in names:
            self._print(self.cmd_prefix + name)

    def _cmd_quit(self, args) -> None:
        """Quit the interpreter."""
        self._exit = True


if __name__ == '__main__':
    from stackscript.runtime import ScriptRuntime
    runtime = ScriptRuntime()
    repl = REPL(runtime)
    repl.run()

