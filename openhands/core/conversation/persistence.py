import gzip
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import zstandard as zstd


if TYPE_CHECKING:
    from .conversation import Conversation

@dataclass
class PersistenceConfig:
    """
    Tunables for conversation persistence.

    shard_size: logical target messages per "part" file (used for naming & rotation)
    part_target_bytes: soft target size for compacted part files (informative only here)
    delta_compact_threshold_msgs / _bytes: when exceeded, we compact trailing 1-msg "delta" files
    codec: 'zstd' | 'gzip' | 'none' (zstd preferred; falls back to gzip if zstd unavailable)
    codec_level: compression level (zstd 1–19; gzip 1–9)
    schema_version: manifest/base_state schema version
    """
    shard_size: int = 500
    part_target_bytes: int = 4 * 1024 * 1024
    delta_compact_threshold_msgs: int = 128
    delta_compact_threshold_bytes: int = 2 * 1024 * 1024
    # codec: str = "zstd"
    codec: str = "none"
    codec_level: int = 3
    schema_version: int = 1


class _Codec:
    def __init__(self, name: str, level: int):
        name = name.lower()
        if name not in {"zstd", "gzip", "none"}:
            raise ValueError("codec must be 'zstd' | 'gzip' | 'none'")
        self.name = name
        self.level = int(level)

    def ext(self) -> str:
        return "zst" if self.name == "zstd" else ("gz" if self.name == "gzip" else "json")

    def compress(self, data: bytes) -> bytes:
        if self.name == "none":
            return data
        if self.name == "gzip":
            out = io.BytesIO()
            with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=max(1, min(9, self.level))) as f:
                f.write(data)
            return out.getvalue()
        cctx = zstd.ZstdCompressor(level=max(1, min(19, self.level)))  # type: ignore[name-defined]
        return cctx.compress(data)

    def decompress(self, data: bytes) -> bytes:
        if self.name == "none":
            return data
        if self.name == "gzip":
            with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as f:
                return f.read()
        dctx = zstd.ZstdDecompressor()  # type: ignore[name-defined]
        return dctx.decompress(data)


