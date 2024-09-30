from common.handles import LANGUAGE_MODEL, PROMPTING_PATTERNS
from .spec_parser import (
    SpecTree,
    SpecModule,
    SpecItem,
    ParsedClass,
)
from .spec_planner import SpecPlanner
from .spec_pseudocoder import SpecPseudoCoder
from .transpiler_prompts import (
    TRANSPILER_SYSTEM_MSG_WITH_HEADER,
    TRANSPILER_SYSTEM_MSG_NO_HEADER,
    TRANSPILER_INTERFACE_INSTRUCTIONS,
    TRANSPILE_IMPLEMENTATION_HEADER_INSTRUCTIONS,
    TRANSPILE_IMPLEMENTATION_SOURCE_INSTRUCTIONS,
    TRANSPILE_IMPLEMENTATION_SOURCE_CONFIRMATION,
    CMAKELISTS_TXT,
    CARGO_TOML,
)
import typing as t
import os


class LanguageInfo:
    def __init__(self, name: str, extension: str, header_extension: t.Optional[str] = None):
        self.name = name
        self.extension = extension
        self.header_extension = header_extension

    def has_separate_header(self):
        return self.header_extension is not None
    
    def setup_transpilation_folder(self, spec_tree: SpecTree):
        target_folder =  f"{spec_tree.source_folder}/assistant_transpiled_{self.extension}"
        if not os.path.exists(target_folder):
            os.makedirs(target_folder, exist_ok=True)
        return target_folder


    def third_party_notes(self):
        pass

    def additional_system_msg(self):
        pass

    def transpilation_instructions(self):
        pass

    def format_prompt(self, prompt: str):
        header_extension = self.header_extension if self.has_separate_header() else self.extension
        source_extension = self.extension
        third_party_instructions = self.third_party_notes()
        language_name = self.name
        return prompt.format(
            header_extension=header_extension,
            source_extension=source_extension,
            third_party_library_instructions=third_party_instructions,
            language_name=language_name,
            additional_system_msg=self.additional_system_msg(),
            transpilation_instructions = self.transpilation_instructions()
        )

class CppLanguageInfo(LanguageInfo):
    def __init__(self):
        super().__init__("C++23", "cpp", "hpp")

    def setup_transpilation_folder(self, spec_tree: SpecTree):
        target_folder = super().setup_transpilation_folder(spec_tree)
        abs_path = os.path.abspath(target_folder)
        cmakelists_file = f"{target_folder}/CMakeLists.txt"
        content = CMAKELISTS_TXT.format(cpp_src_folder=abs_path)
        with open(cmakelists_file, "w") as f:
            f.write(content)
        return target_folder

    def third_party_notes(self):
        return "Assume third party libraries are in `third_party/<library_name>`"
    
    def transpilation_instructions(self):
        return f"""
- Use shared_ptr to pass Interfaces around. This is the most simple and flexible way to handle dependencies.
- For the sake of simplicity and conciseness, avoid using const and constexpr. They make other generated code more difficult to compile.
- Generally avoid const and constexpr. They make compilation more difficult.
""".strip()

class GoLanguageInfo(LanguageInfo):
    def __init__(self):
        super().__init__("Go", "go", None)

    def setup_transpilation_folder(self, spec_tree: SpecTree):
        return super().setup_transpilation_folder(spec_tree)

    def third_party_notes(self):
        return "Assume third party libraries are already setup in the standard `go.mod` way."
    
    def transpilation_instructions(self):
        return f"""
- Do not declare or define any creation methods in the interface file. This is a common mistake in Go.
    - Creation methods (e.g., `NewSomething(...)`) are specific to the implementation and should be in the implementation file.
""".strip()
    

