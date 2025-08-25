from openhands.core.agenthub.agent import AgentBase
from openhands.core.llm import Message


class Conversation:
    def __init__(self, agent: AgentBase):
        self.agent = agent

    def send_message(self, message: Message):
        self.agent.run(message)
