from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from app.services.report_generator import generate_report, generate_suggestions, extract_image_keywords
from app.db.database import get_connection

router = APIRouter(prefix="/report", tags=["report"])

class GenerateReportRequest(BaseModel):
    session_id: str

@router.post("/generate")
async def generate_report_endpoint(request: GenerateReportRequest):
    conn = get_connection()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (request.session_id,)
    ).fetchone()
    conn.close()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if not session["raw_content"]:
        raise HTTPException(status_code=422, detail="Session has no content to analyze.")

    async def stream_report():
        full_report = []

        # Stream the report chunks
        async for chunk in generate_report(
            session["raw_content"],
            session["source_label"]
        ):
            full_report.append(chunk)
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        # Report complete — save it
        complete_report = "".join(full_report)

        # Generate suggestions + image keywords in parallel
        suggestions = await generate_suggestions(complete_report)
        image_keywords = await extract_image_keywords(session["source_label"], complete_report)

        # Save to database
        conn = get_connection()
        conn.execute(
            "UPDATE sessions SET report_markdown = ?, suggestions_json = ? WHERE id = ?",
            (complete_report, json.dumps(suggestions), request.session_id)
        )
        conn.commit()
        conn.close()

        # Send suggestions to frontend
        yield f"data: {json.dumps({'type': 'suggestions', 'content': suggestions})}\n\n"

        # Send image keywords
        yield f"data: {json.dumps({'type': 'image_keywords', 'content': image_keywords})}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        stream_report(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    conn = get_connection()
    session = conn.execute(
        "SELECT id, input_type, source_label, report_markdown, suggestions_json, created_at FROM sessions WHERE id = ?",
        (session_id,)
    ).fetchone()
    conn.close()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    return {
        "session_id": session["id"],
        "input_type": session["input_type"],
        "source_label": session["source_label"],
        "report_markdown": session["report_markdown"],
        "suggestions": json.loads(session["suggestions_json"]) if session["suggestions_json"] else [],
        "created_at": session["created_at"]
    }


@router.get("/sessions")
async def list_sessions():
    conn = get_connection()
    sessions = conn.execute(
        """SELECT id, input_type, source_label, created_at 
           FROM sessions 
           WHERE report_markdown IS NOT NULL 
           ORDER BY created_at DESC 
           LIMIT 50"""
    ).fetchall()
    conn.close()

    return [
        {
            "session_id": s["id"],
            "input_type": s["input_type"],
            "source_label": s["source_label"],
            "created_at": s["created_at"],
        }
        for s in sessions
    ]


@router.post("/suggestions/refresh")
async def refresh_suggestions(request: dict):
    conn = get_connection()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (request["session_id"],)).fetchone()
    conn.close()
    if not session or not session["report_markdown"]:
        raise HTTPException(status_code=404, detail="Session not found.")
    suggestions = await generate_suggestions(session["report_markdown"])
    return {"suggestions": suggestions}