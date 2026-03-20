from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uuid
from app.services.ingest_url import ingest_url
from app.services.ingest_document import ingest_document
from app.services.ingest_topic import ingest_topic
from app.db.database import get_connection

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/url")
async def ingest_url_endpoint(url: str = Form(...)):
    try:
        result = await ingest_url(url)
        session_id = _save_session(result)
        return {"session_id": session_id, **result}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch URL. Check that it's publicly accessible.")

@router.post("/document")
async def ingest_document_endpoint(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        result = await ingest_document(file_bytes, file.filename)
        session_id = _save_session(result)
        return {"session_id": session_id, **result}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process document.")

@router.post("/topic")
async def ingest_topic_endpoint(topic: str = Form(...)):
    try:
        result = await ingest_topic(topic)
        session_id = _save_session(result)
        return {"session_id": session_id, **result}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to research topic.")

def _save_session(result: dict) -> str:
    session_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (id, input_type, source_label, raw_content) VALUES (?, ?, ?, ?)",
        (session_id, result["input_type"], result["source_label"], result["content"])
    )
    conn.commit()
    conn.close()
    return session_id