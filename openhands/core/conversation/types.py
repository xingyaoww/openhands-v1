from typing import Callable

from openhands.core.llm import Message
from openhands.core.tool import ActionBase, ObservationBase


ConversationCallbackType = Callable[[Message | ActionBase | ObservationBase], None]
