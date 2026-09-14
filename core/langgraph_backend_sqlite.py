from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
#Specialised reducer
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
import sqlite3
import os

os.environ['LANGSMITH_PROJECT'] = "streamlit-chatbot"

load_dotenv()

#tools
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(a:float, b:float, operation:str) -> float:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b
    else:
        raise ValueError(f"Unsupported operation: {operation}")

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

# LANGSMITH_TRACE_URL = https://eu.smith.langchain.com/public/f3cce930-f134-48bb-b5a5-bf6c3cd37430/r/01a0a0a7-0886-7023-b342-9f6f6a1576f0?start_time=2026-09-14T16%3A01%3A36.390092Z
