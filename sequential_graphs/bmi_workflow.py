from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

class BMIState(BaseModel):
    height: float = Field(description="Height in meters" , gt=0)
    weight: float = Field(description="Weight in kilograms", gt=0)
    bmi: float = Field(description="Body Mass Index")
