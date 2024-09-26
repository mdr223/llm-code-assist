import ast
from common.handles import LANGUAGE_MODEL
from collections import OrderedDict
import tomllib
import os

class SpecItem:
    """Represents an individual item (e.g., one class) in the spec."""
    def __init__(self, filename):
        self.filename = filename
        self.dependencies = []
        self.api_spec = ""
        self.implementation_essentials = ""

    def resolved_dependencies(self, tree: "SpecTree"):
        pass

class SpecModule:
    """Represents a module (set of related items) in the spec."""
    def __init__(self, module_folder):
        self.module_folder = module_folder
        self.api_spec = ""
        self.dependencies = []
        self.spec_items = []

    def resolved_dependencies(self, tree: "SpecTree"):
        pass


class SpecTree:
    """Represents the entire spec tree."""
    def __init__(self, source_folder):
        self.source_folder = source_folder
        self.spec_modules = []

    def resolved_dependencies(self):
        pass


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