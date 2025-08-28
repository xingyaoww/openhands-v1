import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel


if TYPE_CHECKING:
    from .conversation import Conversation  # noqa

from openhands.core.io import IOProtocol, LocalFS


class PersistenceConfig(BaseModel):
    """
    Plain JSON persistence using ordered object keys, no manifest, no compaction.
    """
    index_width: int = 12
    message_dir_name: str = "messages"
    base_state_name: str = "base_state.json"

class ConversationPersistence:
    """
    Layout under `root/`:
      - base_state.json                     # small JSON
      - messages/<index>-<ts>.jsonl         # one message per file, one JSON object per line

    Conventions:
      - <index> is zero-padded to `cfg.index_width`
      - <ts> is UTC: YYYYMMDDTHHMMSS
    """

    _RE_INDIV = re.compile(
        r"^(?P<idx>\d+)-(?P<ts>\d{8}T\d{6})\.jsonl$"
    )

    def __init__(self, cfg: PersistenceConfig | None = None, io: IOProtocol | None = None) -> None:
        self.cfg = cfg or PersistenceConfig()
        self.io: IOProtocol = io or LocalFS()

    # ---------- Public API ----------

    def save(self, obj: "Conversation", dir_path: str) -> None:
        """
        Persist `obj.state` into `dir_path`:
          - overwrite base_state.json each call (it’s small)
          - enumerate existing message files to see which indices are already saved
          - write new files for missing indices
        """
        base_path = self._join(dir_path, self.cfg.base_state_name)
        msg_dir = self._join(dir_path, self.cfg.message_dir_name)
        self.io.makedirs(msg_dir)

        with obj.state:
            # 1) write base_state (without messages)
            self._write_base_state(base_path, obj)

            # 2) compute which indices are already on disk
            saved_pred = self._build_saved_predicate(msg_dir)

            # 3) write missing messages
            msgs = obj.state.history.messages
            for idx in range(len(msgs)):
                if saved_pred(idx):
                    continue
                self._write_individual(msg_dir, idx, msgs[idx])

    def load(self, cls: "type[Conversation]", agent, dir_path: str, ConversationState, Message, **kwargs) -> "Conversation":
        """
        Restore a Conversation instance from `dir_path`:
          - read base_state.json
          - list and sort individual message files
          - stream JSONL and validate into Message objects
        """
        base_path = self._join(dir_path, self.cfg.base_state_name)
        if not self.io.exists(base_path):
            raise FileNotFoundError(f"Missing {base_path}")

        base_state_dict = json.loads(self.io.read(base_path).decode("utf-8"))

        obj = cls(agent=agent, **kwargs)
        with obj.state:
            obj.state = ConversationState.model_validate(base_state_dict)

            msg_dir = self._join(dir_path, self.cfg.message_dir_name)
            if not self.io.exists(msg_dir):
                return obj

            # collect (idx, path) for individual files
            entries: list[tuple[int, str]] = []
            for p in self.io.list(msg_dir):
                name = os.path.basename(p)
                m = self._RE_INDIV.match(name)
                if m:
                    entries.append((int(m.group("idx")), p))
            entries.sort(key=lambda t: t[0])

            # append messages in order
            for _, path in entries:
                blob = self.io.read(path)
                for line in blob.splitlines():
                    if not line:
                        continue
                    msg_dict = json.loads(line.decode("utf-8"))
                    obj.state.history.messages.append(
                        Message.model_validate(msg_dict)
                    )
        return obj

    # ---------- Internals ----------

    def _write_base_state(self, base_path: str, obj) -> None:
        base = obj.state.model_copy()
        base.history = type(obj.state.history)()  # empty history
        data = json.dumps(base.model_dump(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.io.write(base_path, data)

    def _write_individual(self, msg_dir: str, index: int, msg_model: Any) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        name = f"{index:0{self.cfg.index_width}d}-{ts}.jsonl"
        path = self._join(msg_dir, name)
        line = (json.dumps(msg_model.model_dump(), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        self.io.write(path, line)

    def _build_saved_predicate(self, msg_dir: str):
        saved_indices: set[int] = set()
        for p in self.io.list(msg_dir):
            name = os.path.basename(p)
            m = self._RE_INDIV.match(name)
            if m:
                saved_indices.add(int(m.group("idx")))

        def saved(idx: int) -> bool:
            return idx in saved_indices

        return saved

    @staticmethod
    def _join(prefix: str, *parts: str) -> str:
        return str(Path(prefix).joinpath(*parts))
