from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
import os
from langsmith import traceable

os.environ['LANGSMITH_PROJECT'] = 'langgraph-workflow-observability'

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")

class SentimentOutputSchema(BaseModel):
    sentiment: Literal["positive", "negative"] = Field(..., description="The sentiment of the review.")

sentiment_llm = llm.with_structured_output(SentimentOutputSchema)

class ReviewState(TypedDict):
    review: str
    sentiment: Literal["positive", "negative"]
    assessment: dict
    response: str

from langchain_core.prompts import PromptTemplate

@traceable(name="Find Sentiment", description="Determine the sentiment of the review, either positive or negative." , tags=["customer support", "sentiment analysis"])
def find_sentiment(ReviewState):
    review = ReviewState['review']
    prompt_template = PromptTemplate(
        input_variables=["review"],
        template="Determine the sentiment of the following review: {review}. Respond with either 'positive' or 'negative'."
    )
    chain = prompt_template | sentiment_llm
    sentiment_result = chain.invoke({"review": review})
    return {"sentiment" : sentiment_result.sentiment}

graph = StateGraph(ReviewState)

@traceable(name="Check Sentiment Mood", description="Check the sentiment of the review and determine the appropriate next step.", tags=["customer support", "conditional logic", "sentiment analysis"])
def check_sentiment_mood(ReviewState):
    sentiment = ReviewState['sentiment']
    if sentiment == "positive":
        return 'generate_positive_response'
    else:
        return 'run_assessment'

class AssessmentOutputSchema(BaseModel):
    mood: Literal['angry', 'disappointed', 'constructive', 'calm'] = Field(..., description="The mood/tonality of the review, either 'angry', 'disappointed', or 'constructive', 'calm'.")
    issue_type: Literal['product', 'service', 'delivery', 'bug'] = Field(..., description="The type of issue mentioned in the review, either 'product', 'service', 'delivery', or 'bug'.")
    urgency: Literal['high', 'medium', 'low'] = Field(..., description="The urgency of the issue mentioned in the review, either 'high', 'medium', or 'low'.")

assessement_llm = llm.with_structured_output(AssessmentOutputSchema)

from langchain_core.output_parsers import StrOutputParser

@traceable(name="Run Assessment", description="Run an assessment of the review to determine the mood, issue type, and urgency.", tags=["customer support", "review assessment", "issue analysis"])
def run_assessment(ReviewState):
    review = ReviewState['review']
    prompt_template = PromptTemplate(
        input_variables=["review"],
        template="Assess the following review: \n\n{review}. \n\nProvide a detailed analysis of the issues mentioned."
    )
    chain = prompt_template | assessement_llm
    assessment_result = chain.invoke({"review": review})
    return {"assessment": assessment_result.model_dump()}

@traceable(name="Generate Positive Response", description="Generate a positive thank you message to the review.", tags=["customer support", "review response", "positive"])
def generate_positive_response(ReviewState):
    review = ReviewState['review']
    prompt_template = PromptTemplate(
        input_variables=["review"],
        template="Generate a positive thank you message to the following review: \n{review}."
    )
    parser = StrOutputParser()
    chain = prompt_template | llm | parser
    response_result = chain.invoke({"review": review})
    return {"response": response_result}

@traceable(name="Generate Negative Response", description="Generate a professional empathetic response to the review, addressing the issues mentioned and providing a solution or next steps.", tags=["customer support", "review response", "empathy"])
def generate_negative_response(ReviewState):
    review = ReviewState['review']
    assessment = ReviewState['assessment']
    prompt_template = PromptTemplate(
        input_variables=["review", "assessment"],
        template="Generate a professional empathetic response to the following review: \n{review}. \n\nThe assessment of the review is as follows: {assessment}. \n\nPlease address the issues mentioned in the review and provide a solution or next steps."
    )
    parser = StrOutputParser()
    chain = prompt_template | llm | parser
    response_result = chain.invoke({"review": review, "assessment": assessment})
    return {"response": response_result}

graph.add_node('find_sentiment', find_sentiment)
graph.add_node('run_assessment', run_assessment)
graph.add_node('generate_positive_response', generate_positive_response)
graph.add_node('generate_negative_response', generate_negative_response)

graph.add_edge(START, 'find_sentiment')
graph.add_conditional_edges('find_sentiment', check_sentiment_mood)
graph.add_edge('run_assessment', 'generate_negative_response')
graph.add_edge('generate_positive_response', END)
graph.add_edge('generate_negative_response', END)

workflow = graph.compile()

input_state = {
    "review" : "I recently purchased a product from your store, and I am extremely disappointed with the quality. The item arrived damaged, and the customer service was unhelpful when I tried to resolve the issue. I expected better from your company."
}

config = {
    "run_name": "conditional_workflow_observability",
    "tags": ["customer support", "review response", "sentiment analysis"],
    "metadata": {
        "workflow_type": "conditional",
        "description": "A workflow that analyzes customer reviews and generates appropriate responses based on sentiment and assessment.",
        "review_length": len(input_state['review']),
        "model_used": "gemini-3.5-flash-lite",
    }
}
final_state = workflow.invoke(input_state, config=config)

print("Response:", final_state['response'])

print(final_state)