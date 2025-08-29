# openhands/core/conversation/state.py
from __future__ import annotations

from threading import RLock, get_ident
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from openhands.core.event import EventType


class ConversationState(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,   # allow RLock in PrivateAttr
        validate_assignment=True,       # validate on attribute set
        frozen=False,
    )

    # Public, validated fields
    events: list[EventType] = Field(default_factory=list)
    agent_finished: bool = False
    initial_message_sent: bool = False

    # Private attrs (NOT Fields) — allowed to start with underscore
    _lock: RLock = PrivateAttr(default_factory=RLock)
    _owner_tid: Optional[int] = PrivateAttr(default=None)

    # Lock/guard API
    def acquire(self) -> None:
        self._lock.acquire()
        self._owner_tid = get_ident()

    def release(self) -> None:
        self._owner_tid = None
        self._lock.release()

    def __enter__(self) -> "ConversationState":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    def assert_locked(self) -> None:
        if self._owner_tid != get_ident():
            raise RuntimeError("State not held by current thread")
