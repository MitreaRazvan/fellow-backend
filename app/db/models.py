from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Session:
    id: str
    input_type: str
    source_label: str
    created_at: Optional[str] = None
    raw_content: Optional[str] = None
    report_markdown: Optional[str] = None
    suggestions_json: Optional[str] = None

@dataclass
class Message:
    id: str
    session_id: str
    role: str
    content: str
    created_at: Optional[str] = None