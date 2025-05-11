from abc import ABC, abstractmethod
from typing import Dict, Any
from bs4 import BeautifulSoup
import requests
from ..config.settings import get_settings

class BaseScrapingService(ABC):
    def __init__(self):
        self.settings = get_settings()

    @abstractmethod
    async def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape content from a URL"""
        pass

    async def get_page_content(self, url: str) -> str:
        """Get raw page content"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        except Exception as e:
            raise Exception(f"Error scraping content: {str(e)}")

    async def get_soup(self, url: str) -> BeautifulSoup:
        """Get BeautifulSoup object for parsing"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            raise Exception(f"Error getting page: {str(e)}")