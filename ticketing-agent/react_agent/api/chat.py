"""Chat API router — POST /agent/chat."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming chat request payload."""

    session_id: str
    message: str  # the user's input as a plain string


class ChatResponse(BaseModel):
    """Outgoing chat response payload."""

    session_id: str
    messages: list[dict[str, Any]]  # full message history serialised to dicts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialise_messages(messages) -> list[dict[str, Any]]:
    """Serialise a list of LangChain messages to plain dicts for the API response."""
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            entry: dict[str, Any] = {"role": "ai", "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            result.append(entry)
        elif isinstance(msg, ToolMessage):
            result.append(
                {
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                }
            )
        else:
            # Generic fallback
            result.append(
                {
                    "role": getattr(msg, "type", "unknown"),
                    "content": getattr(msg, "content", str(msg)),
                }
            )
    return result


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """Invoke the LangGraph agent and return the full updated message history.

    The `session_id` is used as the `thread_id` for the PostgreSQL checkpointer,
    so each session maintains its own persistent conversation history.
    The compiled graph is retrieved from `req.app.state.graph`, which is set up
    in the FastAPI lifespan with a real PostgresSaver instance.
    """
    try:
        # Retrieve the compiled graph from app state (set during lifespan startup)
        graph = req.app.state.graph

        # Wrap the user's plain-string message in a HumanMessage
        lc_messages = [HumanMessage(content=request.message)]

        # Build LangGraph config with thread_id for checkpointing
        config = {"configurable": {"thread_id": request.session_id}}

        logger.info(
            "Invoking graph for session=%s | message: %.80s",
            request.session_id,
            request.message,
        )

        # Invoke the compiled graph
        result = graph.invoke({"messages": lc_messages}, config=config)

        # Serialise all messages from the graph output
        serialised = _serialise_messages(result.get("messages", []))

        logger.info(
            "Graph returned %d message(s) for session=%s",
            len(serialised),
            request.session_id,
        )

        return ChatResponse(session_id=request.session_id, messages=serialised)

    except Exception as e:
        logger.error("Error invoking agent for session=%s: %s", request.session_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}",
        )
