____
# High Level Specification format
To specify APIs at a high-level you need to tell me the following in a language agnostic manner. I'll adapt the output to the specific language I am using. Be sure to respect the format.
<spec>
# Interface for `class_name`.
## Creation
To tell me how to create objects of class. Here are alternatives:
- To create `class_name`, provide `(arg1: typ1, arg2: typ2, ...)` arguments to its construction. It takes ... and returns ...
- `class_name`'s creation is opaque. It is created through other methods.
- To create class_name, use the static `make_xxx` functions.

## API Methods
To tell me which methods a class has, use the following approach.
- `f1(param_name1: typ1, ...) -> (ret_name: ret_type)`: Function that take ... and returns ...
- `static f2(...) -> ...`: static method if any.

Here is how to specify high level types:
- Signed integer: `int`
- Unsigned integer: `uint`
- Array/List/Vector of `T`: `vec<T>`
- Index into Array/List/Vector: `usize`
- String type: `string`
- Byte vector: `bytes`
- Handle/Reference/Pointer to `T`: `handle<T>`.
- Pair/Tuple of `T1`, `T2`, ...: `(T1, T2, ...)`.
- Optional `T` (when the value may or may not be present): `optional T`.
- Map from `T1` to `T2`: `map<T1, T2>`
- Other intuitive types: Feel free to come up with intuitive names:
    * `set<T>` or `lru<T>` or `timestamp`, etc.

For greater clarity, also you give me name of parameters and return values. For example, the following two are equivalent:
- `get_value_at(items: vec<(int, int)>, i: usize) -> int`.
- `get_value_at(items: vec<(k: int, v: int)>, i: usize) -> (v: int)`: Note that I specify the name of each item in the vector and the return type.

</spec>
___
