from typing import List
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel
import os
from enums import MessageType
from chatbot_model import model_response

router = APIRouter(tags=["Chatbot"])

class HistoryInput(BaseModel):
    type: MessageType
    message: str

class RequestData(BaseModel):
    input: str
    chat_history: List[HistoryInput]

@router.post("/chatbot")
async def chatbot(data: RequestData):
    history = []
    for h in data.chat_history:
        if h.type == MessageType.AI:
            history.append(AIMessage(h.message))
        else:
            history.append(HumanMessage(h.message))
    
    resp = model_response(data.input, history)
    return {
        "response": resp
    }