import streamlit as st

def add_thread_to_history(t_id):
    if t_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(t_id)