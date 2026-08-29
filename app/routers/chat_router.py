from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
from app.config import CHAT_URL, llm_payload, llm_headers

router = APIRouter(prefix="/chat", tags=["chat"])



class DirectChatRequest(BaseModel):
    message: str
    system: str = "You are a helpful research assistant."
    max_tokens: int = 1500


@router.post("/direct")
async def direct_chat(request: DirectChatRequest):
    async def stream():
        payload = llm_payload(**{
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.message},
            ],
            "max_tokens": request.max_tokens,
            "temperature": 0.4,
            "stream": True,
        })

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                CHAT_URL,
                headers=llm_headers(),
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
