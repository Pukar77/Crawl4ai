from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel


app = FastAPI(
    title="Add Function",
    description="This function adds two different values",
    version="1.0.1"
)


print("Hey user, please enter 2 numbers to add")

#pydantic
class AddRequest(BaseModel):
    num1: float
    num2: float
    
class AddResponse(BaseModel):
    result: float
    
@app.post("/add/numbers", response_model=AddResponse)
def add(request:AddRequest):
    result = request.num1+request.num2
    return {"result":result}

@app.post("/add/numbers/sub", response_model=AddResponse)
def sub(request:AddRequest):
    result = request.num1-request.num2
    return {"result":result}




    
    
    
    
