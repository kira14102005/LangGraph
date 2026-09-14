from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
#Specialised reducer
from langgraph.graph.message import add_messages
import sqlite3

load_dotenv()

from typing import TypedDict, Annotated

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.5)

def chat_with_ai(state: ChatState):
    messages = state['messages']
    prompt_template = PromptTemplate(
        input_variables=["messages"],
        template="You are a helpful assistant. Continue the conversation based on the following messages. Reply in short-oneline if possi:\n\n{messages}"
    )
    chain = prompt_template | llm | StrOutputParser()
    response = chain.invoke({"messages" : messages})
    return  {"messages": [AIMessage(content=response)]}

conn = sqlite3.connect("chat_bot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn = conn)

graph = StateGraph(ChatState)
graph.add_node('chat_node' , chat_with_ai)

#add_edges
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)
workflow = graph.compile(checkpointer=checkpointer)

def fetch_all_thread_ids() -> list[str]:
    cursor = conn.cursor()
    # Check if table exists yet
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'")
    if not cursor.fetchone():
        return []
    
    # Query distinct threads ordered by latest activity
    cursor.execute("""
        SELECT DISTINCT thread_id 
        FROM checkpoints 
        ORDER BY checkpoint_id DESC
    """)
    rows = cursor.fetchall()
    return [row[0] for row in rows]

def fetch_all_thread_ids_with_checkpointer() -> list[str]:
    #since using set order is not guaranteed
    all_thread_set = set()
    for checkpoint in checkpointer.list(None):
        all_thread_set.add(checkpoint.config['configurable']['thread_id'] if 'configurable' in checkpoint.config and 'thread_id' in checkpoint.config['configurable'] else None)
    return list(str(thread_id) for thread_id in all_thread_set)