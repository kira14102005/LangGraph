import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph_backend import workflow

user_input = st.chat_input('Type your message here...')

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

chat_history = st.session_state['chat_history']
thread_id = "user_1"
config = {"configurable": {"thread_id": thread_id}}

for message in chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state['chat_history'].append({"role": "user", "content": user_input})

    ai_response = workflow.invoke({"messages" : [HumanMessage(content=user_input)]}, config=config)['messages'][-1].content

    st.session_state['chat_history'].append({"role": "assistant", "content": ai_response})

    with st.chat_message("assistant"):
        st.markdown(ai_response)