from typing import List, Optional

from pydantic import BaseModel


class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = ""
    num_results: Optional[int] = 10
    job_type: Optional[str] = None
    experience_level: Optional[str] = None


class JobResult(BaseModel):
    title: str
    link: str
    snippet: str
    company: Optional[str] = None
    location: Optional[str] = None
    posted_date: Optional[str] = None


class JobSearchResponse(BaseModel):
    results: List[JobResult]
    total_results: int
    search_query: str
