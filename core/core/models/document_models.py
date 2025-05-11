from enum import Enum
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class DocumentType(str, Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"

class DocumentInfo(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    document_type: DocumentType
    size: int
    content_type: str
    last_modified: Optional[datetime] = None

class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_count: int
    document_type: Optional[DocumentType] = None