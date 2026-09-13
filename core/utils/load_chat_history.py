from langgraph_backend_sqlite import workflow
from langchain_core.messages import HumanMessage, AIMessage

def load_chat_history_from_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = workflow.get_state(config)
    messages = state.values.get("messages", [])
    
    formatted_history = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted_history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted_history.append({"role": "assistant", "content": msg.content})
    return formatted_history