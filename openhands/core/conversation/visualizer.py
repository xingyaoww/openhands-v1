import json

from rich.console import Console
from rich.panel import Panel

from openhands.core.llm import Message, TextContent
from openhands.core.tool import ActionBase, ObservationBase


class ConversationVisualizer:
    """Handles visualization of conversation events with clean, readable formatting."""

    def __init__(self):
        self._console = Console()

    def on_event(self, event: Message | ActionBase | ObservationBase) -> None:
        """Main event handler that routes events to appropriate render methods."""
        if isinstance(event, Message):
            self._render_message(event)
        elif isinstance(event, ActionBase):
            self._render_action(event)
        elif isinstance(event, ObservationBase):
            self._render_observation(event)

    def _render_message(self, message: Message) -> None:
        """Render a message with clean formatting."""
        role = message.role

        if role == "system":
            self._console.print("🔧 [dim]System initialized[/dim]")
            return

        text = "\n".join(c.text for c in message.content if isinstance(c, TextContent))

        if role == "user":
            panel = Panel(
                text,
                title="👤 User",
                title_align="left",
                border_style="cyan",
                padding=(0, 1),
            )
            self._console.print(panel)

        elif role == "assistant":
            if message.tool_calls:
                self._render_tool_call(message.tool_calls[0])
            else:
                panel = Panel(
                    text,
                    title="🤖 Assistant",
                    title_align="left",
                    border_style="green",
                    padding=(0, 1),
                )
                self._console.print(panel)

        elif role == "tool":
            # Tool responses are handled in _render_observation
            pass

    def _render_tool_call(self, tool_call) -> None:
        """Render a tool call with clean formatting."""
        try:
            args = json.loads(tool_call.function.arguments)
            args_text = ""
            for key, value in args.items():
                value = str(value)
                if len(value) > 100:
                    value = value[:97] + "..."
                args_text += f"  {key}: {value}\n"

        except (json.JSONDecodeError, AttributeError):
            args_text = f"  arguments: {tool_call.function.arguments}"

        content = f"🔧 [bold blue]{tool_call.function.name}[/bold blue]\n{args_text.rstrip()}"

        panel = Panel(
            content,
            title="⚡ Tool Call",
            title_align="left",
            border_style="blue",
            padding=(0, 1),
        )
        self._console.print(panel)

    def _render_action(self, action: ActionBase) -> None:
        """Render an action with minimal noise."""
        # Actions are usually redundant with tool calls, so show minimal info
        self._console.print(f"  → Executing [dim]{action.__class__.__name__}[/dim]")

    def _render_observation(self, observation: ObservationBase) -> None:
        """Render an observation with smart content handling."""
        # Extract the most relevant content
        obs_data = observation.model_dump()
        content = observation.agent_observation

        # Color code based on success/failure
        border_style = "red" if ("error" in obs_data and obs_data["error"]) else "yellow"

        panel = Panel(
            content,
            title="📋 Result",
            title_align="left",
            border_style=border_style,
            padding=(0, 1),
        )
        self._console.print(panel)
        self._console.print()  # Add spacing after observations

