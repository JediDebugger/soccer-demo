"""Configuration management for the LangGraph agent."""

from dataclasses import dataclass
from typing import Annotated, Optional

from langchain_core.runnables import ConfigurableField, RunnableConfig

from react_agent.prompts import SYSTEM_PROMPT


@dataclass
class Configuration:
    """Agent configuration for model selection and system prompt injection."""

    model: Annotated[
        str,
        ConfigurableField(
            id="model",
            name="Model",
            description="The language model to use for the agent",
        ),
    ] = "openai/gpt-4.1-mini"

    system_prompt: str = SYSTEM_PROMPT

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Extract configuration values from RunnableConfig.

        Args:
            config: Optional RunnableConfig containing configurable field values

        Returns:
            Configuration instance with values from config or defaults
        """
        configurable = config.get("configurable", {}) if config else {}
        return cls(
            model=configurable.get("model", "openai/gpt-4.1-mini"),
            system_prompt=configurable.get("system_prompt", SYSTEM_PROMPT),
        )
