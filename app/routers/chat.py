"""
Chat API — streaming endpoint for SOP chatbot.
"""
import json
from typing import List, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.sop_store import get_sop
from app.services.chat_agent import chat_stream

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    slug: str
    message: str
    history: List[Dict] = []


@router.post("/stream")
async def stream_chat(req: ChatRequest):
    sop = get_sop(req.slug)
    if not sop:
        raise HTTPException(404, "SOP not found.")
    if not sop.get("markdown"):
        raise HTTPException(422, "SOP has no content to chat about.")

    def generate():
        for chunk in chat_stream(sop["markdown"], req.history, req.message):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