class ConversationPersistence:
    """
    Cloud-friendly persistence for Conversation.

    Design (simple & durable):
      - `base_state.json.<ext>`: ConversationState minus history.messages (small)
      - `messages/*.delta-*.ext`: one message per delta (written immediately after each msg)
      - Optional compaction: merge trailing deltas → `messages/<shard>.part-XXX.<ext>`
      - `manifest.json`: authoritative ordered list of segments

    GCS/S3 safe: we never append to an existing object; we write new objects and then
    rewrite the tiny `manifest.json`. If a crash happens, extra objects not in the manifest
    are harmless and will be picked up next save.

    Requirements on host Conversation:
      - `obj.state` is identity-stable and is a context manager guarding its own lock:
            with obj.state:  # exclusive access
                ...
      - `obj.state.history.messages` is a list of Pydantic `Message` models
      - Importers supply the `Message` and `ConversationState` models to this module
        via the call sites below.
    """

    _MANIFEST = "manifest.json"
    _BASE_STATE = "base_state.json"
    _MSG_DIR = "messages"

    def __init__(self, cfg: PersistenceConfig | None = None) -> None:
        self.cfg = cfg or PersistenceConfig()

    # ---------- Public API ----------

    def save(self, obj, dir_path: str | Path) -> None:
        """
        Persist `obj.state` to `dir_path`.

        - Writes fresh base_state (small) every time.
        - Appends 1-message delta files for any unsaved messages.
        - If thresholds exceeded, compacts trailing deltas into a part file.
        """
        codec = _Codec(self.cfg.codec, self.cfg.codec_level)
        root = Path(dir_path)
        (root / self._MSG_DIR).mkdir(parents=True, exist_ok=True)

        with obj.state:  # state owns the lock
            manifest = self._load_or_init_manifest(root)
            self._write_base_state(root, codec, obj)

            last_idx = int(manifest.get("last_saved_index", -1))
            msgs = obj.state.history.messages
            if len(msgs) - 1 > last_idx:
                start = last_idx + 1
                for i in range(start, len(msgs)):
                    entry = self._write_delta(root, msgs[i], codec, i)
                    manifest["parts"].append(entry)
                manifest["last_saved_index"] = len(msgs) - 1

            if self._should_compact(manifest):
                self._run_compaction(root, manifest, codec)

            self._write_manifest(root, manifest)

    def load(self, cls, agent, dir_path: str | Path, ConversationState, Message, **kwargs) -> "Conversation":
        """
        Restore a Conversation instance from `dir_path`.

        Parameters
        ----------
        cls : type
            The Conversation class (must accept `agent` in its constructor).
        agent : Any
            Agent instance to pass into the Conversation constructor.
        dir_path : str | Path
            Where the conversation was persisted.
        ConversationState : Type
            Pydantic model class to validate the base state dict.
        Message : Type
            Pydantic model class to validate each message.

        Returns
        -------
        obj : cls
            A constructed Conversation with `state` rebuilt.
        """
        root = Path(dir_path)
        mpath = root / self._MANIFEST
        if not mpath.exists():
            raise FileNotFoundError(f"Missing manifest at {mpath}")

        manifest = json.loads(mpath.read_text("utf-8"))
        # Allow manifest to override codec at read time
        rd_codec = _Codec(
            manifest.get("codec", self.cfg.codec),
            int(manifest.get("codec_level", self.cfg.codec_level)),
        )

        base_state_dict = self._read_base_state(root, rd_codec)

        obj = cls(agent=agent)
        with obj.state:
            obj.state = ConversationState.model_validate(base_state_dict)
            for e in manifest.get("parts", []):
                p = root / e["name"]
                if not p.exists():
                    continue
                payload = rd_codec.decompress(p.read_bytes())
                for line in payload.splitlines():
                    if not line:
                        continue
                    obj.state.history.messages.append(
                        Message.model_validate(json.loads(line))
                    )
        return obj

    def compact_now(self, dir_path: str | Path) -> None:
        """
        Force a compaction pass (merge trailing deltas into one part).
        Safe to call repeatedly; no-op if nothing to compact.
        """
        codec = _Codec(self.cfg.codec, self.cfg.codec_level)
        root = Path(dir_path)
        manifest = self._load_or_init_manifest(root)
        if self._run_compaction(root, manifest, codec):
            self._write_manifest(root, manifest)

    # ---------- Internals (small & boring) ----------

    def _load_or_init_manifest(self, root: Path) -> dict[str, Any]:
        mpath = root / self._MANIFEST
        if mpath.exists():
            m = json.loads(mpath.read_text("utf-8"))
            ver = int(m.get("schema_version", 0))
            if ver != self.cfg.schema_version:
                raise RuntimeError(f"Unsupported manifest schema {ver}, expected {self.cfg.schema_version}")
            return m
        m = {
            "schema_version": self.cfg.schema_version,
            "shard_size": self.cfg.shard_size,
            "codec": self.cfg.codec,
            "codec_level": self.cfg.codec_level,
            "parts": [],
            "last_saved_index": -1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write_manifest(root, m)
        return m

    def _write_manifest(self, root: Path, manifest: dict[str, Any]) -> None:
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        mpath = root / self._MANIFEST
        tmp = mpath.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), "utf-8")
        tmp.replace(mpath)

    def _write_base_state(self, root: Path, codec: _Codec, obj) -> None:
        base = obj.state.model_copy()
        base.history = type(obj.state.history)()  # empty history
        data = json.dumps(base.model_dump(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        path = root / f"{self._BASE_STATE}.{codec.ext()}"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(codec.compress(data))
        tmp.replace(path)

    def _read_base_state(self, root: Path, codec: _Codec) -> dict[str, Any]:
        candidates = [
            f"{self._BASE_STATE}.{codec.ext()}",
            f"{self._BASE_STATE}.zst",
            f"{self._BASE_STATE}.gz",
            f"{self._BASE_STATE}",
        ]
        for fname in candidates:
            p = root / fname
            if not p.exists():
                continue
            blob = p.read_bytes()
            if fname.endswith(".json"):
                return json.loads(blob.decode("utf-8"))
            dec = (_Codec("zstd", 3) if fname.endswith(".zst") else _Codec("gzip", 6)).decompress(blob) \
                  if not fname.endswith(".json") else blob
            return json.loads(dec.decode("utf-8"))
        raise FileNotFoundError("base_state not found in any supported format")

    def _write_delta(self, root: Path, msg, codec: _Codec, index: int) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        name = f"{index:06d}.delta-{ts}.{codec.ext()}"
        path = (root / self._MSG_DIR) / name
        ndjson = (json.dumps(msg.model_dump(), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        path.write_bytes(codec.compress(ndjson))
        return {"kind": "delta", "name": str(path.relative_to(root)), "count": 1, "bytes": path.stat().st_size}

    def _should_compact(self, manifest: dict[str, Any]) -> bool:
        parts = manifest.get("parts", [])
        n = 0
        b = 0
        for e in reversed(parts):
            if e.get("kind") != "delta":
                break
            n += 1
            b += int(e.get("bytes", 0))
        return (n >= self.cfg.delta_compact_threshold_msgs) or (b >= self.cfg.delta_compact_threshold_bytes)

    def _run_compaction(self, root: Path, manifest: dict[str, Any], codec: _Codec) -> bool:
        parts = manifest.get("parts", [])
        # gather trailing deltas
        tail: list[dict[str, Any]] = []
        for e in reversed(parts):
            if e.get("kind") == "delta":
                tail.append(e)
            else:
                break
        if not tail:
            return False
        tail.reverse()

        buf = io.BytesIO()
        for e in tail:
            p = root / e["name"]
            if not p.exists():
                continue
            buf.write(codec.decompress(p.read_bytes()))
        payload = buf.getvalue()
        if not payload:
            return False

        # naming: shard by last_saved_index // shard_size
        last = int(manifest.get("last_saved_index", -1))
        shard_index = (last // max(1, self.cfg.shard_size)) if last >= 0 else 0
        part_suffix = sum(1 for e in parts if e.get("kind") == "part" and f"{shard_index:06d}.part-" in e.get("name", ""))
        part_name = f"{shard_index:06d}.part-{part_suffix:03d}.{codec.ext()}"
        part_path = (root / self._MSG_DIR) / part_name
        part_path.write_bytes(codec.compress(payload))

        split_idx = len(parts) - len(tail)
        manifest["parts"] = parts[:split_idx] + [{
            "kind": "part",
            "name": str(part_path.relative_to(root)),
            "count": sum(int(e.get("count", 1)) for e in tail),
            "bytes": part_path.stat().st_size,
        }]

        # best effort cleanup
        for e in tail:
            try:
                (root / e["name"]).unlink(missing_ok=True)
            except Exception:
                pass
        return True
