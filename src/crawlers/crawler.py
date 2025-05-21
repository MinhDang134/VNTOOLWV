import os

import requests
import time
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from src.crawlers.database import get_db
from src.crawlers.models import Trademark, TrademarkStatusHistory, CrawlLog
from proxy.proxy_manager import ProxyManager
from logs.logger import logger

class WIPOCrawler:
    def __init__(self):
        self.base_url = "https://publish.wipo.int"
        self.proxy_manager = ProxyManager()
        self.session = requests.Session()
        self.max_retries = int(os.getenv('MAX_RETRIES', 3))
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', 30))

    def _get_headers(self) -> Dict:
        """Get request headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with proxy rotation and retry logic"""
        for attempt in range(self.max_retries):
            try:
                proxy = self.proxy_manager.get_working_proxy()
                if not proxy:
                    logger.error("No working proxy available")
                    return None

                proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                kwargs['proxies'] = {'http': proxy_url, 'https': proxy_url}
                kwargs['headers'] = self._get_headers()
                kwargs['timeout'] = self.request_timeout

                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                self.proxy_manager.update_proxy_status(proxy, False)
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff

    def get_trademark_details(self, application_number: str) -> Optional[Dict]:
        """Get trademark details from WIPO"""
        url = f"{self.base_url}/api/trademark/{application_number}"
        response = self._make_request(url)
        
        if not response:
            return None

        try:
            data = response.json()
            return {
                'application_number': application_number,
                'filing_date': datetime.strptime(data['filingDate'], '%Y-%m-%d'),
                'status': data['status'],
                'applicant_name': data['applicant']['name'],
                'applicant_address': data['applicant']['address'],
                'trademark_name': data['trademarkName'],
                'trademark_description': data['description'],
                'class_number': data['classNumber']
            }
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing trademark data: {str(e)}")
            return None

    def save_trademark(self, trademark_data: Dict, db: Session):
        """Save trademark data to database"""
        try:
            # Check if trademark exists
            existing_trademark = db.query(Trademark).filter(
                Trademark.application_number == trademark_data['application_number']
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
            logger.info(f"Saved trademark {trademark_data['application_number']}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving trademark: {str(e)}")
            raise

    def crawl_trademarks(self, start_number: int, end_number: int):
        """Crawl trademarks in range"""
        db = next(get_db())
        
        for app_number in range(start_number, end_number + 1):
            try:
                app_number_str = str(app_number).zfill(8)
                trademark_data = self.get_trademark_details(app_number_str)
                
                if trademark_data:
                    self.save_trademark(trademark_data, db)
                
                # Log crawl attempt
                crawl_log = CrawlLog(
                    application_number=app_number_str,
                    status='SUCCESS' if trademark_data else 'FAILED',
                    error_message=None if trademark_data else 'No data found'
                )
                db.add(crawl_log)
                db.commit()

            except Exception as e:
                logger.error(f"Error crawling trademark {app_number}: {str(e)}")
                db.rollback()
                continue

            time.sleep(1)  # Rate limiting 