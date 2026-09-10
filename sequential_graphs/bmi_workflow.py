from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

class BMIState(BaseModel):
    height: float = Field(description="Height in meters" , gt=0)
    weight: float = Field(description="Weight in kilograms", gt=0)
    bmi: float = Field(description="Body Mass Index")

#define task_executor function
def calc_bmi(state: BMIState) -> BMIState:
    bmi = state.weight / (state.height ** 2)
    bmi = round(bmi, 2)
    state.bmi = bmi
    return state

#define graph
graph = StateGraph(BMIState)

#add nodes
graph.add_node("calculate_bmi", calc_bmi)

#add edges
graph.add_edge(START, "calculate_bmi")
graph.add_edge("calculate_bmi", END)

#compile graph
workflow = graph.compile()

#execute workflow
print("Executing BMI Workflow...")
height = float(input("Enter height in meters: "))
weight = float(input("Enter weight in kilograms: "))

#Wrap the input values in a BMIState object
initial_state = BMIState(**{"height": height, "weight": weight})

final_state =workflow.invoke(initial_state)
print(f"Final State: {final_state}")