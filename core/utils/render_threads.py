import streamlit as st
from langgraph_backend import workflow
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def render_chat_threads():
    for thread_id in reversed(st.session_state['chat_threads']):
        if st.sidebar.button(thread_id):
            st.session_state['thread_id'] = thread_id
            config = {"configurable" : {"thread_id" : thread_id}}
            chat_history = []
            state_snapshot = workflow.get_state(config).values
            # print(state_snapshot)
            for message in state_snapshot['messages']:
                if type(message) == HumanMessage:
                    role = 'user'
                elif type(message) == AIMessage:
                    role= 'assistant'
                else:
                    role = 'system'

                chat_history.append({'role' : role, 'content' : message.content})

            st.session_state['chat_history']  = chat_history