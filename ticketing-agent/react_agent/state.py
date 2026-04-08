"""State management for the LangGraph agent."""

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class InputState(TypedDict):
    """Input state for handling incoming messages."""

    messages: Annotated[Sequence[AnyMessage], add_messages]


class State(TypedDict):
    """Full agent state for conversation management."""

    messages: Annotated[Sequence[AnyMessage], add_messages]
    is_last_step: bool
