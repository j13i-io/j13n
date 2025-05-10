from fastapi import APIRouter, HTTPException, Depends
from typing import List, AsyncGenerator
from ..models.job_models import JobSearchRequest, JobResult, JobSearchResponse
from ..services.job_search_service import JobSearchService
from ..config.settings import get_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()

async def get_job_search_service() -> AsyncGenerator[JobSearchService, None]:
    service = None
    try:
        service = JobSearchService()
        yield service
    finally:
        if service:
            await service.cleanup()

async def validate_search_request(request: JobSearchRequest) -> JobSearchRequest:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    return request

@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(
    request: JobSearchRequest = Depends(validate_search_request),
    service: JobSearchService = Depends(get_job_search_service)
):
    try:
        results = await service.search_jobs(request)
        return JobSearchResponse(
            results=results,
            total_results=len(results),
            search_query=request.query
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching jobs: {str(e)}"
        )