PSEUDOCODER_SYSTEM_MSG = """
You will help me generate language-agnostic pseudocode from high-level implementation plans written in English.

While the syntax should be compatible with Python to ground the implementation, I want a language-agnostic solution that can be implemented in any language.

When creating variables, you can use Python's types and standard library.
- For example, you can use `t.List[int]` to denote a list of integers.
- Or `t.IO` to denote a file object.
- Or `t.Optional` to denote an optional value.
- Or `t.Dict` to denote a dictionary.
- Or `threading.Lock` to denote a lock.
- Or `bytes` to denote a byte vector.
- Feel free to import `typing as t` to make the type hints cleaner.

Likewise, use Python's variable/class/function/method definitions and syntax.
- For example, you can use `def` to define a function.
- Also, arithmetic operations, control-flow operations, function calls, etc. can be in Python.
    - That's because these can easily be translated to any language.

However, minimize reliance on Python-specific features to keep language agnostism.
- I want you to assume that there exists a function call `assistant_codegen("high-level english")` and can generate code in any language as long as the high-level English is not too complex.
    * For example:
        - Instead using python's sorting, you can do `sorted_list = assistant_codegen("sort the list", list_to_sort)`.
        - Instead of using low-level I/O operations, you can do `file = assistant_codegen("open the file in RW Mode", filename)` or `assistant_codegen("write to the file at the given offset", file, offset, data)`.
    * It cannot, however, do extremely complex/multstep tasks like:
        - `assistant_codegen("Building a full OS from scratch") or `assistant_codegen("a full Python interpreter")`.
        - `assistant_codegen("Call a Lambda function, then Insert in DynamoDB, then Write to S3 and notify the a REST API")`.
            -  This can however be broken down into multiple steps:
                - `value = assistant_codegen("Call a Lambda function and parse its output from json", lambda_name, lambda_args)`.
                - `assistant_codegen("Insert in DynamoDB. Throw an exception if failure.", key, value)`.
                - `success = assistant_codegen("Write to S3. Return a boolean marking success.", data)`.
                - `assistant_codegen("Notify the a REST API. Ignore output/error.", endpoint, success)`.
- Assume any library the assistant needs is already available.

As an example, here is code than returns the value at a given percentile in a list of integers:
```python
# Use python syntax and type hints for declarations.
def percentile(lst: t.List[int], p: float) -> int:
    # Use codegen for sorting.
    sorted_list: t.List[int] = assistant_codegen("sort the list", lst)
    # Use python for regular operations and common operations (e.g., length, indexing).
    index: int = int(len(sorted_list) * p)
    return sorted_list[index]
```
"""


PSEUDOCODER_OUTPUT_FORMAT = """
Your output should be formatted as follows:

<reason>
```md
... Overall reasoning for the method implementation here ...
```
</reason>

<code>
```python
# ... All imports here ...

# Class definition here...
class ClassName(...):
    # Class member declarations here...

    def __init__(self, ...):
        # ... Implementation here ...

    def method_name1(self, ...):
        # ... Implementation here ...

    ...
```
</code>


For my own convenience:
- Place the import inside the class definition (for dynamic loading to work).
- Be sure to use `assistant_codegen` whenever possible to keep the code mostly high-level and language-agnostic.
    - Remember to break down complex tasks into multiple steps, each calling `assistant_codegen` if possible.
    - Simple operations like arithmetic, control-flow, basic function calls, object creation, etc. can be in Python.
    - Likewise types can be Python types (e.g., `t.List[int]`).
- Be as explicit about the types of class members, method arguments, and return values as possible.
    - You can be less strict for local variables if the type is obvious from the context.
- Explicitly put class member declarations above the `__init__` method.
- You can import Python dependencies at the top of the class definition using any syntax.
- However, to import project-specific modules, you must use:
    - import <module_name>.<item_name> or from <module_name>.<item_name> import <class/interface>.
    - I have given you the modules and items that are project-specific dependencies.
    - Also, you should import the module's own interface using <own_module_name>.<own_item_name>.
- NOTE on concrete implementations:
    - While method calls can occur on interface, object creation can only be done with concrete implementations.
    - I've given you the spec for concrete implementations of the dependencies. Use them to create objects.
Be sure to respect the tags (reason, code) and the markdown formatting.
"""


PSEUDOCODER_INSTRUCTION = f"""
Generate pseudo-code from the given high-level implementation plan.

{PSEUDOCODER_OUTPUT_FORMAT}
"""

PSEUDOCODER_CONFIRMATION = f"""
Confirm that the generated pseudo-code is correct.
If something is incorrect, provide a full corrected pseudocode (i.e., rewrite the entire pseudocode correctly).

{PSEUDOCODER_OUTPUT_FORMAT}

If the previous pseudocode is already correct, DO NOT include the `code` tag in the response.
My automated tool relies on this to know that the previous pseudocode is correct.
"""



ASSISTANT_CODEGEN_DUMMY = """
def assistant_codegen(description: str, *args, **kwargs):
    \"\"\"
    This just a dummy function. The transpiler will remove it and replace calls to this with actual code for the target language.
    \"\"\"
    pass
"""