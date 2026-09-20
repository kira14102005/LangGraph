import streamlit as st
from .load_chat_history import load_chat_history

async def render_chat_threads(workflow):
    for thread_id in reversed(st.session_state['chat_threads']):
        if st.sidebar.button(thread_id):
            await click_thread(workflow, thread_id)

async def click_thread(workflow, thread_id):
    st.session_state['thread_id'] = thread_id
    updated_chat_history = await load_chat_history(workflow, thread_id)
    st.session_state['chat_history'] = updated_chat_history