import openhands
import os


def get_llm_metadata(
    model_name: str,
    agent_name: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict:
    metadata = {
        "trace_version": openhands.__version__,
        "tags": [
            f"model:{model_name}",
            f"agent:{agent_name}",
            f"web_host:{os.environ.get('WEB_HOST', 'unspecified')}",
            f"openhands_version:{openhands.__version__}",
        ],
    }
    if session_id is not None:
        metadata["session_id"] = session_id
    if user_id is not None:
        metadata["trace_user_id"] = user_id
    return metadata
