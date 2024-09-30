from common.handles import LANGUAGE_MODEL, PROMPTING_PATTERNS
import typing as t
import os

from .spec_planner import SpecPlanner
from .spec_parser import (
    SpecTree,
    SpecModule,
    SpecItem,
    ParsedClass,
)

from .pseudocoder_prompts import (
    PSEUDOCODER_SYSTEM_MSG,
    PSEUDOCODER_INSTRUCTION,
    PSEUDOCODER_CONFIRMATION
)


class SpecPseudoCoder:
    def __init__(self, spec_planner: SpecPlanner):
        self.spec_planner = spec_planner
        self.spec_tree = spec_planner.spec_tree
        self._approved_pseudocodes: t.Dict[str, t.Dict[str, t.Dict[str, str]]] = {}
        self._recover_approved_pseudocodes()
        spec_planner._process_tree(spec_planner._process_module, self._process_item)


    def _process_item(self, module_name: str, item_name: str):
        print(f"Pseudocoding item: {item_name}. Module: {module_name}")
        spec_module = self.spec_tree.spec_modules[module_name]
        spec_item = spec_module.spec_items[item_name]
        dependency_context = self.spec_planner.make_dependency_context(spec_item, with_concrete_impl=True)
        for implementation_name, implementation in spec_item.implementations.items():
            if implementation_name in self._approved_pseudocodes[module_name][item_name]:
                continue
            self._prompt_pseudocode(spec_module, spec_item, implementation, dependency_context)
        pass


    def _pseudocode_folder(self, spec_module: SpecModule):
        return f"{spec_module.module_folder}/assistant_pseudocodes"

    def _pseudocode_filepath(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass):
        return f"{self._pseudocode_folder(spec_module)}/{spec_item.spec_name}_{implementation.node.name}.py"

    def _prompt_pseudocode(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass, dependency_context: str):
        implementation_context = self.spec_planner._get_implementation_context(spec_module, spec_item, implementation, dependency_context)
        implementation_plan = self.spec_planner.generated_plans[spec_module.module_name][spec_item.spec_name][implementation.node.name]
        common_context = f"""
{implementation_context}
---
Here is the implementation plan. Follow it well.
{implementation_plan}
        """
        cache_key = f"pseudocode_{spec_module.module_name}_{spec_item.spec_name}_{implementation.node.name}"
        response, confirmed = PROMPTING_PATTERNS.prompt_and_confirm(
            system_msg=PSEUDOCODER_SYSTEM_MSG,
            common_context=common_context,
            initial_instructions=PSEUDOCODER_INSTRUCTION,
            confirm_instructions=PSEUDOCODER_CONFIRMATION,
            cache_key=cache_key,
            num_iterations=3,
            expected_iterations=2,
            response_tag="code"
        )
        if not confirmed:
            raise NotImplementedError("Pseudocode not confirmed. Next steps not implemented.")
        _, codeblocks, _ = LANGUAGE_MODEL.parse_standard_response(response, code_tag="code")
        code = codeblocks["code"]
        pseudocode_filepath = self._pseudocode_filepath(spec_module, spec_item, implementation)
        with open(pseudocode_filepath, "w") as f:
            f.write(code)
        print(code)
        pass


    def _recover_approved_pseudocodes(self):
        for module_name, module in self.spec_tree.spec_modules.items():
            self._approved_pseudocodes[module_name] = {}
            valid_files = set()
            module_folder = self._pseudocode_folder(module)
            if not os.path.exists(module_folder):
                os.makedirs(module_folder, exist_ok=True)
            for item_name, item in module.spec_items.items():
                self._approved_pseudocodes[module_name][item_name] = {}
                for implementation_name, implementation in item.implementations.items():
                    pseudocode_filepath = self._pseudocode_filepath(module, item, implementation)
                    if os.path.exists(pseudocode_filepath):
                        with open(pseudocode_filepath, "r") as f:
                            content = f.read()
                            # TODO: Should actually parse the file and look for the variable.
                            if "APPROVED = True" in content:
                                self._approved_pseudocodes[module_name][item_name][implementation_name] = content
                                valid_files.add(pseudocode_filepath)
            # Delete invalid files
            for file in os.listdir(self._pseudocode_folder(module)):
                if file not in valid_files:
                    # os.remove(f"{self._pseudocode_folder(module)}/{file}")
                    pass


def test_spec_pseudocoder():
    source_folder = "tree_src"
    tree = SpecTree(source_folder)
    planner = SpecPlanner(tree)
    pseudocoder = SpecPseudoCoder(planner)
    pass