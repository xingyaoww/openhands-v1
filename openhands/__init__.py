"""OpenHands package."""

import os
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version

__package_name__ = "openhands-ai"


def get_version():
    # Try getting the version from pyproject.toml
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate_paths = [
            Path(root_dir) / "pyproject.toml",
            Path(root_dir) / "openhands" / "pyproject.toml",
        ]
        for file_path in candidate_paths:
            if file_path.is_file():
                with open(file_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("version ="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass

    try:
        return version(__package_name__)
    except (ImportError, PackageNotFoundError):
        pass
    return "unknown"


try:
    __version__ = get_version()
except Exception:
    __version__ = "unknown"
