import ast
from common.handles import LANGUAGE_MODEL
from collections import OrderedDict
import tomllib
import os

SPEC_FILE = "metadata_store.py"

SYSTEM_MSG = """
You are a code architect that will help me design a system in multiple phases.
I will provide you the API specification and system guarantees.

From there, we will have two kinds of implementations:
- A basic implementation that fulfills the guarantees, is very simple, but may be inefficient.
    * It can have simple algorithms (e.g., linear, O(n^2) or even worse).
    * It can have coarse-grained global locks and sequentialize every operation.
    * It can do coarse-grained file/network I/O without complex file reorganization or protocols.
    * It can have the crudest form of durability and recovery (e.g., full rewrites/rereads).
    * But it should be correct and fulfill the guarantees.
- An advanced implementation that is efficient, concurrent and safe.

Each implementation will be broken down into multiple steps.
- First, we will come up with an implementation plan which will be a high-level description of the steps.
- Then, we will implement each step in a separate function.

For now, our implementations will be high-level and language-agnostic.
We will later concretize them in many target languages once I am certain of the design.
"""

GENERAL_CODING_GUIDELINES = """
# General Coding Guidelines
Even though we are using Python to ground the implementation, I want a language-agnostic solution that can be implemented in any language.

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

IMPLEMENTATION_PLAN_INSTRUCTIONS = """
Create an implementation plan for the basic implementation.
The steps should be high-level, unless there is something extremely specific and complex that requires pseudo-code.

Your output should be formatted as follows:

<reason>
```md
... Overall reasoning for the plan here ...
```
</reason>

<plan>
```md
... High-level steps for the plan here ...
```
</plan>

Be sure to respect the tags (reason, plan) and the markdown formatting.
"""

TOML_IMPLEMENTATION_PLAN_INSTRUCTIONS = """
I now have the implementation. Convert it to an easy-to-parse and easy-to-understand TOML format.
I have automated tools that rely on well-generated TOML files, so please ensure the output is correct and complete.

Your output should be formatted as follows:

<plan>
```toml
[[method]]
class_name = "class_name"|"" # If the method is in a class (i.e. not an outer function)
class_interface = "interface_name"|"" # If the class implements an interface
method_name = "method_name"|"function_name"
is_auxiliary = false|true
description = "Brief description of the method"
steps = \"\"\"
... The steps for the method ...
\"\"\"

[[method]]
...
```
</plan>
"""

METHOD_IMPLEMENTATION_INSTRUCTIONS = """
Implement the method given the overall plan.
We will implement one method at a time, but you can see the overall plan for context.

Your output should be formatted as follows:

<reason>
```md
... Overall reasoning for the method implementation here ...
```
</reason>

<code>
```python
class ClassName(...):
    # ... Imports here ...
    def method_name(self, ...):
        # ... Implementation here ...
```
</code>


For my own convenience:
- Define the method inside the class so that I can easily merge it with the existing code.
- Place the import inside the class definition (for dynamic loading to work).
- Be sure to use `assistant_codegen` whenever possible to keep the code mostly high-level and language-agnostic.
    - Remember to break down complex tasks into multiple steps, each calling `assistant_codegen` if possible.
    - Simple operations like arithmetic, control-flow, basic function calls, object creation, etc. can be in Python.
    - Likewise types can be Python types (e.g., `t.List[int]`).
- Be as explicit about the types of class members, method arguments, and return values as possible.
    - You can be less strict for local variables if the type is obvious from the context.
Be sure to respect the tags (reason, code) and the markdown formatting.
"""


ASSISTANT_CODEGEN_DUMMY = """
def assistant_codegen(description: str, *args, **kwargs):
    \"\"\"
    This just a dummy function. The transpiler will remove it and replace calls to this with actual code for the target language.
    \"\"\"
    pass
"""

TRANSPILER_SYSTEM_MSG = """
You are a code transpiler assistant that will help me convert pseudo-code to a target language.
The pseudo-code is written in a Python-like language, but is not actually Python.
In particular, it uses a function `assistant_codegen` that takes a high-level description.
- Wheneven you see a call to `assistant_codegen`, you should convert the high-level description to actual code in the target language.

