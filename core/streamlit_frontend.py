import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph_backend import workflow
import time

def stream_token_generator():
    for chunk, metadata in workflow.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="messages",
    ):
        text = chunk.text

        if text:
            for word in text.split(" "):
                yield word + " "
                time.sleep(0.05)


if __name__ == "__main__":
    st.set_page_config(page_title="LangGraph Chatbot", page_icon=":robot:")
    st.title("LangGraph Chatbot")

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
        st.session_state['chat_history'].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
                st.markdown(user_input)

        with st.chat_message("assistant"):
            ai_response = st.write_stream(stream_token_generator())
        
        st.session_state['chat_history'].append({"role": "assistant", "content": ai_response})
        