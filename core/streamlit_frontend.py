import streamlit as st
from langchain_core.messages import HumanMessage, AIMessageChunk
from langchain_core.output_parsers import StrOutputParser
from langgraph_backend import workflow
from utils.generate_thread_id import generate_thread_id
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def stream_token_generator():
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

    user_input = st.chat_input('Type your message here...')

    st.sidebar.title("LangGraph Chatbot")
    st.sidebar.button("New Chat")
    st.sidebar.header("Your Chats")

    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    if 'thread_id' not in st.session_state:
        st.session_state['thread_id'] = generate_thread_id()

    chat_history = st.session_state['chat_history']
    thread_id = "user_1"
    config = {"configurable": {"thread_id": thread_id}}
    
    for message in chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    if user_input:
        st.session_state['chat_history'].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
                st.markdown(user_input)

        with st.chat_message("assistant"):
            ai_response = st.write_stream(stream_token_generator())
        
        st.session_state['chat_history'].append({"role": "assistant", "content": ai_response})
        