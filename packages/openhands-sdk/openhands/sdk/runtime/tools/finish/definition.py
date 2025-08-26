"""Finish tool implementation."""

from pydantic import Field

from openhands.sdk.runtime.schema import ActionBase
from openhands.sdk.runtime.tool import Tool, ToolAnnotations


class FinishAction(ActionBase):
    message: str = Field(description="Final message to send to the user.")


TOOL_DESCRIPTION = """Signals the completion of the current task or conversation.

Use this tool when:
- You have successfully completed the user's requested task
- You cannot proceed further due to technical limitations or missing information

The message should include:
- A clear summary of actions taken and their results
- Any next steps for the user
- Explanation if you're unable to complete the task
- Any follow-up questions if more information is needed
"""


finish_tool = Tool(
    name="finish",
    input_schema=FinishAction,
    description=TOOL_DESCRIPTION,
    annotations=ToolAnnotations(
        title="finish",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
