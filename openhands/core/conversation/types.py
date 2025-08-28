from typing import Callable

from openhands.core.llm import Message
from openhands.core.tool import ActionBase, ObservationBase


ConversationEventType = Message | ActionBase | ObservationBase
ConversationCallbackType = Callable[[ConversationEventType], None]
