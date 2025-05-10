from langchain.utilities import SerpAPIWrapper
from typing import List, Dict, Any
from ..models.job_models import JobResult, JobSearchRequest
from ..config.settings import get_settings
import asyncio
from concurrent.futures import ThreadPoolExecutor

class JobSearchService:
    def __init__(self):
        self.settings = get_settings()
        self.search = SerpAPIWrapper(serpapi_api_key=self.settings.SERPAPI_API_KEY)
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

    def _construct_search_query(self, request: JobSearchRequest) -> str:
        query_parts = [request.query, "jobs"]

        if request.location:
            query_parts.append(f"in {request.location}")
        if request.job_type:
            query_parts.append(request.job_type)
        if request.experience_level:
            query_parts.append(request.experience_level)

        return " ".join(query_parts)

    def _process_search_results(self, results: Dict[str, Any]) -> List[JobResult]:
        job_results = []
        for result in results.get("organic_results", []):
            job_results.append(JobResult(
                title=result.get("title", ""),
                link=result.get("link", ""),
                snippet=result.get("snippet", ""),
                company=result.get("source", ""),
                location=result.get("location", ""),
                posted_date=result.get("date", "")
            ))
        return job_results

    async def _run_in_threadpool(self, func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, func, *args)

    async def search_jobs(self, request: JobSearchRequest) -> List[JobResult]:
        try:
            search_query = self._construct_search_query(request)

            # Run the synchronous SerpAPI call in a thread pool
            results = await self._run_in_threadpool(
                self.search.results,
                search_query,
                request.num_results
            )

            # Process results in the event loop
            return self._process_search_results(results)
        except Exception as e:
            raise Exception(f"Error searching jobs: {str(e)}")

    async def search_multiple_queries(self, requests: List[JobSearchRequest]) -> Dict[str, List[JobResult]]:
        """
        Search for multiple job queries concurrently
        """
        try:
            # Create tasks for each search request
            tasks = [self.search_jobs(request) for request in requests]

            # Run all searches concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine results with their respective queries
            return {
                request.query: result if not isinstance(result, Exception) else []
                for request, result in zip(requests, results)
            }
        except Exception as e:
            raise Exception(f"Error in multiple job searches: {str(e)}")

    async def cleanup(self):
        """
        Cleanup resources when the service is shutting down
        """
        self._thread_pool.shutdown(wait=True)