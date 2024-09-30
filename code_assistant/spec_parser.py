import ast
from common.handles import LANGUAGE_MODEL
from collections import OrderedDict
import os
import typing as t
from typing import NamedTuple
from ordered_set import OrderedSet

class SpecItem:
    """Represents an individual item (e.g., one class) in the spec."""
    def __init__(self, parent_module_name, spec_name, path):
        self.parent_module_name = parent_module_name
        self.spec_name = spec_name
        self.filepath = path
        # Contains global dependencies. Used by the module to resolve dependencies.
        self.dependencies: t.Dict[str, t.Set[str]] = {}
        self._unresolved_dependencies: t.List[t.List[str]] = []
        self.interface: t.Optional[ParsedClass] = None
        self.implementations: t.Dict[str, ParsedClass] = OrderedDict()
        self._initialize()


    def _resolve_dependencies(self, tree: "SpecTree"):
        print(f"Resolving dependencies for {self.spec_name}: {self._unresolved_dependencies}")
        for unresolved_dep in self._unresolved_dependencies:
            if len(unresolved_dep) == 3:
                # Expected case: from a.b import c
                module_name = unresolved_dep[0]
                if len(module_name) == 0:
                    # Relative import
                    module_name = self.parent_module_name
                item_names = [unresolved_dep[1]]
            elif len(unresolved_dep) == 2:
                # Expected case: import a.b
                module_name = unresolved_dep[0]
                if len(module_name) == 0:
                    # Relative import
                    module_name = self.parent_module_name
                item_names = [unresolved_dep[1]]
            elif len(unresolved_dep) == 1:
                # Expected case: import a
                module_name = unresolved_dep[0]
                assert len(module_name) > 0, "Global import's module name must be non-empty"
                if module_name in tree.spec_modules:
                    item_names = tree.spec_modules[module_name].spec_items.keys()
                else:
                    # Not an export for our tool.
                    continue
            else:
                # Not an export for our tool.
                continue
            if module_name not in tree.spec_modules:
                # Not an export for our tool.
                continue
            for item_name in item_names:
                if item_name not in tree.spec_modules[module_name].spec_items:
                    # Not an export for our tool.
                    continue
                if module_name not in self.dependencies:
                    self.dependencies[module_name] = OrderedSet()
                self.dependencies[module_name].add(item_name)
        print(f"Resolved dependencies for {self.spec_name}: {self.dependencies}")
        self._unresolved_dependencies = []

    def _initialize(self):
        with open(self.filepath) as f:
            content = f.read()
        parsed_spec = SpecFileParser(content)
        self.interface = parsed_spec.interface
        self.implementations = parsed_spec.implementations
        self._unresolved_dependencies = parsed_spec.imports

    def __str__(self):
        return f"SpecItem({self.parent_module_name}.{self.spec_name})"
    
    def __repr__(self):
        return self.__str__()

class SpecModule:
    """Represents a module (set of related items) in the spec."""
    def __init__(self, module_name, module_folder):
        self.module_name = module_name
        self.module_folder = module_folder
        self.api_spec = ""
        self.spec_items: t.Dict[str, SpecItem] = {}
        self._unresolved_dependencies: t.List[t.List[str]] = []
        # Contains only dependencies within this module.
        self.inner_dependencies: t.Dict[str, t.Set[str]] = {}
        self.outer_dependencies: t.Set[str] = OrderedSet()
        self._initialize()
    
    
    def _resolve_dependencies(self, tree: "SpecTree"):
        # Resolved at the item level.
        # Each item tracks its global dependencies.
        for item in self.spec_items.values():
            item._resolve_dependencies(tree)
        # Now resolve the dependencies of this module.
        # This is used as an ordering for processing the items.
        for item_name, item in self.spec_items.items():
            for parent_module, deps in item.dependencies.items():
                if parent_module == self.module_name:
                    self.inner_dependencies[item_name] = deps
                else:
                    self.outer_dependencies.add(parent_module)
            # Add empty set for items with no dependencies.
            if item_name not in self.inner_dependencies:
                self.inner_dependencies[item_name] = OrderedSet()


    def _initialize(self):
        """Read the module folder and initialize the spec items."""
        init_file = os.path.join(self.module_folder, "__init__.py")
        with open(init_file) as f:
            content = f.read()
        parsed_spec = SpecFileParser(content)
        self.api_spec = parsed_spec.file_docstring
        self._unresolved_dependencies = parsed_spec.imports
        # Iterate through the folder.
        for file in os.listdir(self.module_folder):
            if file == "__init__.py" or not file.endswith(".py"):
                continue
            spec_name = file.split(".")[0]
            filepath = os.path.join(self.module_folder, file)
            self.spec_items[spec_name] = SpecItem(self.module_name, spec_name, filepath)

    
    def __str__(self):
        sep = "" if len(self.spec_items) == 0 else "\n"
        child_strs = [f"    {str(item)}" for item in self.spec_items.values()]
        child_strs = ",\n".join(child_strs) 
        return f"SpecModule({self.module_name},{sep}{child_strs})"
    
    def __repr__(self):
        return self.__str__()

