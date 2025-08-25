from __future__ import annotations

import json
from typing import Callable

import rich

from openhands.core.agenthub.agent import AgentBase
from openhands.core.llm import Message, TextContent
from openhands.core.runtime import ActionBase, ObservationBase


OnEvent = Callable[[Message | ActionBase | ObservationBase], None]


class Conversation:
    def __init__(self, agent: AgentBase, on_event: OnEvent | None = None):
        self.agent = agent
        self._on_event: OnEvent = on_event or self._default_on_event

    def set_callback(self, on_event: OnEvent) -> None:
        self._on_event = on_event

    def send_message(self, message: Message) -> None:
        self.agent.run(message, on_event=self._on_event)

    def _default_on_event(self, event: Message | ActionBase | ObservationBase) -> None:
        if isinstance(event, Message):
            role = event.role
            if role == "system":
                rich.print("[bold dim]System initialized[/bold dim]")
            elif role == "user":
                text = "\n".join(
                    c.text for c in event.content if isinstance(c, TextContent)
                )
                rich.print(f"[bold cyan]User:[/bold cyan] {text}")
            elif role == "assistant":
                if event.tool_calls:
                    tool_call = event.tool_calls[0]
                    rich.print(
                        "[bold blue]Assistant called tool:[/bold blue]\n"
                        + json.dumps(
                            {
                                "id": tool_call.id,
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                            indent=2,
                        )
                    )
                else:
                    text = "\n".join(
                        c.text for c in event.content if isinstance(c, TextContent)
                    )
                    rich.print(f"[bold green]Assistant:[/bold green] {text}")
            elif role == "tool":
                text = "\n".join(
                    c.text for c in event.content if isinstance(c, TextContent)
                )
                rich.print(f"[bold yellow]Tool observation:[/bold yellow] {text}")
            return

        if isinstance(event, ActionBase):
            rich.print(
                f"[bold yellow]Execute action:[/bold yellow] {event.__class__.__name__}\n"
                + json.dumps(event.model_dump(), indent=2)
            )
            return

        if isinstance(event, ObservationBase):
            rich.print(
                f"[bold magenta]Observation:[/bold magenta] {event.__class__.__name__}\n"
                + json.dumps(event.model_dump(), indent=2)
            )
            return
