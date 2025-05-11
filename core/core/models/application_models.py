from typing import Dict, Any
from pydantic import BaseModel, HttpUrl

class JobAnalysis(BaseModel):
    url: HttpUrl
    form_fields: Dict[str, Any]  # Dynamic form fields from the job posting

class ApplicationRequest(BaseModel):
    job_url: HttpUrl
    form_data: Dict[str, Any]
    resume_id: str | None = None
    cover_letter_id: str | None = None

class ApplicationResponse(BaseModel):
    analysis: JobAnalysis
    success: bool
    message: str
