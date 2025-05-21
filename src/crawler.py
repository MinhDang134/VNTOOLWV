import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time
from .models import Trademark
from .database import Database
from .config import Config
from .proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

class WIPOCrawler:
    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config)
        self.base_url = "https://publish.wipo.int"
        self.session = requests.Session()
        self.proxy_manager = ProxyManager.from_env(
            ','.join(config.get_proxy_list()),
            config.max_requests_per_proxy
        )
        
    def _make_request(self, url: str, params: Dict = None) -> Optional[requests.Response]:
        """Make HTTP request with proxy rotation"""
        max_retries = len(self.proxy_manager.proxy_list)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                proxy = self.proxy_manager.get_current_proxy()
                if proxy:
                    self.session.proxies = {
                        'http': proxy,
                        'https': proxy
                    }
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                self.proxy_manager.increment_request_count()
                return response
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed with proxy {self.proxy_manager.get_current_proxy()}: {str(e)}")
                self.proxy_manager.handle_proxy_error()
                retry_count += 1
                
        logger.error("All proxies failed")
        return None
        
    def search_trademarks(self, query: str, page: int = 1) -> List[Dict]:
        """Search trademarks on WIPO website"""
        try:
            url = f"{self.base_url}/search/trademarks"
            params = {
                "q": query,
                "page": page,
                "sort": "date_desc"
            }
            
            response = self._make_request(url, params)
            if not response:
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for item in soup.select('.search-result-item'):
                trademark = {
                    'name': item.select_one('.trademark-name').text.strip(),
                    'number': item.select_one('.trademark-number').text.strip(),
                    'status': item.select_one('.trademark-status').text.strip(),
                    'date': item.select_one('.trademark-date').text.strip(),
                    'owner': item.select_one('.trademark-owner').text.strip(),
                    'classes': [c.text.strip() for c in item.select('.trademark-class')]
                }
                results.append(trademark)
                
            return results
            
        except Exception as e:
            logger.error(f"Error searching trademarks: {str(e)}")
            return []
            
    def get_trademark_details(self, trademark_number: str) -> Optional[Dict]:
        """Get detailed information for a specific trademark"""
        try:
            url = f"{self.base_url}/trademark/{trademark_number}"
            response = self._make_request(url)
            if not response:
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            details = {
                'number': trademark_number,
                'name': soup.select_one('.trademark-name').text.strip(),
                'status': soup.select_one('.trademark-status').text.strip(),
                'filing_date': soup.select_one('.filing-date').text.strip(),
                'registration_date': soup.select_one('.registration-date').text.strip(),
                'owner': soup.select_one('.owner-name').text.strip(),
                'owner_address': soup.select_one('.owner-address').text.strip(),
                'classes': [c.text.strip() for c in soup.select('.trademark-class')],
                'description': soup.select_one('.trademark-description').text.strip(),
                'images': [img['src'] for img in soup.select('.trademark-image img')]
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting trademark details: {str(e)}")
            return None
            
    def monitor_trademarks(self):
        """Monitor new trademarks and update database"""
        try:
            # Get latest trademarks
            new_trademarks = self.search_trademarks("", page=1)
            
            for tm_data in new_trademarks:
                # Check if trademark exists
                existing = self.db.get_trademark(tm_data['number'])
                
                if not existing:
                    # Get full details
                    details = self.get_trademark_details(tm_data['number'])
                    if details:
                        # Create new trademark record
                        trademark = Trademark(
                            number=details['number'],
                            name=details['name'],
                            status=details['status'],
                            filing_date=datetime.strptime(details['filing_date'], '%Y-%m-%d'),
                            registration_date=datetime.strptime(details['registration_date'], '%Y-%m-%d') if details['registration_date'] else None,
                            owner=details['owner'],
                            owner_address=details['owner_address'],
                            classes=details['classes'],
                            description=details['description'],
                            images=details['images']
                        )
                        self.db.add_trademark(trademark)
                        logger.info(f"Added new trademark: {trademark.number}")
                        
        except Exception as e:
            logger.error(f"Error monitoring trademarks: {str(e)}")
            
    def run(self):
        """Run the crawler continuously"""
        while True:
            try:
                self.monitor_trademarks()
                time.sleep(self.config.crawler_interval)
            except Exception as e:
                logger.error(f"Crawler error: {str(e)}")
                time.sleep(60)  # Wait before retrying 