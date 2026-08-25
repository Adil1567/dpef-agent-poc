from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

from research_chat_agent.llm import get_chat_model
from research_chat_agent.tools import web_research

TOOLS = [web_research]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _router_node(state: AgentState) -> dict:
    # Tools stay bound on every call through this node - including after a
    # research round trip - so the model can either produce a final answer
    # or ask for another tool call. Some providers error if a tool result is
    # in the conversation but no tools are declared on the next call.
    llm = get_chat_model().bind_tools(TOOLS)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def _should_call_tool(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "research"
    return "end"


def build_graph():
    """Build the research-chat-agent graph.

    router -> (direct end) or (research tool -> router again -> ... -> end)
    """
    graph = StateGraph(AgentState)

    graph.add_node("router", _router_node)
    graph.add_node("research", ToolNode(TOOLS))

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router", _should_call_tool, {"research": "research", "end": END}
    )
    graph.add_edge("research", "router")

    return graph.compile()
