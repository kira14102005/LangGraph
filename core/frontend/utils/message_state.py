from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages

class SimpleMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str