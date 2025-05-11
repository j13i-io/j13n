from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, urljoin
from .base import BaseScrapingService

class JobScrappingService(BaseScrapingService):
    # Common job board domains and their job posting URL patterns
    JOB_BOARDS = {
        'linkedin.com': {
            'job_pattern': '/jobs/view/',
            'content_selector': '.job-description',
            'title_selector': '.job-details-jobs-unified-top-card__job-title',
            'company_selector': '.job-details-jobs-unified-top-card__company-name'
        },
        'indeed.com': {
            'job_pattern': '/job/',
            'content_selector': '.jobsearch-jobDescriptionText',
            'title_selector': '.jobsearch-JobInfoHeader-title',
            'company_selector': '.jobsearch-CompanyInfoContainer'
        },
        'glassdoor.com': {
            'job_pattern': '/Job/',
            'content_selector': '.jobDescriptionContent',
            'title_selector': '.job-title',
            'company_selector': '.employer-name'
        }
    }

    async def validate_job_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate if URL is a job posting and get the actual job posting URL"""
        try:
            # Follow redirects to get the final URL
            response = requests.get(url, allow_redirects=True)
            final_url = response.url

            # Parse the URL
            parsed_url = urlparse(final_url)
            domain = parsed_url.netloc.lower()

            # Check if it's a known job board
            for job_board, patterns in self.JOB_BOARDS.items():
                if job_board in domain:
                    # Check if it matches the job posting pattern
                    if patterns['job_pattern'] in final_url:
                        return True, final_url

            # If not a known job board, try to detect if it's a job posting
            soup = BeautifulSoup(response.text, 'html.parser')

            # Common job posting indicators
            job_indicators = [
                'job', 'career', 'position', 'vacancy', 'opening',
                'apply', 'application', 'requirements', 'qualifications'
            ]

            text_content = soup.get_text().lower()
            if any(indicator in text_content for indicator in job_indicators):
                return True, final_url

            return False, None

        except Exception as e:
            raise Exception(f"Error validating job URL: {str(e)}")

    async def get_job_details(self, url: str, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract job details from the page"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # Try to get selectors for known job boards
        selectors = None
        for job_board, patterns in self.JOB_BOARDS.items():
            if job_board in domain:
                selectors = patterns
                break

        details = {}
        if selectors:
            # Extract using known selectors
            if selectors['title_selector']:
                title_elem = soup.select_one(selectors['title_selector'])
                if title_elem:
                    details['title'] = title_elem.get_text(strip=True)

            if selectors['company_selector']:
                company_elem = soup.select_one(selectors['company_selector'])
                if company_elem:
                    details['company'] = company_elem.get_text(strip=True)

            if selectors['content_selector']:
                content_elem = soup.select_one(selectors['content_selector'])
                if content_elem:
                    details['content'] = content_elem.get_text(strip=True)
        else:
            # Generic extraction for unknown job boards
            # Look for common job posting elements
            title_candidates = soup.find_all(['h1', 'h2', 'h3'])
            for title in title_candidates:
                if any(keyword in title.get_text().lower() for keyword in ['job', 'position', 'career']):
                    details['title'] = title.get_text(strip=True)
                    break

            # Try to find company name
            company_candidates = soup.find_all(['div', 'span'], class_=lambda x: x and any(word in str(x).lower() for word in ['company', 'employer', 'organization']))
            if company_candidates:
                details['company'] = company_candidates[0].get_text(strip=True)

            # Get main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=lambda x: x and any(word in str(x).lower() for word in ['content', 'main', 'body']))
            if main_content:
                details['content'] = main_content.get_text(strip=True)

        return details

    async def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape job posting content"""
        try:
            # First validate if it's a job posting
            is_job, final_url = await self.validate_job_url(url)
            if not is_job:
                raise Exception("URL does not appear to be a job posting")

            # Get the page content
            soup = await self.get_soup(final_url)

            # Extract job details
            job_details = await self.get_job_details(final_url, soup)

            if not job_details.get('content'):
                # Fallback to basic content extraction if specific selectors didn't work
                job_details['content'] = soup.get_text(separator='\n', strip=True)

            return {
                "url": final_url,
                "is_job_posting": True,
                **job_details
            }
        except Exception as e:
            raise Exception(f"Error scraping job posting: {str(e)}")