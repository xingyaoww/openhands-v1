# Task List

1. ✅ Fetch and analyze GitHub issue #19 details
Used GitHub API to retrieve issue. Issue requests setting LiteLLM logging to WARNING by default to suppress noisy INFO logs.
2. ✅ Locate logging configuration and analyze LiteLLM logging behavior
Identified openhands/core/logger.py controlling litellm behavior. Existing code toggled litellm.suppress_debug_info and set_verbose but didn't set Python logger levels.
3. 🔄 Implement change to set LiteLLM loggers to WARNING by default
Add helper to set levels for 'LiteLLM' and 'litellm' to WARNING unless DEBUG_LLM confirmed; then set to DEBUG.
4. ⏳ Add minimal test verifying LiteLLM logger level is WARNING by default

5. ⏳ Run pre-commit hooks on changed files

6. ⏳ Run pytest and ensure all tests pass

7. ⏳ Create branch, commit changes, push, and open PR referencing issue #19


