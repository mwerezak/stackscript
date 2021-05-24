# Title Goes Here

This an interpreter for an unnamed stack-based scripting language.

The interpreter is implemented in Python and very much incomplete. The whole project is a personal experiment. 

See the bottom of `stackscript/runtime.py` for example of usage. Or just run `python -m stackscript.runtime` from the repository root to see some examples.

Also included is a slightly modified version of PLY which I am using as the lexer. 
I plan to replace it with a simple regex-based lexer, as I'm not really doing anything fancy.

At the end of this readme is an operator reference.

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
    10

You can assign values to identifiers using the assignment operator `:`.

    [1 2 3 'a' 'b' 'c']: mylist

Right now the available data types are booleans, integers, floats, strings, lists, and blocks. The block type is really important so I will get back to that later.

In the future I'd like to have immutable and mutable flavours of lists.

I also want to add a Lua-inspired "table" mapping type that also supports Lua-style metatables. I think this will add a lot of *oomph* to the language without needing to add the weight of a fully-fledged object system.

Like Lua I plan to have a small closed set of types. I think you can do a lot with just lists, tables, and primitives.

Now, back to the "block" type. Blocks are immutable containers that contain unexecuted code. This part of the language is inspired by GolfScript.

Blocks can be invoked using the "invoke" operator `!`. This operator pops two values off of the stack, a block and a single argument value.

    >>> 4 { 1+ }!  // adds 1 to the argument
    5

If you assign a block to an identifier, you can use them like functions.

    {.*}: sqr;  // duplicates the argument, then multiplies 
                // semicolon just clears the stack, helpful for avoiding accidents
    4 sqr!

Blocks are just values, so you can put them in lists, pass them when invoking another block, etc.

When the `!` operator is used the block operand is executed in a new "scope" where the argument is the only value on the stack.

This done is for programmer sanity. However, for efficiency, no new stack needs to be created. Instead, a "stack protection" pointer can be used that raises an error if the interpreter tries to pop values beyond it (pretending that the stack is empty). When the block is done executing this pointer can then be cleared.

Identifiers are local to their scope though, so the interpreter still needs to allocate a data structure for that.

Another example, calculating the factorial.

```
{
    :n; // assign the argument to the name "n"
    // "if" will pop 3 items from the stack, like a ternary operator
    n 0 <=
    1
    { n 1- factorial! n * } if
}: factorial;

// alternatively
{
    . 0 > {. 1- factorial! *} {;1} if
}: factorial;

5 factorial!
```

When functions require multiple arguments an argument list can be passed.

    [1 2 'a'] foo!

In addition to the evaluate operator `!`, there are two other operators that act on blocks: map `/` and fold `%`.

Both take two operands, a block and a list.

The map operator `/` invokes a block on every element of a list and produces a new list from the results.

    >>> [2 3 4 5] {.*}/
    [4 9 16 25]

Unlike `!` or `/`, the fold operator `%` does not execute the block in a new scope. Instead, for each item in the list operand, `%` will push the item onto the stack and then evaluate the block directly in the current scope.

    >>> 0 [2 3 1 5] {+}%  // sum a list of values
    11

Of course you can wrap the `%` expression in a block for safety.

```
// a sum "function"
{
    :seq; // assign the sole argument to the name "seq"
    0 seq {+}%
}: sum;

[2 3 1 5] sum!
```

Last thing, about handling argument lists. There's an indexing operator `$` that replaces a list and an integer with the n-th item in the list.

    >>> ['a' 'b' 'c'] 1$
    'a'

This combined with the stack manipulation operators `.` (duplicate) and `,` (drop) allow you to assign positional arguments to local identifiers in a way that looks really nice.

```
{
    .$1: first,
    .$2: second,
    .$3: third;  // you could put these on one line if you want

    first second + third *
}: add_then_mult;

[3 4 5] add_then_mult!
```

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
| <<          | left shift  | 2      | Ditto.
| >>          | right shift | 2      | Ditto.

### Blocks
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| ~           | unpack      | 1      | "Unpack" a block by executing it in the current scope.
| !           | invoke      | 2      | Takes an argument and a block, and executes the block in a new scope where the argument is the sole element of the stack. 
| /           | map         | 2      | Operates on a block and a list. Apply a block to each element of a list, producing a new list.
| %           | fold        | 2      | Operates on a block and a list. For each element in a list, push the element onto the stack then apply the block to the stack.
| +           | concat      | 2      | Concatenate two blocks, producing a new block.

### Lists
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| ~           | unpack      | 1      | Replace a list with its contents. Each item in the list is pushed onto the stack.
| #           | length      | 1      | Produce the size of the list
| $           | index       | 2      | Operates on a list and an integer. Replaces both with the n-th item in the list.
| ++          | cons/append | 2      | Takes a list and another value, and inserts/appends the value into the list, then pushes the list back onto the stack.
| --          | decons      | 1      | Takes a list, removes the last value and then pushes them both back onto the stack (list followed by value).
| +           | concat      | 2      | Concatentate two lists.
| -           | difference  | 2      | Remove all items present in the second list from the first list, then push the first list back onto the stack.
| |           | union       | 2      | Replace two lists with their setwise union.
| &           | intersection | 2      | Replace two lists with their setwise intersection.
| ^           | symmetric difference | 2      | Replace two lists with their setwise symmetric difference.

### Strings
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| ~           | unpack      | 1      | Replace a string, pushing a sequence of strings, each containing a single character from the original, onto the stack.
| #           | length      | 1      | Produce the length of the string.
| $           | index       | 2      | Operates on a string and an integer. Replaces both with a string containing just the n-th character.
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
| and         | short-circuiting and | 2   | If the first operand is "falsey", it is pushed back onto the stack. Otherwise the second operand is pushed. If either operand is a block, it is executed in a new scope to produce a value (blocks that produce multiple values result in an error).
| or          | short-circuiting and | 2   | If the first operand is "truthy", it is pushed back onto the stack. Otherwise the second operand is pushed. If either operand is a block, it is executed in a new scope to produce a value (blocks that produce multiple values result in an error).

### Conditional Operators
| operator    | name        | arity  |  effect
| ----------- | ----------- | ------ | -------
| if          | ternary if  | 3      | If the first value is "truthy", push the second value. Otherwise push the third value. If the value that would be pushed is a block, instead execute the block in the current scope.
| while       | while       | 2      | Operates on two blocks. Execute the first block in a new scope. If it results in a single value (multiple values result in an error) that is "truthy" execute the second block in the current scope. Repeat this until the first block yields a "falsey" value.
| do          | do .. while | 1      | Operates on a block. Execute the block in the current scope and then pop the top value. Repeat this as long as the popped value is "truthy".
