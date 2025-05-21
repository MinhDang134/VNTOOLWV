import os
import time
import json
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List, Tuple
from datetime import datetime

import requests
from sqlalchemy.orm import Session
from src.crawlers.database import get_db
from src.crawlers.models import Trademark, TrademarkStatusHistory, CrawlLog, Cookie
from proxy.proxy_manager import ProxyManager
from logs.logger import logger
from config.config import config


class WIPOCrawler:
    def __init__(self):
        self.base_url = "https://wipopublish.ipvietnam.gov.vn/wopublish-search/public/trademarks"
        self.proxy_manager = ProxyManager()
        self.session = requests.Session()
        self.request_count = 0
        self.last_request_time = datetime.now()
        self.load_cookies()

    def load_cookies(self):
        """Load active cookies from database"""
        db = next(get_db())
        active_cookie = db.query(Cookie).filter(Cookie.is_active == True).first()
        if active_cookie:
            self.session.cookies.update({
                'psusr': active_cookie.psusr,
                'JSESSIONID': active_cookie.jsessionid
            })

    def _get_headers(self) -> Dict:
        """Get request headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = datetime.now()
        time_diff = (current_time - self.last_request_time).total_seconds()

        if time_diff < 60 and self.request_count >= config.crawler.max_requests_per_minute:
            sleep_time = 60 - time_diff
            logger.info(f"Rate limit reached. Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)
            self.request_count = 0
            self.last_request_time = datetime.now()
        elif time_diff >= 60:
            self.request_count = 0
            self.last_request_time = current_time

    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with rate limiting and proxy rotation"""
        self._check_rate_limit()

        for attempt in range(config.crawler.max_retries):
            try:
                proxy = self.proxy_manager.get_working_proxy()
                if not proxy:
                    logger.error("No working proxy available")
                    return None

                proxy_url = config.get_proxy_url(proxy)
                kwargs['proxies'] = {'http': proxy_url, 'https': proxy_url}
                kwargs['headers'] = self._get_headers()
                kwargs['timeout'] = config.crawler.request_timeout

                response = self.session.request(method, url, **kwargs)
                self.request_count += 1

                # Check for cookie expiration
                if response.status_code in [401, 403]:
                    logger.error("Cookie expired. Need manual update.")
                    return None

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                self.proxy_manager.update_proxy_status(proxy, False)
                if attempt == config.crawler.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff

    def validate_trademark_code(self, term: str) -> bool:
        """Validate trademark code (Step 1)"""
        url = f"{self.base_url}?10-1.IBehaviorListener.0-body-advancedSearchTab-advancedSearchInputPanel-advancedSearchForm-advancedInputWrapper-advancedInputsList-1-advancedInputSearchPanel-input&query=*:*&term={term}"

        response = self._make_request(url)
        if not response:
            return False

        try:
            data = response.json()
            return bool(data and isinstance(data, list) and len(data) > 0 and data[0].get('value') == term)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing validate response for {term}: {str(e)}")
            return False

    def fetch_trademark_data(self, term: str) -> Optional[Dict]:
        """Fetch trademark data (Step 2)"""
        url = f"{self.base_url}?10-1.IBehaviorListener.0-body-basicSearchTab-searchInputPanel-searchForm-searchSubmitLink&query=*:*"
        data = {
            'searchSubmitLink': '1',
            'autoCompleteFieldValue': f'(AFNB_ORI:({term}))'
        }

        response = self._make_request(url, method='POST', data=data)
        if not response:
            return None

        try:
            # Parse XML response
            root = ET.fromstring(response.text)
            # TODO: Implement XML parsing logic based on actual response structure
            return {
                'trademark_code': term,
                'trademark_name': '',  # Extract from XML
                'trademark_image': '',  # Extract from XML
                'trademark_text': '',  # Extract from XML
                'filing_date': None,  # Extract from XML
                'publication_date': None,  # Extract from XML
                'registration_number': '',  # Extract from XML
                'registration_date': None,  # Extract from XML
                'applicant_name': '',  # Extract from XML
                'applicant_address': '',  # Extract from XML
                'nice_class': '',  # Extract from XML
                'nice_description': '',  # Extract from XML
                'status': '',  # Extract from XML
                'raw_data': response.text
            }
        except ET.ParseError as e:
            logger.error(f"Error parsing XML response for {term}: {str(e)}")
            return None

    def save_trademark(self, trademark_data: Dict, db: Session):
        """Save trademark data to database"""
        try:
            # Check if trademark exists
            existing_trademark = db.query(Trademark).filter(
                Trademark.trademark_code == trademark_data['trademark_code']
            ).first()

            if existing_trademark:
                # Update existing trademark
                for key, value in trademark_data.items():
                    setattr(existing_trademark, key, value)
                existing_trademark.updated_at = datetime.utcnow()
            else:
                # Create new trademark
                new_trademark = Trademark(**trademark_data)
                db.add(new_trademark)
                existing_trademark = new_trademark

            # Add status history
            status_history = TrademarkStatusHistory(
                trademark_id=existing_trademark.id,
                status=trademark_data['status'],
                status_date=datetime.utcnow()
            )
            db.add(status_history)

            db.commit()
            logger.info(f"Saved trademark {trademark_data['trademark_code']}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving trademark: {str(e)}")
            raise

    def crawl_trademark(self, year: int, sequence: int) -> Tuple[bool, Optional[Dict]]:
        """Crawl single trademark"""
        term = f"VN-4-{year}-{str(sequence).zfill(5)}"
        logger.info(f"Processing trademark {term}")

        # Step 1: Validate trademark code
        if not self.validate_trademark_code(term):
            logger.info(f"Trademark {term} not found or validation failed")
            return False, None

        # Step 2: Fetch trademark data
        trademark_data = self.fetch_trademark_data(term)
        if not trademark_data:
            logger.error(f"Failed to fetch data for trademark {term}")
            return False, None

        return True, trademark_data

    def crawl_year(self, year: int):
        """Crawl all trademarks for a given year"""
        logger.info(f"Starting crawl for year {year}")
        db = next(get_db())
        sequence = int(config.crawler.y_start_value_new_year)
        success_count = 0

        while True:
            success, trademark_data = self.crawl_trademark(year, sequence)

            if not success:
                # If validation fails, assume we've reached the end of the year
                break

            if trademark_data:
                self.save_trademark(trademark_data, db)
                success_count += 1

            sequence += 1
            time.sleep(config.crawler.request_delay_ms / 1000)  # Convert ms to seconds

        logger.info(f"Completed crawl for year {year}. Total trademarks processed: {success_count}")
        return success_count 