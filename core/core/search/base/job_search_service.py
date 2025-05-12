from abc import abstractmethod
from typing import List, Optional
from pydantic import BaseModel

from .search_service import BaseSearchService, SearchRequest, SearchResult


class JobSearchResult(SearchResult):
    """Extended search result specifically for job listings"""
    company_name: str
    job_title: str
    location: str
    salary_range: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Part-time, Contract, etc.
    posted_date: Optional[str] = None
    application_url: str  # Direct URL to apply for the job
    job_description: Optional[str] = None


class JobSearchRequest(SearchRequest):
    """Extended search request with job-specific parameters"""
    job_title: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    remote: Optional[bool] = None
    posted_within: Optional[str] = None  # e.g., "24h", "7d", "30d"


class BaseJobSearchService(BaseSearchService):
    """Abstract base class for job search services"""

    @abstractmethod
    async def optimize_search_query(self, request: JobSearchRequest) -> str:
        """
        Use LLM to optimize the search query for better job search results

        Args:
            request: JobSearchRequest containing job search parameters

        Returns:
            Optimized search query string
        """
        pass

    @abstractmethod
    async def extract_application_url(self, search_result: SearchResult) -> str:
        """
        Extract or generate the direct application URL from a search result

        Args:
            search_result: Raw search result from the search provider

        Returns:
            Direct URL to the job application page
        """
        pass

    @abstractmethod
    async def search(self, request: JobSearchRequest) -> List[JobSearchResult]:
        """
        Perform a job search using the provided request parameters

        Args:
            request: JobSearchRequest object containing job search parameters

        Returns:
            List of JobSearchResult objects with direct application URLs
        """
        pass