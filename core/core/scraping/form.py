from typing import Dict, Any
from bs4 import BeautifulSoup
from .base import BaseScrapingService

class FormScrapingService(BaseScrapingService):
    async def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape form fields from a page"""
        try:
            soup = await self.get_soup(url)
            form_fields = {}

            # Find all form elements
            for form in soup.find_all('form'):
                for field in form.find_all(['input', 'select', 'textarea']):
                    field_name = field.get('name') or field.get('id')
                    if field_name:
                        form_fields[field_name] = {
                            "type": field.get('type', 'text'),
                            "required": field.get('required', False),
                            "placeholder": field.get('placeholder', ''),
                            "options": [opt.get('value') for opt in field.find_all('option')] if field.name == 'select' else None
                        }

            return {
                "url": url,
                "form_fields": form_fields
            }
        except Exception as e:
            raise Exception(f"Error scraping form fields: {str(e)}")