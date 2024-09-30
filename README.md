# LLM Code Assistant
- Most of the code is in `code_assistant/`.
- The spec used for testing is in `tree_src/`.
- Components:
    - Spec Parser: `code_assistant/spec_parser.py`.
        - Reads `tree_src` folder and builds a tree of the spec.
        - Checkout `SpecTree`, `SpecModule` and `SpecItem` for the different elements in the spec.
    - Spec Planner: `code_assistant/spec_planner.py`.
        - Takes the tree and generates a plan for the code.
        - Checkout `prompt_*` functions for the different steps in the plan.
    - Spec Pseudocoder: `code_assistant/spec_pseudocoder.py`.
        - Takes the plan and generates pseudocode.
    - Spec Transpiler: `code_assistant/spec_transpiler.py`.
        - Takes the pseudocode and transpiles it to actual code.
        - Also checkout `prompt_*` functions for the different steps in the transpilation.
    - Other useful stuff in `common/`.
        - Especially `common/language_model.py` and `common/prompting_patterns.py`.

# Adding new steps
- To add a new, just make `spec_<step_name>.py` in `code_assistant/`.
    - Maybe use the planner or pseudocoder's `_process_item()` function as a starting guide.