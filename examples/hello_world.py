import os
from pydantic import SecretStr
from openhands.core import (
    OpenHandsConfig,
    Conversation,
    LLMConfig,
    Message,
    TextContent,
    LLM,
    Tool,
    get_logger,
    CodeActAgent,
)
from openhands.core.runtime.tools import (
    BashExecutor,
    FileEditorExecutor,
    execute_bash_tool,
    str_replace_editor_tool,
)

logger = get_logger(__name__)

# Configure LLM
api_key = os.getenv("LITELLM_API_KEY")
assert api_key is not None, "LITELLM_API_KEY environment variable is not set."
config = OpenHandsConfig(
    llm=LLMConfig(
        model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )
)
llm = LLM(config=config.llm)

# Tools
cwd = os.getcwd()
bash = BashExecutor(working_dir=cwd)
file_editor = FileEditorExecutor()
tools: list[Tool] = [
    execute_bash_tool.set_executor(executor=bash),
    str_replace_editor_tool.set_executor(executor=file_editor),
]

# Agent
agent = CodeActAgent(llm=llm, tools=tools)
conversation = Conversation(agent=agent)

conversation.send_message(
    message=Message(
        role="user",
        content=[
            TextContent(
                text="Hello! Can you create a new Python file named hello.py that prints 'Hello, World!'?"
            )
        ],
    )
)
