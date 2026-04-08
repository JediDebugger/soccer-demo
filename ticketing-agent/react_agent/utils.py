"""Utility functions for the LangGraph agent."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


def load_chat_model(model: str) -> BaseChatModel:
    """Load a chat model from a provider/model-name string.

    Args:
        model: Model identifier in format "provider/model-name"
               e.g., "openai/gpt-4.1-mini", "anthropic/claude-3-opus"

    Returns:
        An initialized BaseChatModel instance
    """
    if "/" in model:
        provider, model_name = model.split("/", 1)
        return init_chat_model(model_name, model_provider=provider)
    return init_chat_model(model)
