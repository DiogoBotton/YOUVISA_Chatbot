from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import numpy as np
import os

router = APIRouter(tags=["Chatbot"])

class RequestData(BaseModel):
    input: str

@router.post("/chatbot")
async def chatbot(data: RequestData):
    # TODO
    
    return {
        "response": "teste"
    }