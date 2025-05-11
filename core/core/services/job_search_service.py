from typing import List
from ..models.job_models import JobResult, JobSearchRequest, JobSearchResponse
from ..search.providers.serp_search import SerpSearchService
from ..search.base.search_service import SearchRequest
from ..config.settings import get_settings


class JobSearchService:
    def __init__(self):
        self.settings = get_settings()
        self.search_service = SerpSearchService()

    def _construct_search_query(self, request: JobSearchRequest) -> str:
        """Construct a search query for job search"""
        query_parts = [request.query, "jobs"]

        if request.location:
            query_parts.append(f"in {request.location}")
        if request.job_type:
            query_parts.append(request.job_type)
        if request.experience_level:
            query_parts.append(request.experience_level)

        return " ".join(query_parts)

    async def search_jobs(self, request: JobSearchRequest) -> JobSearchResponse:
        try:
            # Construct job-specific search query
            search_query = self._construct_search_query(request)

            # Create search request
            search_request = SearchRequest(
                query=search_query,
                num_results=request.num_results
            )

            # Perform search
            search_results = await self.search_service.search(search_request)

            # Convert search results to job results
            job_results = [
                JobResult(
                    title=result.title,
                    link=result.link,
                    snippet=result.snippet,
                    company=result.source,
                    location=result.metadata.get("location"),
                    posted_date=result.metadata.get("date")
                )
                for result in search_results
            ]

            return JobSearchResponse(
                results=job_results,
                total_results=len(job_results),
                search_query=request.query
            )
        except Exception as e:
            raise Exception(f"Error searching jobs: {str(e)}")

    async def cleanup(self):
        """Cleanup resources"""
        await self.search_service.cleanup()
