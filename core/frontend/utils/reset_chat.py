import streamlit as st
from .generate_thread_id import generate_thread_id
from .add_thread import add_thread_to_history

def reset_chat():
    if not st.session_state['chat_history'] or len(st.session_state['chat_history']) == 0:
        return
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['chat_history'] = []
    add_thread_to_history(st.session_state['thread_id'])