import streamlit as st

def render_chat_threads():
    for thread_id in reversed(st.session_state['chat_threads']):
        st.sidebar.text(thread_id)