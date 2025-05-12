from typing import List, Dict, Any, Optional
import re
from langchain_community.utilities import SerpAPIWrapper
from ...config.settings import get_settings
from ..base.job_search_service import BaseJobSearchService, JobSearchRequest, JobSearchResult
from ..base.search_service import SearchResult, SearchRequest

class SerpSearchService(BaseJobSearchService):
    """
    Job search service using SerpAPI via LangChain.
    This provides comprehensive search results but may be more expensive than Google Search API.

    Requires:
    - SerpAPI Key
    """

    def __init__(self, llm_model: str = "gpt-4", temperature: float = 0):
        """Initialize the SerpAPI job search service

        Args:
            llm_model: The LLM model to use for query optimization
            temperature: The temperature setting for the LLM
        """
        super().__init__(llm_model, temperature)
        settings = get_settings()

        # Initialize SerpAPI wrapper
        self.search_api = SerpAPIWrapper(
            serpapi_api_key=settings.serpapi_key,
            search_engine="google",  # Use Google as the search engine
            params={
                "engine": "google_jobs",  # Specifically target Google Jobs
                "gl": "us",  # Geo-location, can be configured based on user preferences
                "hl": "en"   # Language
            }
        )

    @property
    def provider_name(self) -> str:
        """Return the name of the search provider"""
        return "SerpAPI"

    async def extract_application_url(self, search_result: SearchResult) -> str:

        if search_result.metadata and "apply_link" in search_result.metadata:
            return search_result.metadata["apply_link"]

        # If no direct application link is found, use the main link
        application_url = search_result.link

        # Check if the URL is likely a job application URL
        application_patterns = [
            r'apply', r'application', r'job', r'career', r'position',
            r'greenhouse\.io', r'lever\.co', r'workday\.com', r'taleo\.net',
            r'linkedin\.com\/jobs', r'indeed\.com\/viewjob', r'glassdoor\.com\/job'
        ]

        # If the URL doesn't match any application patterns, it might not be a direct application URL
        is_application_url = any(re.search(pattern, application_url, re.IGNORECASE) for pattern in application_patterns)

        if not is_application_url:
            # Could implement additional logic here to find a more direct application URL
            pass

        return application_url


    async def convert_to_job_search_result(self, search_result: SearchResult) -> JobSearchResult:

        if isinstance(search_result, dict):
            result = search_result
            # Extract basic information
            title = result.get("title", "")
            link = result.get("link", "")
            snippet = result.get("description", "")
            if not snippet and "snippet" in result:
                snippet = result.get("snippet", "")

            # Extract company information
            company_name = result.get("company_name", "Unknown Company")

            # Extract location
            location = result.get("location", "Unknown Location")

            # Extract job type
            job_type = None
            extensions = result.get("extensions", [])
            for ext in extensions:
                if any(jt in ext.lower() for jt in ["full-time", "part-time", "contract", "temporary", "internship"]):
                    job_type = ext
                    break

            # Extract salary range
            salary_range = None
            for ext in extensions:
                if "$" in ext or "salary" in ext.lower():
                    salary_range = ext
                    break

            # Extract posted date
            posted_date = None
            for ext in extensions:
                if any(time_unit in ext.lower() for time_unit in ["day", "week", "month", "hour", "minute", "ago"]):
                    posted_date = ext
                    break

            # Extract application URL
            application_url = result.get("apply_link", link)

            # Create metadata
            metadata = {
                "extensions": extensions,
                "job_id": result.get("job_id", ""),
                "detected_extensions": result.get("detected_extensions", {})
            }
        else:
            # This is a standard SearchResult object
            title = search_result.title
            link = search_result.link
            snippet = search_result.snippet
            company_name = search_result.source or "Unknown Company"
            location = "Unknown Location"
            job_type = None
            salary_range = None
            posted_date = None
            metadata = search_result.metadata or {}

            # Extract application URL
            application_url = await self.extract_application_url(search_result)

        # Create and return JobSearchResult
        return JobSearchResult(
            title=title,
            link=link,
            snippet=snippet,
            source=company_name,
            metadata=metadata,
            company_name=company_name,
            job_title=title,
            location=location,
            salary_range=salary_range,
            job_type=job_type,
            posted_date=posted_date,
            application_url=application_url,
            job_description=snippet
        )

    async def search(self, request: JobSearchRequest) -> List[JobSearchResult]:
        """
        Perform a job search using SerpAPI

        Args:
            request: JobSearchRequest object containing job search parameters

        Returns:
            List of JobSearchResult objects with direct application URLs
        """
        # Optimize the search query using LLM
        optimized_query = await self.optimize_search_query(request)

        # Perform the search using SerpAPI
        raw_results = self.search_api.results(optimized_query, num_results=request.num_results)

        # SerpAPI returns results in a different format depending on the engine
        # For google_jobs, the results are in the "jobs_results" key
        job_results = raw_results.get("jobs_results", [])

        if not job_results and "organic_results" in raw_results:
            # Fall back to organic results if no job results
            job_results = raw_results.get("organic_results", [])

        # Convert raw results to JobSearchResult objects
        processed_results = []
        for result in job_results:
            # Convert to JobSearchResult using the standardized method
            job_result = await self.convert_to_job_search_result(result)
            processed_results.append(job_result)

        return processed_results

    async def cleanup(self) -> None:
        """Cleanup any resources used by the search service"""
        # No specific cleanup needed for SerpAPI
        pass
