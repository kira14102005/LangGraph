import asyncio
import logging

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessageChunk

from async_langgraph_chatbot import build_workflow, fetch_all_thread_ids
from utils.generate_thread_id import generate_thread_id
from utils.reset_chat import reset_chat
from utils.add_thread import add_thread_to_history
from utils.render_threads import render_chat_threads
from utils.load_chat_history import load_chat_history


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

@st.cache_resource
def get_workflow():
    return asyncio.run(build_workflow())

async def stream_token_generator(workflow, user_input: str, config: dict):
    async for chunk, metadata in workflow.astream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="messages",
    ):
        logger.info(
            "NODE = %s | TYPE = %s | TEXT = %r",
            metadata.get("langgraph_node"),
            type(chunk).__name__,
            chunk.text,
        )

        text = chunk.text

        if text and isinstance(chunk, AIMessageChunk):
            for word in text.split(" "):
                yield word + " "
                await asyncio.sleep(0.05)

# TOOLMESSAGE : 2026-09-14 23:08:11,145 - __main__ - INFO - NODE = tools | TYPE = ToolMessage | TEXT = '{"Global Quote": {"01. symbol": "AXP", "02. open": "324.9700", "03. high": "326.2600", "04. low": "322.2100", "05. price": "324.6900", "06. volume": "1930287", "07. latest trading day": "2026-09-11", "08. previous close": "320.7100", "09. change": "3.9800", "10. change percent": "1.2410%"}}'

def run_async(coro):
    return asyncio.run(coro)


def app():

    # Streamlit config should be set before other Streamlit commands
    st.set_page_config(
        page_title="LangGraph Chatbot",
        page_icon=":robot:"
    )

    # --------------------------------------------------
    # Build workflow
    # --------------------------------------------------

    workflow, conn = get_workflow()
    # --------------------------------------------------
    # Session state
    # --------------------------------------------------

    if "thread_id" not in st.session_state:
        st.session_state["thread_id"] = generate_thread_id()

    if "chat_threads" not in st.session_state:
        stored_threads = run_async(
            fetch_all_thread_ids(conn)
        ) or []

        stored_threads.reverse()
        st.session_state["chat_threads"] = stored_threads

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = run_async(load_chat_history(workflow,st.session_state["thread_id"]))

    add_thread_to_history(st.session_state["thread_id"])

    # --------------------------------------------------
    # Sidebar
    # --------------------------------------------------

    st.sidebar.title("LangGraph Chatbot")

    if st.sidebar.button("New Chat"):
        reset_chat()
        st.rerun()

    st.sidebar.header("Your Chats")

    run_async(render_chat_threads(workflow=workflow))

    # --------------------------------------------------
    # Config
    # --------------------------------------------------

    CONFIG = {
        "configurable": {
            "thread_id": st.session_state["thread_id"]
        }
    }

    # --------------------------------------------------
    # Existing chat history
    # --------------------------------------------------

    for message in st.session_state["chat_history"]:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --------------------------------------------------
    # Chat input
    # --------------------------------------------------

    user_input = st.chat_input(
        "Type your message here..."
    )

    if user_input:

        st.session_state["chat_history"].append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            # Don't call asyncio.run() here.
            # Streamlit's write_stream handles the async generator.
            ai_response = st.write_stream(
                stream_token_generator(
                    workflow,
                    user_input,
                    CONFIG
                )
            )

        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": ai_response
        })


if __name__ == "__main__":
    app()