class RustLanguageInfo(LanguageInfo):
    def __init__(self):
        super().__init__("Rust", "rs", None)

    def setup_transpilation_folder(self, spec_tree: SpecTree):
        target_folder = super().setup_transpilation_folder(spec_tree)
        cargo_toml_file = f"{target_folder}/Cargo.toml"
        with open(cargo_toml_file, "w") as f:
            f.write(CARGO_TOML)
        src = f"{target_folder}/src"
        if not os.path.exists(src):
            os.makedirs(src, exist_ok=True)
        lib_rs = f"{src}/lib.rs"
        with open(lib_rs, "w") as f:
            for module_name, module in spec_tree.spec_modules.items():
                for item_name, item in module.spec_items.items():
                    f.write(f"pub mod {module_name}_{item.spec_name}_interface;\n".lower())
                    for implementation_name, implementation in item.implementations.items():
                        f.write(f"pub mod {module_name}_{item.spec_name}_{implementation.node.name};\n".lower())
        return src

    def third_party_notes(self):
        return """
- Assume third party libraries are already setup in the standard `Cargo.toml` way.
- Assume the `src/lib.rs` file is already setup with the necessary module declarations.
""".strip()
    
    def transpilation_instructions(self):
        return """
- Be particularly careful about:
    - Mutable vs immutable references.
    - Lifetimes.
- Liberally make things mutable if you're not sure. It makes the code easier to generate for you.
- DO NOT put a `new` method in the interface. It makes it "object unsafe", and very difficult to use for other code.
    - Only place regular API methods in the interface.
    - Creation methods (e.g., `new()`) should be in the implementation.
- Don't bother handling errors. Just use `unwrap()`, `expect()`, or `panic()` liberally.
"""


CPP = CppLanguageInfo()
GO = GoLanguageInfo()
RUST = RustLanguageInfo()

