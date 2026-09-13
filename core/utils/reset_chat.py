import streamlit as st
from .generate_thread_id import generate_thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['chat_history'] = []