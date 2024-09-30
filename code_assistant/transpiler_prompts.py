PRE_COMMON_SYSTEM_MSG = """
You will help transpile pseudocode to {language_name}.

The pseudo-code is written in a Python-like language, but is not actually Python.
In particular, it may use a function `assistant_codegen` that takes a high-level description.
- Wheneven you see a call to `assistant_codegen`, you should convert the high-level description to actual code in the target language.

Make sure that the code you generate is correct and idiomatic in the target language.
You should leave generous comments and explanations in the code to make it easy to understand.
Also keep my exisiting comments and docstrings (for interfaces, classes, and methods) in the generated code.
It should compile well, and perform the intended task, whether specified in precise code, or in high-level English.

We will assume a flat directory structure that contains all the necessary files (both header and source files).
For a module named `<module_name>` and an item named `<item_name>` here is the naming scheme. Be sure to follow this naming scheme when generating code, especially in the import/include directives.
""".strip()

POST_COMMON_SYSTEM_MSG = """
If you need a third-party library, assume it is installed.
    - Mention using this library in the reasoning and comments.
    - {third_party_library_instructions}

{additional_system_msg}
"""

INTERFACE_NAMING_SCHEME = """
- A pure interface header file named `<module_name>_<item_name>_interface.{header_extension}` in lowercase.
"""

IMPLEMENTATION_HEADER_NAMING_SCHEME = """
- An implementation header file named `<module_name>_<item_name>_<class_name>.{header_extension}` in lowercase.
""".strip()

IMPLEMENTATION_SOURCE_NAMING_SCHEME = """
- An implementation source file named `<module_name>_<item_name>_<class_name>.{source_extension}` in lowercase.
""".strip()

CPP_SYSTEM_MSG = f"""
- All code belongs in the namespace called `<module_name>`.
Remember that while virtual function calls can occur on references to interfaces, object creation can only be done with concrete implementations.
"""

TRANSPILER_SYSTEM_MSG_WITH_HEADER = f"""
{PRE_COMMON_SYSTEM_MSG}
{INTERFACE_NAMING_SCHEME}
{IMPLEMENTATION_HEADER_NAMING_SCHEME}
{IMPLEMENTATION_SOURCE_NAMING_SCHEME}
{POST_COMMON_SYSTEM_MSG}
"""

TRANSPILER_SYSTEM_MSG_NO_HEADER = f"""
{PRE_COMMON_SYSTEM_MSG}
{INTERFACE_NAMING_SCHEME}
{INTERFACE_NAMING_SCHEME}
{IMPLEMENTATION_SOURCE_NAMING_SCHEME}
{POST_COMMON_SYSTEM_MSG}
"""



TRANSPILER_OUTPUT_FORMAT = """

Your output should be formatted as follows:
<reason>
```md
... Overall reasoning for the code here ...
```
</reason>

<code>
```[target_language]
... The actual code in the target language ...
```
</code>

Be sure to respect the tags (reason, code) and the markdown formatting.
"""

TRANSPILER_INTERFACE_INSTRUCTIONS = f"""
Transiple the **interface** this particular item to {{language_name}}.
Preserve the API comments (docstring) I've already made. Add some if beneficial.
Assume its dependencies are already implemented using the same naming scheme.

{TRANSPILER_OUTPUT_FORMAT}

{{transpilation_instructions}}
Make sure that the interface name clearly ends with: `Interface`. Other modules depend on this.
"""

TRANSPILE_IMPLEMENTATION_HEADER_INSTRUCTIONS = f"""
Transpile the **implementation header** for this particular item to {{language_name}}.
Assume its dependencies are already implemented using the same naming scheme.

{TRANSPILER_OUTPUT_FORMAT}

{{transpilation_instructions}}
"""

TRANSPILE_IMPLEMENTATION_SOURCE_INSTRUCTIONS = f"""
Transpile the **implementation source** for this particular item to {{language_name}}.
Assume its dependencies are already implemented using the same naming scheme.

{TRANSPILER_OUTPUT_FORMAT}

{{transpilation_instructions}}
"""

TRANSPILE_IMPLEMENTATION_SOURCE_CONFIRMATION = f"""
Confirm that the **implementation source** for this particular item is correctly transpiled to {{language_name}}.
If something is incorrect, provide a full corrected implementation source (i.e., rewrite the entire source correctly).

{TRANSPILER_OUTPUT_FORMAT}

Be particularly careful with the following:
{{transpilation_instructions}}

If the previous source is already correct, DO NOT include the `code` tag in the response.
My automated tool relies on this to know that the previous source is correct.
"""

# CMakelists.txt for C++.
CMAKELISTS_TXT = """
# Compile everything in the top-level directory
cmake_minimum_required(VERSION 3.28)

# Set the C++ standard to 23
set(CMAKE_CXX_STANDARD 23)

# Set the project name
project(tree_src_cpp)

# Set the source directory
set(SOURCE_DIR "{cpp_src_folder}")


# Add all the source files
file(GLOB_RECURSE SOURCES "${{SOURCE_DIR}}/*.cpp")

# Add the library
add_library(assistant_transpiled_cpp ${{SOURCES}})

# Add the include directories
target_include_directories(assistant_transpiled_cpp PUBLIC "${{SOURCE_DIR}}")
"""

# Cargo.toml for Rust.
CARGO_TOML = """
[package]
name = "transpiled_rust"
version = "0.1.0"

[dependencies]
rand = "*"
byteorder = "*"
"""