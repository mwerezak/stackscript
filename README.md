# Title Goes Here

This an interpreter for an unnamed stack-based scripting language.

The interpreter is implemented in Python and very much incomplete. The whole project is a personal experiment. 

See the bottom of `stackscript/runtime.py` for example of usage. Or just run `python -m stackscript.runtime` from the repository root to see some examples.

Also included is a slightly modified version of PLY which I am using as the lexer. 
I plan to replace it with a simple regex-based lexer, as I'm not really doing anything fancy.

At the end of this readme is an operator reference.

## Usage
Python 3.8+ required.

At the command prompt, run `python interpreter.py`.

Or run `python interpreter.py --help` for command line options.

## TODO
- A proper name
- Actually load script files or run as a REPL.
- Prelude mechanism, so that a standard library of builtin names can be loaded into the global scope.
- A dictionary or mapping type.

## About the Language

I wanted to see how far I could get with designing a stack-based scripting language. As my guide my aim to make the language as expressive and easy to use as I can within the constraint of the language being stack-based in its syntax.

Also, this being my first step into the world of programming language design, I wanted something easy to start with and stack based languages are really easy to parse.

Other inspirations for this language come from Python, Lua, and a bit of Scheme/LISP.

The implementation is still incomplete, I've only started working on it this past week. But I've made a lot of progress so far and I really like the direction it's going.

Anyways, more about the language itself (still yet to be named):

Naturally since it is stack-based all expressions are RPN.

    >>> 3 2 * 4 +
    ] 10

You can assign values to identifiers using the assignment operator `:`.

    >>> [1 2 3 'a' 'b' 'c']: mylist

Right now the available data types are booleans, integers, floats, strings, lists, and blocks. The block type is really important so I will get back to that later.

In the future I'd like to have immutable and mutable flavours of lists.

I also want to add a Lua-inspired "table" mapping type that also supports Lua-style metatables. I think this will add a lot of *oomph* to the language without needing to add the weight of a fully-fledged object system.

Like Lua I plan to have a small closed set of types. I think you can do a lot with just lists, tables, and primitives.

Now, back to the "block" type. Blocks are containers that contain unexecuted code. These are very similar to "quotations" in Factor.

Blocks can be evaluated using either the invoke operator `/`, or the evaluate operator `!`. 

The `!` operator is the simplest, it just applies the contents of the block to the stack.

    >>> {.. *}: sqr;  // can be assigned to names, like any other value
    ...
    >>> 5 sqr!
    ] 25

Unlike `!`, the invoke operator `/` executes the block in a new "scope".


    >>> (1 2) twoargs/

...

    >>> {1 +}: add1;
    ...
    >>> 5 sqr/ add1/
    ] 26

Blocks are just values, so you can put them in lists, pass them when invoking another block, etc.

Another example, calculating the factorial.

    >>> {
    ...     .. 0 > { (.. 1-) factorial! * } { ;1 } if  // ternary if
    ... }: factorial;
    ...
    >>> (5) factorial/
    ] 120

There's an indexing operator `$` that replaces a list and an integer with the n-th item in the list.

    >>> ['a' 'b' 'c'] 1$
    ] 'a'

As well, I plan to add multiple assignment syntax for lists and tuples to make handling argument lists convenient.

    >>> {
    ...     :(first second third);
    ...
    ...     third first + second *
    ...
    ... }: example;
    ...
    >>> [3 4 5] example/
    ] 32



I imagine named arguments could be accomodated Lua-style by passing a single table as the argument.

## Operator Reference

Note that certain operators are *overloaded* and so may appear multiple times in the following tables.

