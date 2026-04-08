"""LangGraph agent graph for the Cavaleiro Capa Preta ticketing agent."""

from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from react_agent.configuration import Configuration
from react_agent.prompts import SYSTEM_PROMPT
from react_agent.state import InputState, State
from react_agent.tools import tools
from react_agent.utils import load_chat_model

# ---------------------------------------------------------------------------
# Node: greeting_node
# ---------------------------------------------------------------------------

GREETING_MESSAGE = (
    "Olá! Eu sou o Cavaleiro Capa Preta, o guardião do Rio Branco Esporte Clube! ⚔️⚽\n\n"
    "Posso te ajudar com informações sobre o clube, jogadores, jogos, patrocínios e muito mais. "
    "Se você tiver interesse em parceria ou precisar falar com nossa equipe, "
    "é só me dizer — vou registrar seus dados e garantir que te contatemos em breve.\n\n"
    "Como posso te ajudar hoje?"
)


def greeting_node(state: State, config: RunnableConfig) -> dict:
    """Emit a welcome message when the conversation starts with no user input."""
    return {
        "messages": [AIMessage(content=GREETING_MESSAGE)],
        "is_last_step": False,
    }


# ---------------------------------------------------------------------------
# Node: call_model_node
# ---------------------------------------------------------------------------


def call_model_node(state: State, config: RunnableConfig) -> dict:
    """Invoke the LLM with tools bound, using the configurable model string."""
    configuration = Configuration.from_runnable_config(config)

    # Load and bind tools to the configurable model
    model = load_chat_model(configuration.model).bind_tools(tools)

    # Prepend system prompt to the conversation history
    messages = [SystemMessage(content=configuration.system_prompt)] + list(
        state["messages"]
    )

    response = model.invoke(messages)

    # Detect if we've hit the recursion limit to prevent infinite loops
    is_last_step = state.get("is_last_step", False)

    return {
        "messages": [response],
        "is_last_step": is_last_step,
    }


# ---------------------------------------------------------------------------
# Node: tools_node
# ---------------------------------------------------------------------------

tools_node = ToolNode(tools)

# ---------------------------------------------------------------------------
# Routing: route_start
# ---------------------------------------------------------------------------


def route_start(state: State) -> Literal["greeting", "call_model"]:
    """Route to greeting if there are no messages yet, otherwise call the model."""
    messages = state.get("messages", [])
    if not messages:
        return "greeting"
    return "call_model"


# ---------------------------------------------------------------------------
# Routing: route_model_output
# ---------------------------------------------------------------------------


def route_model_output(
    state: State,
) -> Literal["tools", "__end__"]:
    """Route to tools node if the model requested tool calls, otherwise end."""
    last_message = state["messages"][-1]

    # If the LLM forced an end due to recursion limit, stop
    if state.get("is_last_step", False):
        return END

    # If the last message contains tool calls, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END


# ---------------------------------------------------------------------------
# Build the StateGraph
# ---------------------------------------------------------------------------

workflow = StateGraph(State, input=InputState, config_schema=Configuration)

# Register nodes
workflow.add_node("greeting", greeting_node)
workflow.add_node("call_model", call_model_node)
workflow.add_node("tools", tools_node)

# Entry point: smart routing from START
workflow.add_conditional_edges(
    START,
    route_start,
    {"greeting": "greeting", "call_model": "call_model"},
)

# Greeting always ends the turn
workflow.add_edge("greeting", END)

# After call_model: run tools or end
workflow.add_conditional_edges(
    "call_model",
    route_model_output,
    {"tools": "tools", END: END},
)

# After tools, loop back to the model for a follow-up response
workflow.add_edge("tools", "call_model")

# workflow is exported here; it is compiled with the PostgresSaver checkpointer
# inside the FastAPI lifespan in app.py so the connection is managed correctly.
