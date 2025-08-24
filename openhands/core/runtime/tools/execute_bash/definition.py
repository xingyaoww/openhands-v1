"""Execute bash tool implementation."""

from pydantic import Field

from openhands.core.runtime.tool import Tool, ToolAnnotations
from openhands.core.runtime.schema import ActionBase, ObservationBase
from openhands.core.runtime.security import SECURITY_RISK_DESC, SECURITY_RISK_LITERAL


class ExecuteBashAction(ActionBase):
    """Schema for bash command execution."""

    command: str = Field(
        description="The bash command to execute. Can be empty string to view additional logs when previous exit code is `-1`. Can be `C-c` (Ctrl+C) to interrupt the currently running process. Note: You can only execute one bash command at a time. If you need to run multiple commands sequentially, you can use `&&` or `;` to chain them together."
    )
    is_input: bool = Field(
        default=False,
        description="If True, the command is an input to the running process. If False, the command is a bash command to be executed in the terminal. Default is False.",
    )
    timeout: float | None = Field(
        default=None,
        description="Optional. Sets a hard timeout in seconds for the command execution. If not provided, the command will use the default soft timeout behavior.",
    )
    security_risk: SECURITY_RISK_LITERAL = Field(description=SECURITY_RISK_DESC)


class ExecuteBashObservation(ObservationBase):
    """A ToolResult that can be rendered as a CLI output."""

    output: str = Field(
        default="", description="The output from the command execution (stdout)."
    )
    exit_code: int = Field(
        default=0,
        description="The exit code of the command. -1 indicates the process hit the soft timeout and is not yet finished.",
    )
    error: str = Field(
        default="", description="Any error output from the command execution (stderr)."
    )
    timeout: bool = Field(
        default=False, description="Whether the command execution timed out."
    )


TOOL_DESCRIPTION = """Execute a bash command in the terminal within a persistent shell session.


### Command Execution
* One command at a time: You can only execute one bash command at a time. If you need to run multiple commands sequentially, use `&&` or `;` to chain them together.
* Persistent session: Commands execute in a persistent shell session where environment variables, virtual environments, and working directory persist between commands.
* Soft timeout: Commands have a soft timeout of 10 seconds, once that's reached, you have the option to continue or interrupt the command (see section below for details)
* Shell options: Do NOT use `set -e`, `set -eu`, or `set -euo pipefail` in shell scripts or commands in this environment. The runtime may not support them and can cause unusable shell sessions. If you want to run multi-line bash commands, write the commands to a file and then run it, instead.

### Long-running Commands
* For commands that may run indefinitely, run them in the background and redirect output to a file, e.g. `python3 app.py > server.log 2>&1 &`.
* For commands that may run for a long time (e.g. installation or testing commands), or commands that run for a fixed amount of time (e.g. sleep), you should set the "timeout" parameter of your function call to an appropriate value.
* If a bash command returns exit code `-1`, this means the process hit the soft timeout and is not yet finished. By setting `is_input` to `true`, you can:
  - Send empty `command` to retrieve additional logs
  - Send text (set `command` to the text) to STDIN of the running process
  - Send control commands like `C-c` (Ctrl+C), `C-d` (Ctrl+D), or `C-z` (Ctrl+Z) to interrupt the process
  - If you do C-c, you can re-start the process with a longer "timeout" parameter to let it run to completion

### Best Practices
* Directory verification: Before creating new directories or files, first verify the parent directory exists and is the correct location.
* Directory management: Try to maintain working directory by using absolute paths and avoiding excessive use of `cd`.

### Output Handling
* Output truncation: If the output exceeds a maximum length, it will be truncated before being returned.
"""


execute_bash_tool = Tool(
    name="execute_bash",
    input_schema=ExecuteBashAction,
    output_schema=ExecuteBashObservation,
    description=TOOL_DESCRIPTION,
    annotations=ToolAnnotations(
        title="execute_bash",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
