
from pydantic import BaseModel, Field

from openhands.core.context import AgentHistory


class ConversationState(BaseModel):
    history: AgentHistory = Field(default_factory=AgentHistory)
    agent_finished: bool = Field(default=False, description="Whether the agent has finished the conversation.")
