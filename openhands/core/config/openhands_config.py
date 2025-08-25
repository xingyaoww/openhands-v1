from pydantic import BaseModel, ConfigDict, Field

from openhands.core.config.llm_config import LLMConfig

from openhands.core.logger import get_logger

logger = get_logger(__name__)

OH_DEFAULT_AGENT = "CodeActAgent"
OH_MAX_ITERATIONS = 500


class OpenHandsConfig(BaseModel):
    """Configuration for the app."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    secondary_llm: LLMConfig | None = Field(
        default=None,
        description="Secondary LLM config, used for tasks like summarization or verification.",
    )
    workspace_base: str | None = Field(
        default="./workspace",
        description="Path to launch the agent workspace from. Relative paths are relative to the current working directory.",
    )
    max_iterations: int = Field(
        default=OH_MAX_ITERATIONS,
        description="Maximum number of iterations the agent can perform.",
    )
    model_config = ConfigDict(extra="forbid")
