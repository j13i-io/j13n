from fastapi import APIRouter, HTTPException, Depends
from typing import List, AsyncGenerator, Dict, Any
from ..models.job_models import JobSearchRequest, JobResult, JobSearchResponse
from ..services.job_search_service import JobSearchService
from ..services.job_application_service import JobApplicationService
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

async def get_job_application_service() -> AsyncGenerator[JobApplicationService, None]:
    service = None
    try:
        service = JobApplicationService()
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

@router.post("/apply", response_model=Dict[str, Any])
async def process_job_application(
    job: JobResult,
    service: JobApplicationService = Depends(get_job_application_service)
):
    try:
        result = await service.process_job_application(job)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing job application: {str(e)}"
        )

@router.post("/search-and-apply", response_model=Dict[str, Any])
async def search_and_apply(
    request: JobSearchRequest = Depends(validate_search_request),
    search_service: JobSearchService = Depends(get_job_search_service),
    application_service: JobApplicationService = Depends(get_job_application_service)
):
    try:
        # First search for jobs
        search_results = await search_service.search_jobs(request)

        if not search_results.results:
            raise HTTPException(
                status_code=404,
                detail="No jobs found matching your criteria"
            )

        # Process the first job in the results
        first_job = search_results.results[0]
        application_result = await application_service.process_job_application(first_job)

        return {
            "search_results": search_results,
            "application": application_result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in search and apply process: {str(e)}"
        )