from pathlib import Path

from .typing import IOProtocol


class LocalFS(IOProtocol):
    def read(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def write(self, path: str, data: bytes) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def list(self, prefix: str) -> list[str]:
        p = Path(prefix)
        if not p.exists():
            return []
        return sorted(str(child) for child in p.iterdir() if child.is_file())

    def makedirs(self, path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)

    def exists(self, path: str) -> bool:
        return Path(path).exists()
