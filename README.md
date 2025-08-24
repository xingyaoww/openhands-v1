# Prototype for OpenHands V1

[![Coverage](badges/coverage.svg)](./badges/coverage.svg)

This folder contains my tasks of completely refactor [OpenHands](https://github.com/All-Hands-AI/OpenHands) project V0 into the new V1 version. There's a lot of changes, including (non-exhausive):

- Switching from poetry to uv as package manager
- better dependency management
  - include `--dev` group for development only
- stricter pre-commit hooks `.pre-commit-config.yaml` that includes
  - type check through pyright
  - linting and formatter with `uv ruff`
- cleaner architecture for how a tool works and how it is executed
  - read about how we define tools: [`openhands/core/runtime/tool.py`](openhands/core/runtime/tool.py)
  - read about how we define schema (input/output) for tools: [`openhands/core/runtime/schema.py`](openhands/core/runtime/schema.py)
  - read about patterns for how we define an executable tool:
    - read [openhands/core/runtime/tools/str_replace_editor/impl.py](openhands/core/runtime/tools/str_replace_editor/impl.py) for tool execute_fn
    - read [openhands/core/runtime/tools/str_replace_editor/definition.py](openhands/core/runtime/tools/str_replace_editor/definition.py) for how do we define a tool
    - read [openhands/core/runtime/tools/str_replace_editor/__init__.py](openhands/core/runtime/tools/str_replace_editor/__init__.py) for how we define each tool module
- ...
