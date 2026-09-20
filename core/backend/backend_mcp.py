from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
#Specialised reducer
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
from langchain_mcp_adapters.client import MultiServerMCPClient
import requests
import os
import aiosqlite

os.environ['LANGSMITH_PROJECT'] = "streamlit-chatbot-mcp"
load_dotenv()

REMOTE_MCP_SERVER_URL = os.getenv("REMOTE_MCP_SERVER_URL")
FMCP_ACCESS_KEY = os.getenv("FMCP_ACCESS_KEY")

servers = {
    "remote_expense_server": {
        "transport": "http",
        "url": REMOTE_MCP_SERVER_URL,
        "headers": {
            "Authorization": f"Bearer {FMCP_ACCESS_KEY}"
        }
    },
}

client = MultiServerMCPClient(servers)

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.5)
llm_2 = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.0)
#tools
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(a:float, b:float, operation:str) -> float:
    """
    Performs a calculation on two numbers.
       Args:
           a (float): The first number.
           b (float): The second number.
           operation (str): The operation to perform. Can be 'add', 'subtract', 'multiply', or 'divide'.
       Returns:
           float: The result of the calculation.
    """
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

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

tools = [search_tool, calculator, find_stock_price_with_keyword, find_stock_symbol, find_stock_price_with_symbol]


    
prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant. Reply briefly when possible."
    ),
    MessagesPlaceholder(variable_name="messages"),
    ])


async def build_workflow():
    mcp_tool_list = await client.get_tools()
    llm_with_tools = llm.bind_tools(tools + mcp_tool_list)
    for tool in mcp_tool_list:
        print(f"Tool Name: {tool.name}")
    conn = await aiosqlite.connect("chat_bot.db")
    checkpointer = AsyncSqliteSaver(conn)

        
    async def chat_with_ai(state: ChatState):
        messages = state['messages']
        chain = prompt_template | llm_with_tools 

        response = await chain.ainvoke({"messages" : messages})
        return  {"messages": [response]}
    
    tool_node = ToolNode(tools)

    graph = StateGraph(ChatState)
    graph.add_node('chat_node' , chat_with_ai)
    graph.add_node('tools', tool_node)

    #add_edges
    graph.add_edge(START, 'chat_node')
    graph.add_conditional_edges('chat_node', tools_condition)
    graph.add_edge('tools', 'chat_node')

    workflow = graph.compile(checkpointer=checkpointer)

    return workflow, conn

async def fetch_all_thread_ids(conn) -> list[str]:
    """
    Fetches all distinct thread IDs from the checkpoints table in the SQLite database.
    Args:
        conn (aiosqlite.Connection): An active connection to the SQLite database.
    Returns:
        list[str]: A list of distinct thread IDs, ordered by the most recent checkpoint first.
    """
    
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'"
    ) as cursor:
        if not await cursor.fetchone():
            return []

    # Query distinct threads ordered by latest activity
    async with conn.execute("""
        SELECT DISTINCT thread_id 
        FROM checkpoints 
        ORDER BY checkpoint_id DESC
    """) as cursor:
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def main():
    workflow, conn = await build_workflow()
    while True:
        input_text = input("You: ")
        if input_text.lower() == "exit":
            break
        config = {"configurable": {"thread_id": "user_thread_1"}}  # You can change the thread_id as needed
        respone = await workflow.ainvoke({"messages": [HumanMessage(content=input_text)]}, config=config)
        print(f"AI: {respone['messages'][-1].text}")
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())