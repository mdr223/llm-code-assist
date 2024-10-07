from common.handles import LANGUAGE_MODEL, PROMPTING_PATTERNS
import os
import toml

from .spec_parser import (
    SpecTree,
    SpecModule,
    SpecItem,
    ParsedClass,
)

from .planner_prompts import (
    PLAN_SYSTEM_MSG,
    INFORMAL_PLAN_EXAMPLE,
    INFORMAL_BASIC_PLAN_INSTRUCTIONS,
    CONFIRM_INFORMAL_BASIC_PLAN_INSTRUCTIONS,
    FORMAL_IMPLEMENTATION_PLAN_INSTRUCTIONS,
)

import typing as t

class SpecUnitTestGenerator:
    def __init__(self, spec_tree: SpecTree):
        self.spec_tree = spec_tree
        

class SpecPlanner:
    def __init__(self, spec_tree: SpecTree):
        self.spec_tree = spec_tree
        self.generated_plans: t.Dict[str, t.Dict[str, t.Dict[str, str]]] = {}
        self._recover_approved_plan()
        self._process_tree(self._process_module, self._process_item)


    def make_dependency_context(self, spec_item: SpecItem, with_concrete_impl: bool) -> str:
        dep_specs = []
        item_sep = "\n" + ("_" * 5) + "\n"
        module_sep = "\n" + ("_" * 10) + "\n"
        dep_sep = "\n" + ("_" * 15) + "\n"
        # Iterate through dependencies
        for dep_module_name, dep_item_names in spec_item.dependencies.items():
            # Add module context unless it's the parent module
            dep_module = self.spec_tree.spec_modules[dep_module_name]
            if dep_module_name == spec_item.parent_module_name:
                module_spec = ""
            else:
                module_spec = dep_module.api_spec
            # Add item contexts.
            dep_spec = []
            for dep_item_name in dep_item_names:
                dep_item = dep_module.spec_items[dep_item_name]
                # Get the interface context.
                interface_context = f"# Interface Dependency:\n{dep_item.interface.code}\n"
                # Get concrete implementation context if requested.
                concrete_context = ""
                if with_concrete_impl:
                    dep_impls = dep_item.implementations.values()
                    if len(dep_impls) > 0:
                        concrete_context = "\n\n\n".join([f"# Concrete Dependency:\n{x.code}" for x in dep_impls])
                        concrete_context = f"\n\n\n{concrete_context}"
                # Make item context.
                dep_item_context = f"{item_sep}Dependency on {dep_item_name}:\n```py\n{interface_context}{concrete_context}\n```{item_sep}"
                dep_spec.append(dep_item_context)
            dep_spec = "".join(dep_spec)
            dep_spec = f"{module_sep}Dependencies from module `{dep_module_name}`:\n{module_spec}{dep_spec}{module_sep}"
            dep_specs.append(dep_spec)
        dep_specs = "".join(dep_specs)
        if len(dep_specs) > 0:
            dep_specs = f"{dep_sep}Start Dependency Specs.\n{dep_specs}\nEnd of Dependency Specs.{dep_sep}"
        return dep_specs


    def _process_item(self, module_name: str, item_name: str):
        """Process the implementations of the given item in the current module."""
        print(f"Processing item: {item_name}. Module: {module_name}")
        spec_module: SpecModule = self.spec_tree.spec_modules[module_name]
        spec_item: SpecItem = spec_module.spec_items[item_name]
        dep_specs = self.make_dependency_context(spec_item, with_concrete_impl=False)
        for implementation in spec_item.implementations.values():
            if implementation.node.name in self.generated_plans[module_name][item_name]:
                print(f"Skipping approved plan for {module_name}.{item_name}.{implementation.node.name}")
                continue
            plan = self._prompt_formal_plan(spec_module, spec_item, implementation, dep_specs)
            self.generated_plans[module_name][item_name][implementation.node.name] = plan
        # exit(0)
        pass

    def _process_module(self, module_name: str, process_item_fn: t.Callable[[str, str], None]):
        """Process the items in the given module."""
        print(f"Pre-Processing module: {module_name}")
        process_fn = lambda item_name: process_item_fn(module_name, item_name)
        graph = self.spec_tree.spec_modules[module_name].inner_dependencies.copy()
        print(f"Module Graph: {graph}")
        self.traverse_graph(graph, set(), process_fn)
        print(f"Post-Processing module: {module_name}")
        pass

    def _process_tree(self, process_module_fn: t.Callable[[str, t.Callable[[str, str], None]], None], process_item_fn: t.Callable[[str], None]):
        process_fn = lambda module_name: process_module_fn(module_name, process_item_fn)
        graph = self.spec_tree.module_dependencies.copy()
        print(f"Tree Graph: {graph}")
        self.traverse_graph(graph, set(), process_fn)

    def traverse_graph(self, curr_graph: t.Dict[str, t.List[str]], processed: t.Set[str], process_fn: t.Callable[[str], None]):
        """Recursively traverse the graph and process each module."""
        # TODO: Make more efficient. This may iterate over the same nodes multiple times (but only process each once).
        if len(curr_graph) == 0:
            # All modules processed
            return
        # Find next unprocessed module with all dependencies processed
        for module_name in curr_graph:
            # Processed things should not be in the graph
            assert module_name not in processed
            # Check if all dependencies are processed
            deps = curr_graph[module_name]
            all_children_processed = True
            for dep in deps:
                if dep not in processed:
                    all_children_processed = False
                    break
            # Process if all dependencies are processed
            if all_children_processed:
                process_fn(module_name)
                processed.add(module_name)
                del curr_graph[module_name]
                return self.traverse_graph(curr_graph, processed, process_fn)
        assert False, "Should not reach here."

    def _plan_directory(self, spec_module: SpecModule):
        return f"{spec_module.module_folder}/assistant_plans"

    def _informal_plan_filepath(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass, extension: str):
        parent_folder = self._plan_directory(spec_module)
        if not os.path.exists(parent_folder):
            os.makedirs(parent_folder, exist_ok=True)
        return f"{parent_folder}/{spec_item.spec_name}_{implementation.node.name}.{extension}"


    def _get_implementation_context(self, spec_module: SpecModule, spec_item: SpecItem, implementation: t.Optional[ParsedClass], dep_specs: str):
        # TODO: Include dependencies.
        implementation_notes = ""
        if implementation is not None:
            implementation_notes = f"Here are essential implementation notes for the item:\n{implementation.code}"
        return f"""
---
{dep_specs}
---
Here is the spec for parent module `{spec_module.module_name}` this belongs to:
{spec_module.api_spec}
---
Here is the spec for the item `{spec_module.module_name}.{spec_item.spec_name}` itself:
{spec_item.interface.code}
---
{implementation_notes}
""".strip()


    def _prompt_formal_plan(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass, dep_specs: str):
        """Prompt for a formal plan for the given item in the given module."""
        informal_plan = self._prompt_informal_plan(spec_module, spec_item, implementation, dep_specs)
        prompt = f"""
{self._get_implementation_context(spec_module, spec_item, implementation, dep_specs)}
---
Here is the informal plan you provided:
{informal_plan}
---
Your task: {FORMAL_IMPLEMENTATION_PLAN_INSTRUCTIONS}
""".strip()
        cache_key = f"formal_plan_{spec_module.module_name}_{spec_item.spec_name}_{implementation.node.name}"
        response = LANGUAGE_MODEL.invoke(prompt, cache_key=cache_key, system_msg=PLAN_SYSTEM_MSG)
        _, codeblocks, _attrs = LANGUAGE_MODEL.parse_standard_response(response, code_tag="plan", code_langs=["toml"])
        plan = codeblocks["plan"]
        print(f"Plan:\n{plan}")
        filepath = self._informal_plan_filepath(spec_module, spec_item, implementation, "toml")
        with open(filepath, "w") as f:
            f.write(plan)
        # exit(0)
        return plan


    def _prompt_informal_plan(self, spec_module: SpecModule, spec_item: SpecItem, implementation: ParsedClass, dep_specs: str):
        """Prompt for an informal plan for the given item in the given module."""
        common_context = f"""
{self._get_implementation_context(spec_module, spec_item, implementation, dep_specs)}
---
Here is an example of what a plan should look like:
{INFORMAL_PLAN_EXAMPLE}
"""
        cache_key = f"basic_informal_plan_{spec_module.module_name}_{spec_item.spec_name}_{implementation.node.name}"
        response, confirmed = PROMPTING_PATTERNS.prompt_and_confirm(
            system_msg=PLAN_SYSTEM_MSG,
            common_context=common_context,
            initial_instructions=INFORMAL_BASIC_PLAN_INSTRUCTIONS,
            confirm_instructions=CONFIRM_INFORMAL_BASIC_PLAN_INSTRUCTIONS,
            cache_key=cache_key,
            num_iterations=3,
            expected_iterations=2,
            response_tag="plan"
        )
        _, codeblocks, _attrs = LANGUAGE_MODEL.parse_standard_response(response, code_tag="plan", code_langs=["md"])
        plan = codeblocks["plan"]
        if not confirmed:
            raise NotImplementedError("Figure out what to do when the LLM doesn't confirm the plan.")
        print(f"Plan:\n{plan}")
        return plan
    
    def _recover_approved_plan(self):
        for module_name, spec_module in self.spec_tree.spec_modules.items():
            self.generated_plans[module_name] = {}
            valid_files = set()
            for item_name, spec_item in spec_module.spec_items.items():
                self.generated_plans[module_name][item_name] = {}
                for implementation in spec_item.implementations.values():
                    filepath = self._informal_plan_filepath(spec_module, spec_item, implementation, "toml")
                    if os.path.exists(filepath):
                        with open(filepath) as f:
                            plan_str = f.read()
                            parsed_plan = toml.loads(plan_str)
                            if "approved" in parsed_plan and parsed_plan["approved"]:
                                print(f"Recovered approved plan for {module_name}.{item_name}.{implementation.node.name}")
                                self.generated_plans[module_name][item_name][implementation.node.name] = plan_str
                                valid_files.add(filepath)
            plan_dir = self._plan_directory(spec_module)
            # Delete all files ending with .toml that are not in valid_files
            for file in os.listdir(plan_dir):
                if file.endswith(".toml") and os.path.join(plan_dir, file) not in valid_files:
                    os.remove(os.path.join(plan_dir, file))
        pass

def test_spec_unit_test_generator():
    source_folder = "tree_src"
    tree = SpecTree(source_folder)
    planner = SpecPlanner(tree)