### General
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| \`          | inspect     | 1      | "Quotes" a value, replacing it with a string that when evaluted produces the original value.
| .           | duplicate   | 1      | Copy the top value on the stack.
| ,           | drop        | 1      | Remove the top value from the stack.
| :&nbsp;\<name\> | assignment  | 1      | Assign the a value to a name, then push it back onto the stack.

### Arithmetic 
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| +           | add         | 2      | What you'd expect. Operates on two numbers.
| -           | subtract    | 2      | Ditto.
| *           | multiply    | 2      | Ditto.
| /           | divide      | 2      | Ditto.
| %           | mod         | 2      | Calculate the modulus. Operates on two integers.
| **          | pow         | 2      | Raise the first number to the power of the second.

### Bitwise
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| ~           | bitwise not | 1      | Inverts the bits of an integer.
| \|          | bitwise or  | 2      | What you'd expect. Operates on two integers.
| &           | bitwise and | 2      | Ditto.
| ^           | bitwise xor | 2      | Ditto.

Note: left and right bitshifts will be built-in functions, rather than having dedicated operators.

### Blocks
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| %           | eval        | 1      | Evaluate a block by executing it in the current scope. Stack concatentation, effectively.
| !           | invoke      | 2      | Takes an argument and a block, and executes the block in a new scope where the argument is the only visible element of the stack, then concatenates the results with the outer stack.
| \|          | compose     | 2      | Like call, except the results of executing the block are collected into a tuple.
| +           | concat      | 2      | Concatenate two blocks, producing a new block.

### Lists/Tuples
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| ~           | unpack      | 1      | Replace a list with its contents. Each item in the list is pushed onto the stack.
| <<          | collection  | 1      | Operates on an integer and collects the next n items on the stack into a tuple.
| #           | length      | 1      | Produce the size of the list
| $           | index       | 2      | Operates on a list and an integer. Replaces both with the n-th item in the list (starting at 1).
| +           | concat      | 2      | Concatentate two lists.
| -           | difference  | 2      | Remove all items present in the second list from the first list, then push the first list back onto the stack.
| \|          | union       | 2      | Replace two lists with their setwise union.
| &           | intersection | 2      | Replace two lists with their setwise intersection.
| ^           | symmetric difference | 2      | Replace two lists with their setwise symmetric difference.

### Strings
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| ~           | unpack      | 1      | Replace a string, pushing a sequence of strings, each containing a single character from the original, onto the stack.
| %           | eval        | 1      | Evaluate a string as script code.
| #           | length      | 1      | Produce the length of the string.
| $           | index       | 2      | Operates on a string and an integer. Replaces both with a string containing just the n-th character (starting at 1).
| +           | concat      | 2      | Concatentate two strings.

### Comparison
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| <           | less than   | 2      | Compare two numbers.
| <=          | less than or equal | 2      | Compare two numbers.
| >           | greater than   | 2      | Compare two numbers.
| >=          | greater than or equal | 2      | Compare two numbers.
| =           | equality    | 2      | Compare two values for equality. Lists are only equal if they are the same list object. Blocks are compared structurally.
| ~=          | inequality  | 2      | Equivalent to `= not`

### Logical Operators
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| not         | logical not | 1      | Coerces a value into a boolean then produces the inverse of that boolean.
| and         | short-circuiting and | 2   | If the first operand is logically false, it is pushed back onto the stack. Otherwise the second operand is pushed. If either operand is a block, it is executed in a new scope to produce a value (blocks that produce multiple values result in an error).
| or          | short-circuiting and | 2   | If the first operand is logically true, it is pushed back onto the stack. Otherwise the second operand is pushed. If either operand is a block, it is executed in a new scope to produce a value (blocks that produce multiple values result in an error).

### Conditional Operators
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| if          | ternary if  | 3      | If the first value is logically true, push the second value. Otherwise push the third value. If the value that would be pushed is a block, instead execute the block in the current scope.
| while       | while       | 2      | Operates on two blocks. Execute the first block in a new scope. If it results in a single value (multiple values result in an error) that is "truthy" execute the second block in the current scope. Repeat this until the first block yields a logically false value.
| do          | do .. while | 1      | Operates on a block. Execute the block in the current scope and then pop the top value. Repeat this as long as the popped value is logically true.
