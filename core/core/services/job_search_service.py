from typing import List, Optional, Dict, Any, Type, Tuple, Callable
from functools import lru_cache
import logging
from ..models.job_models import JobResult, JobSearchRequest, JobSearchResponse
from ..search.base.job_search_service import BaseJobSearchService, JobSearchRequest as BaseJobSearchRequest
from ..search.providers.serp_search import SerpSearchService
from ..search.providers.google_search import GoogleJobSearchService
from ..search.base.search_service import SearchRequest
from ..config.settings import get_settings

# Set up logging
logger = logging.getLogger(__name__)


class JobSearchError(Exception):
    """Base exception for job search errors"""
    pass


class ProviderNotFoundError(JobSearchError):
    """Exception raised when a provider is not found"""
    pass


class SearchExecutionError(JobSearchError):
    """Exception raised when there's an error executing the search"""
    pass


class JobSearchService:
    """
    Service for searching jobs using different search providers.
    Supports multiple providers including SerpAPI and Google Search API.

    Features:
    - Provider selection (Google Search API, SerpAPI)
    - Query optimization
    - Result caching
    - Configurable search parameters
    """

    # Available search providers with their configuration options
    PROVIDERS = {
        "serp": {
            "class": SerpSearchService,
            "description": "SerpAPI provider with comprehensive results (higher cost)",
            "default_params": {
                "llm_model": "gpt-4",
                "temperature": 0
            }
        },
        "google": {
            "class": GoogleJobSearchService,
            "description": "Google Search API provider (cost-efficient)",
            "default_params": {
                "llm_model": "gpt-4",
                "temperature": 0
            }
        }
    }

    def __init__(self, provider: str = "google", **provider_params):
        """
        Initialize the job search service with the specified provider

        Args:
            provider: The name of the search provider to use (default: "google")
                     Options: "serp", "google"
            **provider_params: Additional parameters to pass to the provider constructor

        Raises:
            ProviderNotFoundError: If the specified provider is not found
        """
        self.settings = get_settings()
        self.provider_name = provider.lower()
        self._result_cache = {}

        # Get provider configuration
        provider_config = self.PROVIDERS.get(self.provider_name)
        if not provider_config:
            available_providers = ", ".join(self.PROVIDERS.keys())
            raise ProviderNotFoundError(
                f"Unknown provider: {provider}. Available providers: {available_providers}"
            )

        # Merge default params with provided params
        provider_class = provider_config["class"]
        params = {**provider_config["default_params"], **provider_params}

        # Initialize the selected provider
        try:
            self.search_service = provider_class(**params)
            logger.info(f"Initialized job search service with provider: {self.provider_name}")
        except Exception as e:
            logger.error(f"Failed to initialize provider {self.provider_name}: {str(e)}")
            raise ProviderNotFoundError(f"Failed to initialize provider {self.provider_name}: {str(e)}")

    def _construct_search_query(self, request: JobSearchRequest) -> str:
        """
        Construct an optimized search query for job search

        Args:
            request: JobSearchRequest containing search parameters

        Returns:
            Optimized search query string
        """
        # Start with the base query
        query_parts = [request.query]

        # Add "jobs" keyword if not already in the query
        if "job" not in request.query.lower() and "career" not in request.query.lower():
            query_parts.append("jobs")

        # Add location if provided
        if request.location:
            query_parts.append(f"in {request.location}")

        # Add job type if provided
        if request.job_type:
            query_parts.append(request.job_type)

        # Add experience level if provided
        if request.experience_level:
            query_parts.append(request.experience_level)

        # Join all parts with spaces
        return " ".join(query_parts)

    def _get_cache_key(self, request: JobSearchRequest) -> str:
        """
        Generate a cache key for the search request

        Args:
            request: JobSearchRequest to generate a cache key for

        Returns:
            Cache key string
        """
        # Create a cache key based on provider and request parameters
        return f"{self.provider_name}:{request.query}:{request.location}:{request.job_type}:{request.experience_level}:{request.num_results}"

    def _convert_to_job_result(self, result) -> JobResult:
        """
        Convert a JobSearchResult to a JobResult

        Args:
            result: JobSearchResult from the search provider

        Returns:
            JobResult object
        """
        return JobResult(
            title=result.job_title,
            link=result.application_url,
            snippet=result.job_description or result.snippet,
            company=result.company_name,
            location=result.location,
            posted_date=result.posted_date
        )

    async def search_jobs(self, request: JobSearchRequest) -> JobSearchResponse:
        """
        Search for jobs using the configured provider

        Args:
            request: JobSearchRequest containing search parameters

        Returns:
            JobSearchResponse with search results

        Raises:
            SearchExecutionError: If there's an error executing the search
        """
        # Check cache first
        cache_key = self._get_cache_key(request)
        if cache_key in self._result_cache:
            logger.info(f"Cache hit for query: {request.query}")
            return self._result_cache[cache_key]

        try:
            logger.info(f"Searching jobs with provider {self.provider_name}: {request.query}")

            # Construct job-specific search query
            search_query = self._construct_search_query(request)

            # Create search request for the provider
            # Convert from the API model to the internal model
            search_request = BaseJobSearchRequest(
                query=search_query,
                num_results=request.num_results,
                job_title=request.query,
                location=request.location,
                job_type=request.job_type,
                experience_level=request.experience_level
            )

            # Perform search
            search_results = await self.search_service.search(search_request)

            # Convert JobSearchResult objects to JobResult objects
            job_results = [self._convert_to_job_result(result) for result in search_results]

            # Create response
            response = JobSearchResponse(
                results=job_results,
                total_results=len(job_results),
                search_query=request.query
            )

            # Cache the results
            self._result_cache[cache_key] = response

            return response

        except Exception as e:
            logger.error(f"Error searching jobs: {str(e)}")
            raise SearchExecutionError(f"Error searching jobs: {str(e)}")

    async def clear_cache(self):
        """Clear the search results cache"""
        self._result_cache.clear()
        logger.info("Search results cache cleared")

    async def cleanup(self):
        """Cleanup resources used by the search service"""
        try:
            await self.search_service.cleanup()
            logger.info(f"Cleaned up resources for provider: {self.provider_name}")
        except Exception as e:
            logger.error(f"Error cleaning up resources: {str(e)}")

    @classmethod
    def get_available_providers(cls) -> Dict[str, str]:
        """
        Get a dictionary of available providers with their descriptions

        Returns:
            Dictionary mapping provider names to descriptions
        """
        return {
            name: config["description"] 
            for name, config in cls.PROVIDERS.items()
        }
