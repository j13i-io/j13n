from abc import abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

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


def _get_query_optimization_prompt() -> ChatPromptTemplate:
    """Get the prompt template for query optimization.
    Can be overridden by specific providers to customize the prompt.
    """
    return ChatPromptTemplate.from_messages([
        ("system", """You are a job search expert. Your task is to optimize the given job search parameters
        into an effective search query. Follow these guidelines:

        1. Use site: operator to target specific job boards:
           - site:linkedin.com/jobs
           - site:indeed.com
           - site:glassdoor.com
           - site:careers.google.com
           - site:jobs.apple.com
           - site:jobs.lever.co
           - site:greenhouse.io

        2. Use advanced search operators:
           - Use quotes for exact phrases: "software engineer"
           - Use OR for alternatives: (senior OR lead)
           - Use - to exclude terms: -intern -contractor
           - Use intitle: for job titles
           - Use inurl: for specific sections

        3. Add relevant filters:
           - Add "apply now" or "apply online" for direct application pages
           - Add "posted" for recent jobs
           - Add location-specific terms
           - Add experience level indicators

        4. Format the query to prioritize:
           - Direct application pages
           - Recent postings
           - Relevant job titles
           - Company career pages

        Example format:
        (site:linkedin.com/jobs OR site:indeed.com) "software engineer" (senior OR lead) -intern -contractor "apply now" posted:7d"""),
        ("user", """Job Title: {job_title}
        Location: {location}
        Company: {company}
        Job Type: {job_type}
        Experience: {experience}
        Salary: {salary}
        Remote: {remote}
        Posted Within: {posted_within}

        Additional Context:
        - Focus on direct application pages
        - Prioritize company career pages
        - Include multiple job boards
        - Add relevant filters for better results""")
    ])


class BaseJobSearchService(BaseSearchService):
    """Abstract base class for job search services"""

    def __init__(self, llm_model: str = "gpt-4", temperature: float = 0):
        """Initialize the base job search service

        Args:
            llm_model: The LLM model to use for query optimization
            temperature: The temperature setting for the LLM
        """
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=temperature
        )
        self._query_cache: Dict[str, str] = {}

    async def optimize_search_query(self, request: JobSearchRequest) -> str:
        """
        Use LLM to optimize the search query for better job search results.
        This base implementation can be overridden by specific providers if needed.

        Args:
            request: JobSearchRequest containing job search parameters

        Returns:
            Optimized search query string
        """
        # Check cache first
        cache_key = f"{request.job_title}:{request.location}:{request.company}"
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        # Get provider-specific prompt template
        prompt = _get_query_optimization_prompt()

        # Format the prompt with the request parameters
        formatted_prompt = prompt.format_messages(
            job_title=request.job_title or "",
            location=request.location or "",
            company=request.company or "",
            job_type=request.job_type or "",
            experience=request.experience_level or "",
            salary=request.salary_range or "",
            remote="remote" if request.remote else "",
            posted_within=request.posted_within or ""
        )

        # Get optimized query from LLM
        response = await self.llm.agenerate([formatted_prompt])
        optimized_query = response.generations[0][0].text.strip()

        # Cache the result
        self._query_cache[cache_key] = optimized_query
        return optimized_query

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
    async def convert_to_job_search_result(self, search_result: SearchResult) -> JobSearchResult:
        """
        Convert a generic SearchResult to a JobSearchResult with job-specific details

        Args:
            search_result: Generic SearchResult object from the search provider

        Returns:
            JobSearchResult object with job-specific details extracted from the search result
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
