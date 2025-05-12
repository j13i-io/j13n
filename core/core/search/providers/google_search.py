from typing import List, Dict, Any, Optional
import re
from langchain_community.utilities import GoogleSearchAPIWrapper
from ...config.settings import get_settings
from ..base.job_search_service import BaseJobSearchService, JobSearchRequest, JobSearchResult
from ..base.search_service import SearchResult

class GoogleJobSearchService(BaseJobSearchService):

    def __init__(self, llm_model: str = "gpt-4", temperature: float = 0):
        super().__init__(llm_model, temperature)
        settings = get_settings()

        # Initialize Google Search API wrapper
        self.search_api = GoogleSearchAPIWrapper(
            google_api_key=settings.google_api_key,
            google_cse_id=settings.google_cse_id
        )

    @property
    def provider_name(self) -> str:
        """Return the name of the search provider"""
        return "Google Search API"

    async def extract_application_url(self, search_result: SearchResult) -> str:

        # The link from Google search is usually the most direct one
        application_url = search_result.link

        # Check if the URL is likely a job application URL
        application_patterns = [
            r'apply', r'application', r'job', r'career', r'position',
            r'greenhouse\.io', r'lever\.co', r'workday\.com', r'taleo\.net',
            r'linkedin\.com\/jobs', r'indeed\.com\/viewjob', r'glassdoor\.com\/job'
        ]

        is_application_url = any(re.search(pattern, application_url, re.IGNORECASE) for pattern in application_patterns)

        if not is_application_url:
            # Could implement additional logic here to find a more direct application URL
            # For now, we'll just return the original URL
            pass

        return application_url

    async def convert_to_job_search_result(self, search_result: SearchResult) -> JobSearchResult:

        # Extract application URL
        application_url = await self.extract_application_url(search_result)

        # Extract job details from title and snippet
        job_title, company_name = self._extract_job_and_company(search_result.title, search_result.snippet)
        location = self._extract_location(search_result.snippet)

        return JobSearchResult(
            title=search_result.title,
            link=search_result.link,
            snippet=search_result.snippet,
            source=search_result.source,
            metadata=search_result.metadata,
            company_name=company_name,
            job_title=job_title,
            location=location,
            application_url=application_url,
            salary_range=None,
            job_type=None,
            posted_date=None,
            job_description=search_result.snippet
        )

    async def search(self, request: JobSearchRequest) -> List[JobSearchResult]:

        # Optimize the search query using LLM
        optimized_query = await self.optimize_search_query(request)

        # Perform the search using Google Search API
        raw_results = self.search_api.results(optimized_query, num_results=request.num_results)

        # Convert raw results to SearchResult objects
        search_results = [
            SearchResult(
                title=result.get("title", ""),
                link=result.get("link", ""),
                snippet=result.get("snippet", ""),
                source=result.get("source", ""),
                metadata={
                    "position": i,
                    "html_snippet": result.get("htmlSnippet", ""),
                    "mime_type": result.get("mime", ""),
                    "file_format": result.get("fileFormat", ""),
                    "image": result.get("image", {}),
                    "additional_links": result.get("additional_links", [])
                }
            )
            for i, result in enumerate(raw_results)
        ]

        # Process each search result to extract job details and application URL
        job_results = []
        for result in search_results:
            # Convert to JobSearchResult using the standardized method
            job_result = await self.convert_to_job_search_result(result)
            job_results.append(job_result)

        return job_results

    def _extract_job_and_company(self, title: str, snippet: str) -> tuple[str, str]:

        # Common patterns in job listing titles
        # Example: "Software Engineer - Google Careers"
        # Example: "Data Scientist at Microsoft"

        # Try to extract from title first
        company_patterns = [
            r'(.+?)\s+at\s+(.+?)(?:\s|$)',  # "Job Title at Company"
            r'(.+?)\s*[-|]\s*(.+?)\s+(?:careers|jobs|hiring)',  # "Job Title - Company Careers"
            r'(.+?)\s+\((.+?)\)',  # "Job Title (Company)"
        ]

        for pattern in company_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1).strip(), match.group(2).strip()

        # If we couldn't extract from title, use a simpler approach
        # Assume the first part of the title is the job title
        parts = title.split(' - ', 1)
        if len(parts) > 1:
            return parts[0].strip(), parts[1].strip()

        # If we still can't extract, return the title as job title and unknown for company
        return title, "Unknown Company"

    def _extract_location(self, snippet: str) -> str:

        # Common location patterns in job listings
        location_patterns = [
            r'location\s*:?\s*([^\.]+)',
            r'in\s+([A-Za-z\s,]+(?:, [A-Z]{2}))',
            r'(?:remote|onsite|hybrid)\s+in\s+([^\.]+)',
            r'([A-Za-z\s]+(?:, [A-Z]{2}))'
        ]


        for pattern in location_patterns:
            match = re.search(pattern, snippet, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Unknown Location"

    async def cleanup(self) -> None:
        """Cleanup any resources used by the search service"""
        # No specific cleanup needed for Google Search API
        pass
