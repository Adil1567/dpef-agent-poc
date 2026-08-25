import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage

from research_chat_agent.config import ConfigError
from research_chat_agent.graph import build_graph

_graph = build_graph()


def respond(message: str, history: list, session_messages: list):
    session_messages = list(session_messages or [])
    session_messages.append(HumanMessage(content=message))

    try:
        result = _graph.invoke({"messages": session_messages})
    except ConfigError as exc:
        error_text = f"Configuration error: {exc}"
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": error_text},
        ]
        return history, session_messages, ""
    except Exception as exc:
        error_text = (
            "Sorry, something went wrong while talking to the LLM provider "
            f"({exc}). This may be a rate limit or a temporary API issue."
        )
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": error_text},
        ]
        return history, session_messages, ""

    session_messages = result["messages"]
    last_message = session_messages[-1]
    reply = last_message.content if isinstance(last_message, AIMessage) else str(
        last_message.content
    )

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return history, session_messages, ""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Research Chat Agent") as demo:
        gr.Markdown("# Research Chat Agent\nAsk anything. The agent decides on its own whether to search the web.")
        chatbot = gr.Chatbot(label="Conversation")
        session_state = gr.State([])
        msg_box = gr.Textbox(label="Message", placeholder="Type your message and press Enter...")

        msg_box.submit(
            respond,
            inputs=[msg_box, chatbot, session_state],
            outputs=[chatbot, session_state, msg_box],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch()
