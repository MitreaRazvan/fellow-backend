from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import httpx
import uuid
from app.config import GROQ_API_KEY
from app.db.database import get_connection

router = APIRouter(prefix="/chat", tags=["chat"])

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

class ChatRequest(BaseModel):
    session_id: str
    message: str

@router.post("/message")
async def chat_message(request: ChatRequest):
    conn = get_connection()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (request.session_id,)
    ).fetchone()
    messages = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (request.session_id,)
    ).fetchall()
    conn.close()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not session["report_markdown"]:
        raise HTTPException(status_code=422, detail="Report not yet generated for this session.")

    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), request.session_id, "user", request.message)
    )
    conn.commit()
    conn.close()

    history = [{"role": m["role"], "content": m["content"]} for m in messages]
    history.append({"role": "user", "content": request.message})

    system_prompt = (
        "You are LUMA, an expert research partner. "
        "You have generated the following intelligence report and know it intimately.\n\n"
        "INTELLIGENCE REPORT:\n"
        + session["report_markdown"] +
        "\n\nRULES:\n"
        "- Ground every answer in the report first, then expand beyond it if needed\n"
        "- Be direct and analytical — no filler phrases\n"
        "- If you go beyond the source material, say so explicitly\n"
        "- Suggest follow-up angles when you notice the user circling something important\n"
        "- Keep responses focused and well-structured\n"
        "- Use markdown formatting for clarity"
    )

    async def stream_response():
        full_response = []
        print("STREAM STARTING - report length:", len(session["report_markdown"]))

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                *history
            ],
            "max_tokens": 1024,
            "temperature": 0.4,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            ) as response:
                print("GROQ STATUS:", response.status_code)
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            full_response.append(delta)
                            yield f"data: {json.dumps({'type': 'chunk', 'content': delta})}\n\n"
                    except Exception as e:
                        print("PARSE ERROR:", e)
                        continue

        complete = "".join(full_response)
        print("STREAM DONE - response length:", len(complete))

        conn = get_connection()
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), request.session_id, "assistant", complete)
        )
        conn.commit()
        conn.close()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )