from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from typing import List, AsyncGenerator, Dict, Any, Optional
from ..models.job_models import JobSearchRequest, JobResult, JobSearchResponse
from ..models.document_models import DocumentType, DocumentInfo
from ..models.application_models import (
    ApplicationRequest,
    ApplicationResponse,
    ApplicationStatus,
    ApplicationListResponse,
    ApplicationUpdateRequest
)
from ..services.job_search_service import JobSearchService
from ..services.job_application_service import JobApplicationService
from ..services.document_service import DocumentService
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

async def get_document_service() -> AsyncGenerator[DocumentService, None]:
    service = None
    try:
        service = DocumentService()
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

@router.post("/apply-with-url", response_model=ApplicationResponse)
async def apply_with_url(
    request: ApplicationRequest,
    resume: Optional[UploadFile] = File(None),
    cover_letter: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None,
    job_service: JobApplicationService = Depends(get_job_application_service),
    document_service: DocumentService = Depends(get_document_service)
) -> ApplicationResponse:
    """
    Apply for a job using a URL and optional documents
    """
    try:
        # Create a job result from the URL
        job = JobResult(
            title="",  # Will be filled by scraping
            link=str(request.job_url),
            snippet="",
            company=""
        )

        # Process documents if provided
        documents = {}
        if resume:
            resume_info = await document_service.save_document(resume, DocumentType.RESUME)
            documents["resume"] = resume_info
            if background_tasks:
                background_tasks.add_task(resume.close)

        if cover_letter:
            cover_letter_info = await document_service.save_document(cover_letter, DocumentType.COVER_LETTER)
            documents["cover_letter"] = cover_letter_info
            if background_tasks:
                background_tasks.add_task(cover_letter.close)

        # Process the job application
        return await job_service.process_job_application(job, documents)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing job application: {str(e)}"
        )

@router.get("/applications", response_model=ApplicationListResponse)
async def list_applications(
    status: Optional[ApplicationStatus] = None,
    page: int = 1,
    page_size: int = 10,
    job_service: JobApplicationService = Depends(get_job_application_service)
) -> ApplicationListResponse:
    """
    List all job applications with optional filtering
    """
    try:
        # This would be implemented in the service
        # For now, return empty list
        return ApplicationListResponse(
            applications=[],
            total_count=0,
            status_filter=status,
            page=page,
            page_size=page_size,
            total_pages=0
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing applications: {str(e)}"
        )

@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: str,
    update: ApplicationUpdateRequest,
    job_service: JobApplicationService = Depends(get_job_application_service)
) -> ApplicationResponse:
    """
    Update an existing job application
    """
    try:
        # This would be implemented in the service
        # For now, raise not implemented
        raise HTTPException(
            status_code=501,
            detail="Not implemented"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating application: {str(e)}"
        )