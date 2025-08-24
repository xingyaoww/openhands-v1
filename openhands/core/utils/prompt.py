import os
import re
import sys

from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader, Template

from openhands.core.microagents import MicroagentKnowledge


class RuntimeInfo(BaseModel):
    date: str = Field(description="Current date in YYYY-MM-DD format")
    available_hosts: dict[str, int] = Field(
        default_factory=dict, description="Available hosts for agents to deploy to"
    )
    additional_agent_instructions: str = Field(
        default="",
        description="Additional instructions for the agent to follow during the conversation",
    )
    custom_secrets_descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="Descriptions of custom secrets available to the agent",
    )
    working_dir: str = Field(
        default="", description="Current working directory of the agent"
    )


class RepositoryInfo(BaseModel):
    """Information about a GitHub repository that has been cloned."""

    repo_name: str | None = Field(
        None, description="Name of the repository, e.g., 'username/repo'"
    )
    repo_directory: str | None = Field(
        None, description="Local directory path where the repository is cloned"
    )
    branch_name: str | None = Field(
        None, description="Current branch name of the repository"
    )


class ConversationInstructions(BaseModel):
    """Optional instructions the agent must follow throughout the conversation while addressing the user's initial task

    Examples include

        1. Resolver instructions: you're responding to GitHub issue #1234, make sure to open a PR when you are done
        2. Slack instructions: make sure to check whether any of the context attached is relevant to the task <context_messages>
    """

    content: str = Field(
        default="",
        description="Instructions for the agent to follow during the conversation",
    )


def refine_prompt(prompt: str):
    """Refines the prompt based on the platform.

    On Windows systems, replaces 'bash' with 'powershell' and 'execute_bash' with 'execute_powershell'
    to ensure commands work correctly on the Windows platform.

    Args:
        prompt: The prompt text to refine

    Returns:
        The refined prompt text
    """
    if sys.platform == "win32":
        # Replace 'bash' with 'powershell' including tool names like 'execute_bash'
        # First replace 'execute_bash' with 'execute_powershell' to handle tool names
        result = re.sub(
            r"\bexecute_bash\b", "execute_powershell", prompt, flags=re.IGNORECASE
        )
        # Then replace standalone 'bash' with 'powershell'
        result = re.sub(
            r"(?<!execute_)(?<!_)\bbash\b", "powershell", result, flags=re.IGNORECASE
        )
        return result
    return prompt


class PromptManager:
    """Manages prompt templates and includes information from the user's workspace micro-agents and global micro-agents.

    This class is dedicated to loading and rendering prompts (system prompt, user prompt).

    Attributes:
        prompt_dir: Directory containing prompt templates.
    """

    def __init__(
        self,
        prompt_dir: str,
        system_prompt_filename: str = "system_prompt.j2",
    ):
        if prompt_dir is None:
            raise ValueError("Prompt directory is not set")

        self.prompt_dir: str = prompt_dir
        self.env = Environment(loader=FileSystemLoader(prompt_dir))
        self.system_template: Template = self._load_template(system_prompt_filename)
        self.user_template: Template = self._load_template("user_prompt.j2")
        self.additional_info_template: Template = self._load_template(
            "additional_info.j2"
        )
        self.microagent_info_template: Template = self._load_template(
            "microagent_info.j2"
        )

    def _load_template(self, template_name: str) -> Template:
        """Load a template from the prompt directory.

        Args:
            template_name: Full filename of the template to load, including the .j2 extension.

        Returns:
            The loaded Jinja2 template.

        Raises:
            FileNotFoundError: If the template file is not found.
        """
        try:
            return self.env.get_template(template_name)
        except Exception:
            template_path = os.path.join(self.prompt_dir, template_name)
            raise FileNotFoundError(f"Prompt file {template_path} not found")

    def get_system_message(self, **context) -> str:
        system_message = self.system_template.render(**context).strip()
        return refine_prompt(system_message)

    def build_workspace_context(
        self,
        repository_info: RepositoryInfo | None,
        runtime_info: RuntimeInfo | None,
        conversation_instructions: ConversationInstructions | None,
        repo_instructions: str = "",
    ) -> str:
        """Renders the additional info template with the stored repository/runtime info."""
        return self.additional_info_template.render(
            repository_info=repository_info,
            repository_instructions=repo_instructions,
            runtime_info=runtime_info,
            conversation_instructions=conversation_instructions,
        ).strip()

    def build_microagent_info(
        self,
        triggered_agents: list[MicroagentKnowledge],
    ) -> str:
        """Renders the microagent info template with the triggered agents.

        Args:
            triggered_agents: A list of MicroagentKnowledge objects containing information
                              about triggered microagents.
        """
        return self.microagent_info_template.render(
            triggered_agents=triggered_agents
        ).strip()