class SpecTree:
    """Represents the entire spec tree."""
    def __init__(self, source_folder: str):
        """Create a spec tree from the given source folder."""
        self.source_folder: str = source_folder
        self.spec_modules: t.Dict[str, SpecModule] = {}
        self.module_dependencies: t.Dict[str, t.Set[str]] = {}
        self._initialize()


    def _initialize(self):
        for module_folder in os.listdir(self.source_folder):
            module_name = module_folder
            module_folder = os.path.join(self.source_folder, module_folder)
            # Check if it's a directory
            if not os.path.isdir(module_folder):
                continue
            # Check if `__init__.py` exists
            if not os.path.exists(os.path.join(module_folder, "__init__.py")):
                continue
            module = SpecModule(module_name, module_folder)
            self.spec_modules[module_name] = module
        self._resolve_dependencies()

    def _resolve_dependencies(self):
        for module in self.spec_modules.values():
            module._resolve_dependencies(self)
            self.module_dependencies[module.module_name] = module.outer_dependencies

    def _make_dependency_graph(self):
        pass

    def __str__(self):
        sep = "" if len(self.spec_modules) == 0 else "\n"
        child_strs = [f"  {str(module)}" for module in self.spec_modules.values()]
        child_strs = ",\n".join(child_strs)
        return f"SpecTree({self.source_folder}, {sep}{child_strs}{sep})"
    
    def __repr__(self):
        return self.__str__()

class ParsedClass(NamedTuple):
    """Represents a single implementation spec."""
    node: ast.ClassDef
    code: str
    docstring: str


class SpecFileParser(ast.NodeVisitor):
    def __init__(self, source):
        self.source = source
        self.ast_node = ast.parse(source)
        self.file_docstring = ast.get_docstring(self.ast_node)
        self.interface: t.Optional[ParsedClass] = None
        self.implementations: t.Dict[str, ParsedClass] = OrderedDict()
        self.imports: t.List[t.List[str]] = []
        
        # Visit the AST
        self.visit(self.ast_node)
    
    def visit_Module(self, node):
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        class_name = node.name
        if class_name.endswith("Interface"):
            code = ast.get_source_segment(self.source, ast.parse(node))
            docstring = ast.get_docstring(node)
            if self.interface is not None:
                raise ValueError("Multiple interfaces not supported")
            self.interface = ParsedClass(node, code, docstring)
        else:
            # Check that this implementation inherits from the interface
            assert self.interface is not None, "Interface must be before implementations"
            assert len(node.bases) == 1, "Only single inheritance supported"
            assert node.bases[0].id == self.interface.node.name, "Implementation must inherit from interface"
            code = ast.get_source_segment(self.source, ast.parse(node))
            docstring = ast.get_docstring(node)
            self.implementations[class_name] = ParsedClass(node, code, docstring)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        # Parse a.b.c as ['a', 'b', 'c']
        self.imports.append([alias.name for alias in node.names])

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Parse from a.b import c as ['a', 'b', 'c']
        # Parse from .a import b as ['', 'a', 'b']
        modules = [] if node.module is None else node.module.split(".")
        print(f"Import from: {modules}. {node.names}. {node.module}. Level={node.level}")
        if node.level == 1:
            # Relative import
            modules = [""] + modules
        elif node.level > 1 or node.level < 0:
            raise NotImplementedError("Support complex relative imports!")
        self.imports.append(modules + [alias.name for alias in node.names])

def test_spec_parser():
    src_folder = "tree_src"
    tree = SpecTree(src_folder)
    print(tree)
    pass