Make sure that the code you generate is correct and idiomatic in the target language.
It should compile well, and perform the intended task, whether specified in precise code, or in high-level English.
"""

TRANSPILER_INSTRUCTIONS = """
Convert the pseudo-code to actual code in the target language.

You should leave generous commonts and explanations in the code to make it easy to understand.

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

class SpecParser(ast.NodeVisitor):
    def __init__(self, source):
        self.source = source
        self.api_spec = ""
        self.overall_implementation_spec = ""
        self.first_implementation_spec = ""
        self.first_plan_example = ""
        self.interfaces = OrderedDict()
        self.is_code_approved = False
        pass
    
    def visit_Module(self, node):
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_name = node.name
        if class_name.endswith("Interface"):
            class_code = ast.get_source_segment(self.source, ast.parse(node))
            method_names = []
            for child in ast.walk(node):
                if isinstance(child, ast.FunctionDef):
                    method_names.append(child.name)
            self.interfaces[class_name] = (class_code, method_names)
        self.generic_visit(node)


    def visit_Assign(self, node):
        print(f"Class type {type(node.targets[0])}")
        if not isinstance(node.targets[0], ast.Name):
            self.generic_visit(node)
            return
        var_name = node.targets[0].id
        if var_name == "API_SPEC":
            self.api_spec = node.value.value
        elif var_name == "OVERALL_IMPLEMENTATION_SPEC":
            self.overall_implementation_spec = node.value.value
        elif var_name == "FIRST_IMPLEMENTATION_SPEC":
            self.first_implementation_spec = node.value.value
        elif var_name == "FIRST_IMPLEMENTATION_PLAN_EXAMPLE":
            self.first_plan_example = node.value.value
        elif var_name == "APPROVED":
            self.is_code_approved = node.value.value
        self.generic_visit(node)

    def get_common_context(self, interface_code, with_guidelines=True):
        sep = "_" * 10
        return f"""
{sep}
{GENERAL_CODING_GUIDELINES if with_guidelines else ''}
{sep}
{self.api_spec}

Interface Code:
{interface_code}
{sep}
{self.overall_implementation_spec}
{sep}
"""

    def read_plan(self, interface_name, check_approved):
        infile = f"{interface_name}_first_plan.toml"
        if not os.path.exists(infile):
            return None
        with open(infile, "r") as f:
            first_plan_toml = f.read()
        first_plan = tomllib.loads(first_plan_toml)
        if check_approved and ("approved" not in first_plan or not first_plan["approved"]):
            return None
        return first_plan, first_plan_toml
    
    def read_code(self, codefile, check_approved):
        if not os.path.exists(codefile):
            return None
        with open(codefile, "r") as f:
            code = f.read()
        self.is_code_approved = False
        ast_node = ast.parse(code)
        self.visit(ast_node)
        if check_approved and not self.is_code_approved:
            return None
        return code


    def generate_first_implementation_plan(self):
        assert len(self.interfaces) == 1, "Only one interface currently supported"
        interface_name, (interface_code, method_names) = list(self.interfaces.items())[0]
        if self.read_plan(interface_name, check_approved=True) is not None:
            print(f"Plan for {interface_name} already exists and is approved")
            return
        common_context = self.get_common_context(interface_code)
        common_context = f"""
{common_context}
---
{self.first_implementation_spec}
---
{self.first_plan_example}
---
"""
        prompt = f"""
{common_context}
Your task: {IMPLEMENTATION_PLAN_INSTRUCTIONS}
"""
        cache_key = f"first_plan_{interface_name}"
        response = LANGUAGE_MODEL.invoke(prompt, system_msg=SYSTEM_MSG, cache_key=cache_key)
        reasons, codeblocks, attrs = LANGUAGE_MODEL.parse_standard_response(response, code_tag="plan", code_langs=["md"])
        reason = reasons["reason"]
        plan = codeblocks["plan"]
        print(f"Reason:\n{reason}")
        print(f"Plan:\n{plan}")
        # exit(0)
        prompt = f"""
{common_context}
---
Here is the plan you generated. Convert it to TOML format.
{plan}
---
Your task: {TOML_IMPLEMENTATION_PLAN_INSTRUCTIONS}
"""
        cache_key = f"first_plan_toml_{interface_name}"
        response = LANGUAGE_MODEL.invoke(prompt, system_msg=SYSTEM_MSG, cache_key=cache_key)
        reasons, codeblocks, attrs = LANGUAGE_MODEL.parse_standard_response(response, code_tag="plan", code_langs=["toml"])        
        plan_toml = codeblocks["plan"]
        print(f"Plan TOML:\n{plan_toml}")
        _parsed_plan_toml = tomllib.loads(plan_toml)
        print(_parsed_plan_toml)
        outfile = f"{interface_name}_first_plan.toml"
        with open(outfile, "w") as f:
            f.write(plan_toml)

    def generate_first_implementation(self):
        assert len(self.interfaces) == 1, "Only one interface currently supported"
        interface_name, (interface_code, method_names) = list(self.interfaces.items())[0]
        first_plan = self.read_plan(interface_name, check_approved=True)
        if first_plan is None:
            print(f"First plan for {interface_name} does not exist or is not approved. Please generate or approve it first.")
            return
        first_plan_dict, first_plan_str = first_plan
        first_code = self.read_code(f"{interface_name}_first_impl.py", check_approved=False)
        if first_code is not None:
            print(f"Code for {interface_name} already exists and is approved")
            return
        common_context = self.get_common_context(interface_code)
        common_context = f"""
{common_context}
---
{self.first_implementation_spec}
---
Here is the overall first plan. We are going to proceed with the methods one by one.
{first_plan_str}
---
"""
        init_code = None
        stitchers = {}
        for i, method in enumerate(first_plan_dict["method"]):
            method_name = method["method_name"]
            class_name = method["class_name"]
            interface_name = method["class_interface"]
            is_auxiliary = method["is_auxiliary"]
            assert interface_name is not None, "Only interface methods supported for now"
            if is_auxiliary:
                prefix = f"Auxiliary Method"
            else:
                prefix = f"Method"
            if interface_name is not None:
                full_name = f"{prefix} `{method_name}` in `{class_name}({interface_name})`"
            elif class_name is not None:
                full_name = f"{prefix} `{method_name}` in `{class_name}`"
            else:
                prefix = f"Function"
                full_name = f"{prefix} `{method_name}`"
            if method_name == "__init__":
                init_context = "Clearly place the class members (with types) at the top of the class definition."
            elif init_code is not None:
                init_context= f"""
Here is the code for the initialization method for context on class members. Do not repeat their declarations.
```python
{init_code}
```
"""
            else:
                init_context = ""
            prompt = f"""
{common_context}
---
{init_context}
---
What implement in this step: {full_name}
Your task: {METHOD_IMPLEMENTATION_INSTRUCTIONS}
"""
            cache_key = f"first_method_{method_name}"
            response = LANGUAGE_MODEL.invoke(prompt, system_msg=SYSTEM_MSG, cache_key=cache_key)
            reasons, codeblocks, attrs = LANGUAGE_MODEL.parse_standard_response(response, code_tag="code", code_langs=["python"])
            reason = reasons["reason"]
            code = codeblocks["code"]
            # print(f"Reason:\n{reason}")
            # print(f"Code:\n{code}")
            method["implementation"] = {"reason": reason, "code": code}
            if method_name == "__init__":
                init_code = code
            if class_name not in stitchers:
                stitchers[class_name] = CodeStitcher(class_name, interface_name)
            stitcher: CodeStitcher = stitchers[class_name]
            stitcher.curr_source = code
            stitcher.visit(ast.parse(code))
        print(len(stitchers[class_name].functions))
        for class_name, stitcher in stitchers.items():
            string_buffer = []
            # Imports
            for import_name, (import_node, import_source) in stitcher.imports.items():
                code = ast.get_source_segment(import_source, import_node, padded=True)
                string_buffer.append(code)
            string_buffer.append("\n")
            # Dummy
            string_buffer.append(ASSISTANT_CODEGEN_DUMMY.strip())
            string_buffer.append("\n")
            # Class Decl.
            if stitcher.interface_name is not None:
                string_buffer.append(self.interfaces[stitcher.interface_name][0])
                string_buffer.append("\n")
                string_buffer.append(f"class {class_name}({stitcher.interface_name}):")
            else:
                string_buffer.append(f"class {class_name}:")
            # Class Vars
            for var_name, (var_node, var_source) in stitcher.class_vars.items():
                code = ast.get_source_segment(var_source, var_node, padded=True)
                if not code[0].isspace():
                    code = (" " * 4) + code
                string_buffer.append(code)
            string_buffer.append("\n")
            # Functions
            for fn_name, (fn_node, fn_source) in stitcher.functions.items():
                string_buffer.append(ast.get_source_segment(fn_source, fn_node, padded=True))
                string_buffer.append("\n")
            final_output = "\n".join(string_buffer)
            with open(f"{stitcher.interface_name}_first_impl.py", "w") as f:
                f.write(final_output)

    def transpile_first_implementation(self, lang="C++"):
        interface_name, (interface_code, method_names) = list(self.interfaces.items())[0]
        first_plan = self.read_plan(interface_name, check_approved=True)
        if first_plan is None:
            print(f"First plan for {interface_name} does not exist or is not approved. Please generate or approve it first.")
            return
        first_plan_dict, first_plan_str = first_plan
        pseudocode_file = f"{interface_name}_first_impl.py"
        with open(pseudocode_file, "r") as f:
            pseudocode = f.read()
        common_context = self.get_common_context(interface_code)
        common_context = f"""
{common_context}
---
{self.first_implementation_spec}
---
Here is the high-level first plan.
{first_plan_str}
---
Here is the pseudo-code corresponding to the plan.
{pseudocode}
---
"""
        prompt = f"""
{common_context}
---
Target Language: {lang}
Your task: {TRANSPILER_INSTRUCTIONS}
"""
        cache_key = f"first_transpile_{interface_name}_{lang}"
        response = LANGUAGE_MODEL.invoke(prompt, system_msg=TRANSPILER_SYSTEM_MSG, cache_key=cache_key)
        codelangs = ["cpp", "go", "py", "rs", "python", "rust"]
        reasons, codeblocks, attrs = LANGUAGE_MODEL.parse_standard_response(response, code_tag="code", code_langs=codelangs)
        reason = reasons["reason"]
        code = codeblocks["code"]
        print(f"Reason:\n{reason}")
        print(f"Code:\n{code}")
        if lang == "C++":
            extension = "cpp"
        elif lang == "Go":
            extension = "go"
        elif lang == "Python":
            extension = "py"
        elif lang == "Rust":
            extension = "rs"
        target_file = f"{interface_name}_first_code.{extension}"
        with open(target_file, "w") as f:
            f.write(code)
        # exit(0)


