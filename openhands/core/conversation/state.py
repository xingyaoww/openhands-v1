from threading import RLock

from pydantic import BaseModel, Field

from openhands.core.context import AgentHistory


# TODO(openhands): we should maybe add some checks to throw errors when user modify this without acquiring lock?
class ConversationState(BaseModel):
    history: AgentHistory = Field(default_factory=AgentHistory)
    _lock: RLock = Field(default_factory=RLock, exclude=True)

    def acquire(self):
        self._lock.acquire()

    def release(self):
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
