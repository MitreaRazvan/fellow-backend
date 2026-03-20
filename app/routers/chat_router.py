from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
from app.config import GROQ_API_KEY

router = APIRouter(prefix="/chat", tags=["chat"])

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class DirectChatRequest(BaseModel):
    message: str
    system: str = "You are a helpful research assistant."
    max_tokens: int = 1500


@router.post("/direct")
async def direct_chat(request: DirectChatRequest):
    async def stream():
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.message},
            ],
            "max_tokens": request.max_tokens,
            "temperature": 0.4,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return
                    try:
                        parsed = json.loads(data)
                        delta = parsed["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield f"data: {json.dumps({'type': 'chunk', 'content': delta})}\n\n"
                    except Exception:
                        continue

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
