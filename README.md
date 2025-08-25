# Prototype for OpenHands V1

[![Coverage](docs/assets/coverage.svg)](./docs/assets/coverage.svg)

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
- tools: `str_replace_editor`, `execute_bash`
- minimal config (OpenHandsConfig, LLMConfig, MCPConfig): `openhands/core/config`
- core set of LLM (w/o tests): `openhands/core/llm`
- core set of microagent functionality (w/o full integration):
  - `openhands/core/context`: redesigned the triggering of microagents w.r.t. agents into the concept of two types context
    - EnvContext (triggered at the begining of a convo)
    - MessageContext (triggered at each user message)
  - `openhands-v1/openhands/core/microagents`: old code from V1 that loads microagents from folders, etc
- minimal implementation of codeact agent: `openhands-v1/openhands/core/agenthub/codeact_agent`
- ...


**Check hello world example**

```bash
uv sync
uv run python examples/hello.py
```
