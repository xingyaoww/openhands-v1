
from rich.console import Console

from openhands.core.event import EventType


class ConversationVisualizer:
    """Handles visualization of conversation events with clean, readable formatting."""

    def __init__(self):
        self._console = Console()

    def on_event(self, event: EventType) -> None:
        """Main event handler that routes events to appropriate render methods."""
        Console().rule(f"[bold blue]New Event: {event.__class__.__name__}[/bold blue]")
        if hasattr(event, "to_llm_message"):
            llm_message = event.to_llm_message()
            self._console.print(llm_message)
