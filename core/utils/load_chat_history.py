from langchain_core.messages import HumanMessage, AIMessage

async def load_chat_history(workflow, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = await workflow.aget_state(config)
    messages = state.values.get("messages", [])
    formatted_history = []
    for msg in messages:
        if not msg.content:
            continue
        elif isinstance(msg, HumanMessage):
            formatted_history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted_history.append({"role": "assistant", "content": msg.content[0]['text'] if isinstance(msg.content, list) and msg.content and isinstance(msg.content[0], dict) and 'text' in msg.content[0] else msg.content})
    return formatted_history