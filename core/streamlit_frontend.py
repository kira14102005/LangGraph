import streamlit as st
from langchain_core.messages import HumanMessage, AIMessageChunk
from langgraph_backend_sqlite import workflow, fetch_all_thread_ids
from utils.generate_thread_id import generate_thread_id
from utils.reset_chat import reset_chat
from utils.add_thread import add_thread_to_history
from utils.render_threads import render_chat_threads
from utils.load_chat_history import load_chat_history_from_state
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def stream_token_generator(user_input: str, config: dict):
    for chunk, metadata in workflow.stream(
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
                time.sleep(0.05)


if __name__ == "__main__":
    st.set_page_config(page_title="LangGraph Chatbot", page_icon=":robot:")

    stored_threads = fetch_all_thread_ids()
    stored_threads.reverse()

    if 'thread_id' not in st.session_state:
        st.session_state['thread_id'] = generate_thread_id()

    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = stored_threads or []
    
    st.session_state['chat_history'] = load_chat_history_from_state(st.session_state['thread_id'])

    add_thread_to_history(st.session_state['thread_id'])

    st.sidebar.title("LangGraph Chatbot")
    if st.sidebar.button("New Chat"):
        reset_chat()

    st.sidebar.header("Your Chats")
    render_chat_threads()

    CONFIG = {"configurable": {'thread_id': st.session_state['thread_id']}}

    for message in st.session_state['chat_history']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input('Type your message here...')
    if user_input:
        st.session_state['chat_history'].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            ai_response = st.write_stream(stream_token_generator(user_input, CONFIG))

        st.session_state['chat_history'].append({"role": "assistant", "content": ai_response})

        st.rerun()