from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
#Specialised reducer
from langgraph.graph.message import add_messages

load_dotenv()

from typing import Literal, TypedDict, Optional, Annotated

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

graph = StateGraph(ChatState)
checkpointer = MemorySaver()
graph.add_node('chat_node' , chat_with_ai)

#add_edges
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)
workflow = graph.compile(checkpointer=checkpointer)