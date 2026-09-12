import streamlit as st
user_input = st.chat_input('Type your message here...')

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

chat_history = st.session_state['chat_history']

if user_input:
    st.session_state['chat_history'].append({"role": "user", "content": user_input})

    ai_response = user_input
    st.session_state['chat_history'].append({"role": "assistant", "content": ai_response})

for message in chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])