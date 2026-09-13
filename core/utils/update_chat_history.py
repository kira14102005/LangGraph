from langgraph_backend import workflow
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


def update_chat_history(thread_id):
    chat_history = []
    config = {"configurable" : {"thread_id" : thread_id}}
    state_snapshot = workflow.get_state(config)
    updated_chat_history = state_snapshot.values or {}
    for message in updated_chat_history.get('messages', []):
        if type(message) == HumanMessage:
            role = 'user'
        elif type(message) == AIMessage:
            role= 'assistant'
        else:
            role = 'system'

        chat_history.append({'role' : role, 'content' : message.content})

    return chat_history