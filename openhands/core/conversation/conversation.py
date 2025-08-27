from __future__ import annotations

from openhands.core.agent import AgentBase
from openhands.core.llm import Message

from .state import ConversationState
from .types import ConversationCallbackType
from .visualizer import ConversationVisualizer


class Conversation:
    def __init__(self, agent: AgentBase, on_event: ConversationCallbackType | None = None):
        self._visualizer = ConversationVisualizer()
        self._on_event: ConversationCallbackType = on_event or self._visualizer.on_event
        
        self.agent = agent
        self.state = ConversationState()
        self.state = self.agent.init_state(self.state, on_event=self._on_event)

    def send_message(self, message: Message) -> None:
        """Sending messages to the agent."""
        messages = self.state.history.messages
        messages.append(message)
        if self._on_event:
            self._on_event(message)
        self.state = self.agent.step(self.state, on_event=self._on_event)

    def run(self) -> None:
        self.state = self.agent.step(self.state, on_event=self._on_event)