class GenericSpecTranspiler:
    def __init__(self, pseudocoder: SpecPseudoCoder, lang: LanguageInfo):
        self.pseudocoder = pseudocoder
        self.spec_planner = pseudocoder.spec_planner
        self.spec_tree = pseudocoder.spec_tree
        self.pseudocodes = pseudocoder._approved_pseudocodes
        self.plans = pseudocoder.spec_planner.generated_plans
        self.generated_interfaces: t.Dict[str, t.Dict[str, str]] = {}
        self.generated_headers: t.Dict[str, t.Dict[str, t.Dict[str, str]]] = {}
        self.lang = lang
        self.code_langs = ["cpp", "go", "python", "rs", "rust", self.lang.extension]
        if self.lang.has_separate_header():
            self.system_msg = lang.format_prompt(TRANSPILER_SYSTEM_MSG_WITH_HEADER)
        else:
            self.system_msg = lang.format_prompt(TRANSPILER_SYSTEM_MSG_NO_HEADER)
        self.target_folder = lang.setup_transpilation_folder(self.spec_tree)
        self.spec_planner._process_tree(self.spec_planner._process_module, self._process_item)
        pass

    def _make_dependency_headers(self, spec_module: SpecModule, spec_item: SpecItem, dependency_context: str):
        headers = []
        item_sep = "\n" + ("_" * 5) + "\n"
        module_sep = "\n" + ("_" * 10) + "\n"
        dep_sep = "\n" + ("_" * 15) + "\n"
        for dep_module_name, dep_item_names in spec_item.dependencies.items():
            dep_module = self.spec_tree.spec_modules[dep_module_name]
            dep_module_headers = []
            for dep_item_name in dep_item_names:
                assert dep_module_name in self.generated_interfaces and dep_item_name in self.generated_interfaces[dep_module_name], f"Dependency interface not generated: {dep_module_name}.{dep_item_name}"
                dep_item = dep_module.spec_items[dep_item_name]
                dep_file = self._interface_file(dep_module, dep_item)
                abstract_header = self.generated_interfaces[dep_module_name][dep_item_name]
                s = f"/// Abstract Interface Dependency: {dep_module.module_name}.{dep_item.spec_name} in file {dep_file}."
                s = f"\n{s}\n{abstract_header}"
                dep_module_headers.append(f"{item_sep}{s}{item_sep}")
                for dep_implementation_name, dep_implementation in dep_item.implementations.items():
                    dep_file = self._implementation_header_file(dep_module, dep_item, dep_implementation)
                    s = f"/// Implementation Dependency: {dep_module.module_name}.{dep_item.spec_name}.{dep_implementation.node.name} in file {dep_file}."
                    implementation_header = self.generated_headers[dep_module_name][dep_item_name][dep_implementation_name]
                    s = f"{s}\n{implementation_header}"
                    dep_module_headers.append(f"{item_sep}{s}{item_sep}")
            dep_module_headers = "\n".join(dep_module_headers)
            headers.append(f"{module_sep}{dep_module_headers}{module_sep}")
        headers = "\n".join(headers)
        if len(headers) == 0:
            return ""
        headers = f"{dep_sep}{headers}{dep_sep}"
        print(headers)
        return headers



                

    def _process_item(self, module_name: str, item_name: str):
        print(f"Transpiling item: {item_name}. Module: {module_name}")
        if module_name not in self.generated_interfaces:
            self.generated_interfaces[module_name] = {}
        spec_module = self.spec_tree.spec_modules[module_name]
        spec_item = spec_module.spec_items[item_name]
        dependency_context = self._make_dependency_headers(spec_module, spec_item, None)
        self._prompt_interface_transpilation(spec_module, spec_item, dependency_context)
        for implementation_name, implementation in spec_item.implementations.items():
            if self.lang.has_separate_header():
                self._prompt_implementation_header_transpilation(spec_module, spec_item, implementation, dependency_context)
            self._prompt_implementation_source_transpilation(spec_module, spec_item, implementation, dependency_context)
        pass

    def _interface_file(self, spec_module: SpecModule, spec_item: SpecItem):
        ext = self.lang.header_extension if self.lang.has_separate_header() else self.lang.extension
        name = f"{spec_module.module_name}_{spec_item.spec_name}_Interface.{ext}".lower()
        return f"{self.target_folder}/{name}"
    
    def _implementation_header_file(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass):
        ext = self.lang.header_extension if self.lang.has_separate_header() else self.lang.extension
        name = f"{spec_module.module_name}_{spec_item.spec_name}_{implementation.node.name}.{ext}".lower()
        return f"{self.target_folder}/{name}"
    
    def _implementation_source_file(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass):
        name = f"{spec_module.module_name}_{spec_item.spec_name}_{implementation.node.name}.{self.lang.extension}".lower()
        return f"{self.target_folder}/{name}"


    def _prompt_interface_transpilation(self, spec_module: SpecModule, spec_item: SpecItem, dependency_context: str):
        prompt = f"""
{self.spec_planner._get_implementation_context(spec_module, spec_item, None, dependency_context)}
---
Your task: {self.lang.format_prompt(TRANSPILER_INTERFACE_INSTRUCTIONS)}
        """
        cache_key = f"{self.lang.name}_transpile_interface_{spec_module.module_name}_{spec_item.spec_name}"
        response = LANGUAGE_MODEL.invoke(prompt, cache_key=cache_key, system_msg=self.system_msg)
        reasons, codeblocks, _ = LANGUAGE_MODEL.parse_standard_response(response, code_tag="code", code_langs=self.code_langs)
        assert "code" in codeblocks, "Expected code block in response."
        interface_code = codeblocks["code"]
        interface_file = self._interface_file(spec_module, spec_item)
        self.generated_interfaces[spec_module.module_name][spec_item.spec_name] = interface_code
        with open(interface_file, "w") as f:
            f.write(interface_code)
        print(interface_code)
        return interface_code

    def _prompt_implementation_header_transpilation(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass, dependency_context: str):
        prompt = f"""
{self.spec_planner._get_implementation_context(spec_module, spec_item, implementation, dependency_context)}
---
Interface Header for {spec_module.module_name}.{spec_item.spec_name} in file {self._interface_file(spec_module, spec_item)}:
{self.generated_interfaces[spec_module.module_name][spec_item.spec_name]}
---
{self.pseudocodes[spec_module.module_name][spec_item.spec_name][implementation.node.name]}
---

Your task: {self.lang.format_prompt(TRANSPILE_IMPLEMENTATION_HEADER_INSTRUCTIONS)}
        """
        cache_key = f"{self.lang.name}_transpile_header_{spec_module.module_name}_{spec_item.spec_name}_{implementation.node.name}"
        response = LANGUAGE_MODEL.invoke(prompt, cache_key=cache_key, system_msg=self.system_msg)
        reasons, codeblocks, _ = LANGUAGE_MODEL.parse_standard_response(response, code_tag="code", code_langs=self.code_langs)
        assert "code" in codeblocks, "Expected code block in response."
        header_code = codeblocks["code"]
        header_file = self._implementation_header_file(spec_module, spec_item, implementation)
        if spec_module.module_name not in self.generated_headers:
            self.generated_headers[spec_module.module_name] = {}
        if spec_item.spec_name not in self.generated_headers[spec_module.module_name]:
            self.generated_headers[spec_module.module_name][spec_item.spec_name] = {}
        self.generated_headers[spec_module.module_name][spec_item.spec_name][implementation.node.name] = header_code
        with open(header_file, "w") as f:
            f.write(header_code)
        return header_code

    def _prompt_implementation_source_transpilation(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass, dependency_context: str):
        if not self.lang.has_separate_header():
            implementation_header = ""
        else:
            implementation_header = f"Implementation Header for {spec_module.module_name}.{spec_item.spec_name}.{implementation.node.name} in file {self._implementation_header_file(spec_module, spec_item, implementation)}:\n{self.generated_headers[spec_module.module_name][spec_item.spec_name][implementation.node.name]}"
        common_context = f"""
{self.spec_planner._get_implementation_context(spec_module, spec_item, implementation, dependency_context)}
---
Interface for {spec_module.module_name}.{spec_item.spec_name} in file {self._interface_file(spec_module, spec_item)}:
{self.generated_interfaces[spec_module.module_name][spec_item.spec_name]}
---
{implementation_header}
---
{self.pseudocodes[spec_module.module_name][spec_item.spec_name][implementation.node.name]}
---
Your task: {self.lang.format_prompt(TRANSPILE_IMPLEMENTATION_SOURCE_INSTRUCTIONS)}
        """
        cache_key = f"{self.lang.name}_transpile_source_{spec_module.module_name}_{spec_item.spec_name}_{implementation.node.name}"
        response, confirmed = PROMPTING_PATTERNS.prompt_and_confirm(
            system_msg=self.system_msg,
            common_context=common_context,
            initial_instructions=self.lang.format_prompt(TRANSPILE_IMPLEMENTATION_SOURCE_INSTRUCTIONS),
            confirm_instructions=self.lang.format_prompt(TRANSPILE_IMPLEMENTATION_SOURCE_CONFIRMATION),
            cache_key=cache_key,
            num_iterations=5,
            expected_iterations=2,
            response_tag="code"
        )
        if not confirmed:
            raise NotImplementedError("Implementation source not confirmed. Next steps not implemented.")
        reasons, codeblocks, _ = LANGUAGE_MODEL.parse_standard_response(response, code_tag="code", code_langs=self.code_langs)
        assert "code" in codeblocks, "Expected code block in response."
        source_code = codeblocks["code"]
        source_file = self._implementation_source_file(spec_module, spec_item, implementation)
        with open(source_file, "w") as f:
            f.write(source_code)
        if not self.lang.has_separate_header():
            # Treat as header.
            header_code = source_code
            if spec_module.module_name not in self.generated_headers:
                self.generated_headers[spec_module.module_name] = {}
            if spec_item.spec_name not in self.generated_headers[spec_module.module_name]:
                self.generated_headers[spec_module.module_name][spec_item.spec_name] = {}
            self.generated_headers[spec_module.module_name][spec_item.spec_name][implementation.node.name] = header_code

        return source_code
    


def test_spec_transpiler():
    source_folder = "tree_src"
    tree = SpecTree(source_folder)
    planner = SpecPlanner(tree)
    pseudocoder = SpecPseudoCoder(planner)
    # lang = GO
    # lang = CPP
    lang = RUST
    transpiler = GenericSpecTranspiler(pseudocoder, lang)
    pass