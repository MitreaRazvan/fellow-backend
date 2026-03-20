import pypdf
import io
from typing import Optional

async def ingest_document(file_bytes: bytes, filename: str) -> dict:
    extension = filename.lower().split(".")[-1]

    if extension == "pdf":
        return await _process_pdf(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file type: {extension}. Supported: PDF")

async def _process_pdf(file_bytes: bytes, filename: str) -> dict:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(f"[Page {i+1}]\n{text.strip()}")

    if not pages:
        raise ValueError("Could not extract text from this PDF. It may be scanned or image-based.")

    content = "\n\n".join(pages)

    return {
        "content": content,
        "source_label": filename,
        "input_type": "document",
        "word_count": len(content.split())
    }