import streamlit as st
from .update_chat_history import update_chat_history

def render_chat_threads():
    for thread_id in reversed(st.session_state['chat_threads']):
        if st.sidebar.button(thread_id):
            click_thread(thread_id)

def click_thread(thread_id):
    st.session_state['thread_id'] = thread_id
    updated_chat_history = update_chat_history(thread_id)
    st.session_state['chat_history'] = updated_chat_history