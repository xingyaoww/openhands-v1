from typing import Callable

from openhands.core.llm import Message
from openhands.core.tool import ActionBase, ObservationBase


ConversationEventType = Message | ActionBase | ObservationBase
ConversationCallbackReturnType = bool | None  # True means agent should cancel the message/action/observation, false or None means continue (no-op)
ConversationCallbackType = Callable[[ConversationEventType], ConversationCallbackReturnType]
