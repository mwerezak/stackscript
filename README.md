# Title Goes Here

This an interpreter for an unnamed stack-based scripting language.

The interpreter is implemented in Python and is incomplete. The whole project is a personal experiment. 

Also included is a slightly modified version of PLY which I am using as the lexer. 
I plan to replace it with a simple regex-based lexer, as I'm not really doing anything fancy.

At the bottom of this readme is a complete operator reference. I might cut down on the number of operators once I implement some built-in functions.

## Usage
Python 3.8+ required.

At the command prompt, run `python interpreter.py`.

Or run `python interpreter.py --help` for command line options.

## TODO
- A proper name
- Prelude mechanism, so that a standard library of builtin names can be loaded into the global scope.
- A dictionary or mapping type.
- Come up with a way to import scripts into other scripts.

## About the Language

I wanted to see how far I could get with designing a stack-based scripting language. As my guide my aim to make the language as expressive and easy to use as I can within the constraint of the language being stack-based in its syntax.

Also, this being my first step into the world of programming language design, I wanted something easy to start with and stack based languages are really easy to parse.

Other inspirations for this language come from Python, Lua, and a bit of Scheme/LISP.

The implementation is still incomplete, I've only started working on it this past week. But I've made a lot of progress so far and I really like the direction it's going.

### Expressions and Assignment

Anyways, more about the language itself (still yet to be named):

Naturally since it is stack-based all expressions are RPN.

    >>> 3 2 * 4 +
    ] 10

You can assign values to identifiers (actually name binding) using the assignment operator `:`.

    >>> [1 2 3 'a' 'b' 'c']: mylist

Right now the available data types are booleans, integers, floats, strings, arrays, tuples, and blocks.

### Evaluation of Expressions and Operators

Whenever an expression is encountered, each symbol in the expression is applied to the stack.

- If the symbol is a literal, the literal value is pushed onto the stack.
- If the symbol is a name, the name is looked up to produce a value which is pushed onto the stack.
- If the symbol is an operator, the operator manipulates the stack in some way.

Operators can consume values from the stack, push values onto the stack, or do other things.
Many operators are overloaded, so the exact behavior will depend on the type of the first 1-3 items
on top of the stack, depending on arity.

A complete operator reference can be found at the bottom of this README.

### Blocks

Blocks are containers that contain unexecuted code. These are very similar to "quotations" in Factor.
Blocks are just values, so you can put them in lists, pass them when invoking another block, etc.

Blocks can be applied using either the invoke operator `!`, or the evaluate operator `%`. 

The evaluate `%` operator is the simplest, it just applies the contents of the block to the stack.

    >>> {.. *}: sqr;  // can be assigned to names, like any other value
    ...
    >>> 5 sqr%
    ] 25
    >>> '2 2 +'%  // can also evaluate strings
    ] 4

Unlike `%`, the invoke operator `!` executes the block in a new "scope".
This means that only the top item on the parent stack is visible to the inside of the block.
Also any names that are assigned inside the block remain local to the block.

Whenever a block is invoked in a new "scope", the expression inside the block is evaluated and
whatever remains on the stack after applying every symbol in the block is called the block's "results".
When using the `%` operator on a block, the results of the invocation are pushed back onto the parent
stack. Effectively, the child stack is concatenated onto the end of the parent.

An example, calculating the factorial:

    >>> {
    ...     .. 0 > { .. 1- factorial! * } { ;1 } if  // ternary if
    ... }: factorial;
    >>> 5 factorial!
    ] 120

To invoke a block with more than one value, an argument list or tuple can be used.

    >>> (1 2) twoargs!

To pass multiple results from one block directly into another, the composition operator `|` can be used. This operator actually functions just like `!`, 
except that the result of invoking the block are collected into a single tuple.

    >>> (x y) somefunc | anotherfunc!

Using the `!` may necessitate working with lists and tuples, so some support for that is built in.

The unpack operator `~` will take a list or tuple and push its contents onto the stack. The pack operator `<<` will take an integer and collect that many items from the stack into a new tuple.

    >>> 'a' 'b' 'c' 3<<
    ('a' 'b' 'c')

The indexing operator `$` replaces a list and an integer with the n-th item in the list. Indices start at 1.

    >>> ['a' 'b' 'c' 'd' 'e'] 2$
    ] 'b'

### Block Assignment Expressions

When assigning a value using `:`, the right side of the assignment does not always have to be an identifier.
It can also be a block. This provides a convenient syntax for destructuring arrays or tuples, and updating arrays.

For example, using block assignment syntax to destructure an array:

    >>> [ 'aaa' 'bbb' 'ccc' ]: stuff;
    >>> stuff: {thing1 thing2 thing3};
    >>> thing3
    ] 'ccc'

Block assignment syntax can also be used to modify arrays using the index operator `$`.

    >>> [1 2 3 4 5 6 7]: array;
    >>> 42: {array 2$} // replacing a single value
    ] [1 42 3 4 5 6 7]

You can even combine the two to replace multiple values in an array at once.

    >>> [1 2 3 4 5 6 7]: array;
    >>> [56 70]: {array 4$ array 7$};
    >>> array
    ] [1 2 3 56 6 70]

Note that the value of an assignment expression is always the value being assigned
(the value to the left of the `:`).

## Operator Reference

Note that certain operators are *overloaded* and so may appear multiple times in the following tables.

### General
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| \`          | quote       | 1      | "Quotes" a value, replacing it with a string that when evaluted produces the original value.
| ..          | duplicate   | 1      | Copy the top value on the stack.
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
| >>          | collection  | 1      | Operates on an integer and collects the next n items on the stack into a tuple.
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
| while       | while       | 2      | Operates on two blocks. Execute the first block in a new scope. If it results in a single value (multiple values result in an error) that is logically true, execute the second block in the current scope. Repeat this until the first block yields a logically false value.
| do          | do .. while | 1      | Operates on a block. Execute the block in the current scope and then pop the top value. Repeat this as long as the popped value is logically true.
