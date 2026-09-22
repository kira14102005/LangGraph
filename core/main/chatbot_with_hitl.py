from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
#Specialised reducer
from langchain_core.tools import tool
from langgraph.types import Command, interrupt as langgraph_interrupt
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
import requests
import os

from streamlit import json

load_dotenv()

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.5)
llm_2 = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.0)


@tool
def find_stock_price_with_symbol(symbol: str) -> dict:
    """
    Fetches the current stock price for a given stock symbol using the Alpha Vantage API.
    Args:
        symbol (str): The stock symbol to fetch the price for.
    Returns:
        dict: A dictionary containing the stock price information.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    return response.json()

@tool
def find_stock_symbol(keyword: str) -> str:
    """
    Fetches the best matched stock symbol for a given keyword using the Alpha Vantage API.
    Args:
        keyword (str): The keyword to search for a stock symbol.
    Returns:
        str: The best matched stock symbol as a string. If no match is found, returns 'NILL'.
    """
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={keyword}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    prompt_template= PromptTemplate(
        input_variables=["response", "keyword"],
        template="""
        Here is a list of best matches for Stock Symbols for the keyword = {keyword}. 
        Each match is a dictionary with keys: '1. symbol', '2. name', '3. type', '4. region', '5. marketOpen', '6. marketClose', '7. timezone', '8. currency', '9. matchScore'.
        Find the best match for the keyword and return only the stock symbol as a string. If no match is found, return 'NILL'.
        {response}
        """
    )
    chain = prompt_template | llm_2 | StrOutputParser()
    matched_symbol = chain.invoke({"response": response.json(), "keyword": keyword})

    return matched_symbol

@tool
def find_stock_price_with_keyword(keyword: str) -> dict:
    """
    Fetches the current stock price for a given keyword by first finding the best matched stock symbol and then fetching the stock price.
    Args:
        keyword (str): The keyword to search for a stock symbol and fetch the price for.
    Returns:
        dict: A dictionary containing the stock price information. If no matching stock symbol is found, returns an error message.
    """
    symbol = find_stock_symbol.invoke({"keyword": keyword})
    if symbol == "NILL":
        return {"error": "No matching stock symbol found for the given keyword."}
    
    return find_stock_price_with_symbol.invoke({"symbol": symbol})

@tool
def purchase_stock(symbol: str, quantity: int) -> dict:
    """
    Simulates the purchase of a given quantity of stock for a specified stock symbol.
    Args:
        symbol (str): The stock symbol to purchase.
        quantity (int): The quantity of stock to purchase.
    Returns:
        dict: A dictionary containing the purchase confirmation and details.
    """
    # Simulate a stock purchase (in a real application, this would involve API calls to a brokerage)
    decision = langgraph_interrupt(f"Do you want to purchase {quantity} shares of {symbol}? (yes/no)")
    if isinstance(decision, str) and decision.lower() == "yes":
        return {
            "status": "success",
            "message": f"Successfully purchased {quantity} shares of {symbol}.",
            "symbol": symbol,
            "quantity": quantity
        }
    else:
        return {"status": "cancelled", "message": "Purchase cancelled by the user."}

tools = [find_stock_price_with_symbol, find_stock_symbol, find_stock_price_with_keyword, purchase_stock]
llm_with_tools = llm.bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant. Reply briefly when possible."
    ),
    MessagesPlaceholder(variable_name="messages"),
    ])

chain = prompt_template | llm_with_tools 

def chat_with_ai(state: ChatState):
    """
    Handles the chat interaction with the AI model. It takes the current state of the chat, processes the messages, and generates a response using the LLM with tools.
    Args:
        state (ChatState): The current state of the chat containing messages.
    Returns:
        dict: A dictionary containing AI response
    """
    response = chain.invoke({"messages": state["messages"]})
    return {"messages" : [response]}

graph = StateGraph(ChatState)
graph.add_node("chat", chat_with_ai)
tool_node = ToolNode(tools)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")
chatbot = graph.compile(checkpointer=MemorySaver())

if __name__ == "__main__":
    config= {"configurable": {"thread_id": "user_1"}}
    while True:
        input_text = input("You > ")
        end_words = ["exit", "quit", "bye", "0"]
        if input_text.lower() in end_words:
            break
        
        input_state = {"messages": [HumanMessage(content=input_text)]}
        
        output_state = chatbot.invoke(input_state, config=config)
        interrupts = output_state.get("__interrupt__", [])
        if interrupts:
            for langgraph_interrupt_event in interrupts:
                decision = input(f"Interrupt: {langgraph_interrupt_event.value} (yes/no): ")
                decision = decision.strip().lower()
                
                output_state = chatbot.invoke(
                    Command(resume=decision)
                    , config=config
                )
        
        messages = output_state.get("messages", [])
        last_message = messages[-1]
        print(f"AI > {last_message.text}")