class CodeStitcher(ast.NodeVisitor):
    def __init__(self, class_name, interface_name):
        self.imports = OrderedDict()
        self.class_vars = OrderedDict()
        self.functions = OrderedDict()
        self.curr_source = ""
        self.class_name = class_name
        self.interface_name = interface_name

    def visit_ClassDef(self, node: ast.ClassDef):
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self.functions[child.name] = (child, self.curr_source)
            elif isinstance(child, ast.Assign):
                if child.targets[0].id in self.class_vars:
                    continue
                self.class_vars[child.targets[0].id] = (child, self.curr_source)
            elif isinstance(child, ast.AnnAssign):
                if child.target.id in self.class_vars:
                    continue
                self.class_vars[child.target.id] = (child, self.curr_source)
            elif isinstance(child, ast.Import):
                for alias in child.names:
                    if alias.name in self.imports:
                        continue
                    self.imports[alias.name] = (child, self.curr_source)
            elif isinstance(child, ast.ImportFrom):
                for alias in child.names:
                    if alias.name in self.imports:
                        continue
                    self.imports[alias.name] = (child, self.curr_source)
            
            

    


if __name__ == "__main__":
    with open(SPEC_FILE) as f:
        spec = f.read()
        parsed_spec = ast.parse(spec)
    parser = SpecParser(spec)
    parser.visit(parsed_spec)
    parser.generate_first_implementation_plan()
    parser.generate_first_implementation()
    parser.transpile_first_implementation(lang="C++")
    parser.transpile_first_implementation(lang="Go")
    parser.transpile_first_implementation(lang="Python")
    parser.transpile_first_implementation(lang="Rust")