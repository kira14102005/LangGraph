import asyncio

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessageChunk
from async_langgraph_chatbot import build_workflow, fetch_all_thread_ids
from utils.generate_thread_id import generate_thread_id
from utils.reset_chat import reset_chat
from utils.add_thread import add_thread_to_history
from utils.render_threads import render_chat_threads
from utils.load_chat_history import load_chat_history
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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

@st.cache_resource
def get_workflow():
    """
    Create the LangGraph workflow and DB connection only once.
    Streamlit reruns will reuse these resources.
    """
    return asyncio.run(build_workflow())

async def app():
    workflow, conn = get_workflow()
    
    stored_threads = await fetch_all_thread_ids(conn)
    stored_threads.reverse()

    st.set_page_config(page_title="LangGraph Chatbot", page_icon=":robot:")
    if 'thread_id' not in st.session_state:
            st.session_state['thread_id'] = generate_thread_id()
    
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = stored_threads or []
    
    st.session_state['chat_history'] = await load_chat_history(workflow, st.session_state['thread_id'])

    add_thread_to_history(st.session_state['thread_id'])

    st.sidebar.title("LangGraph Chatbot")
    if st.sidebar.button("New Chat"):
        reset_chat()

    st.sidebar.header("Your Chats")
    await render_chat_threads(workflow=workflow)

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
            ai_response = st.write_stream(stream_token_generator(workflow, user_input, CONFIG))
        st.session_state['chat_history'].append({"role": "assistant", "content": ai_response})

        st.rerun()

if __name__ == "__main__":
    asyncio.run(app())   