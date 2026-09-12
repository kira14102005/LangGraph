import streamlit as st

user_input = st.chat_input('Type your message here...')

message_history = []

if user_input:
    message_history.append({"role": "user", "content": user_input})

    ai_response = user_input
    message_history.append({"role": "assistant", "content": ai_response})

for message in message_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])