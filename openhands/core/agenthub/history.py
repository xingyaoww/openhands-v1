from pydantic import BaseModel, Field
from openhands.core.llm import Message


class AgentHistory(BaseModel):
    messages: list[Message] = Field(
        default_factory=list,
        description="List of messages exchanged during the agent's session",
    )
    microagent_activations: list[tuple[str, int]] = Field(
        default_factory=list,
        description="List of tuples containing microagent names and the index in .messages where they were activated",
    )

    def clear(self) -> None:
        """Clears the agent's history."""
        self.messages.clear()
        self.microagent_activations.clear()

    def __len__(self) -> int:
        return len(self.messages)
