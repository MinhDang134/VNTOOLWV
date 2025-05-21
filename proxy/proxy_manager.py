import random
import requests
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from src.crawlers.models import Proxy
from src.crawlers.database import get_db
from config.config import config
from logs.logger import logger


class ProxyManager:
    def __init__(self):
        self.proxies: List[Dict] = []
        self.current_proxy_index = 0
        self.proxy_request_count = {}  # Track request count per proxy
        self.current_proxy = None
        self.load_proxies()

    def load_proxies(self):
        """Load proxies from environment variables and database"""
        # Load from config
        for proxy in config.proxy.list:
            self.proxies.append({
                'host': proxy['host'],
                'port': proxy['port'],
                'username': config.proxy.username,
                'password': config.proxy.password
            })

        # Load from database
        db = next(get_db())
        db_proxies = db.query(Proxy).filter(Proxy.is_active == True).all()
        for proxy in db_proxies:
            self.proxies.append({
                'host': proxy.host,
                'port': proxy.port,
                'username': proxy.username,
                'password': proxy.password
            })

        if self.proxies:
            self.current_proxy = self.proxies[0]
        logger.info(f"Loaded {len(self.proxies)} proxies")

    def get_next_proxy(self) -> Optional[Dict]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None

        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        self.current_proxy = self.proxies[self.current_proxy_index]
        self.proxy_request_count = {}  # Reset request count when switching proxies
        logger.info(f"Switching to next proxy: {self.current_proxy['host']}:{self.current_proxy['port']}")
        return self.current_proxy

    def get_random_proxy(self) -> Optional[Dict]:
        """Get random proxy from the list"""
        if not self.proxies:
            return None
        self.current_proxy = random.choice(self.proxies)
        return self.current_proxy

    def get_current_proxy(self) -> Optional[Dict]:
        """Get current proxy"""
        return self.current_proxy

    def test_proxy(self, proxy: Dict) -> bool:
        """Test if proxy is working"""
        try:
            proxy_url = config.get_proxy_url(proxy)
            response = requests.get(
                'https://publish.wipo.int',
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=config.crawler.request_timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Proxy {proxy['host']}:{proxy['port']} test failed: {str(e)}")
            return False

    def update_proxy_status(self, proxy: Dict, is_working: bool):
        """Update proxy status in database"""
        db = next(get_db())
        db_proxy = db.query(Proxy).filter(
            Proxy.host == proxy['host'],
            Proxy.port == proxy['port']
        ).first()

        if db_proxy:
            db_proxy.is_active = is_working
            db_proxy.last_used = datetime.utcnow()
            db.commit()

    def increment_request_count(self):
        """Increment request count for current proxy"""
        if not self.current_proxy:
            return
            
        proxy_key = f"{self.current_proxy['host']}:{self.current_proxy['port']}"
        self.proxy_request_count[proxy_key] = self.proxy_request_count.get(proxy_key, 0) + 1
        
        if self.proxy_request_count[proxy_key] >= config.proxy.max_requests:
            old_proxy = self.current_proxy
            self.get_next_proxy()
            logger.info(f"Proxy {old_proxy['host']}:{old_proxy['port']} reached max requests ({config.proxy.max_requests}). Switching to {self.current_proxy['host']}:{self.current_proxy['port']}")

    def handle_proxy_error(self):
        """Handle proxy error by switching to next proxy"""
        if not self.current_proxy:
            return
            
        old_proxy = self.current_proxy
        self.get_next_proxy()
        logger.warning(f"Proxy {old_proxy['host']}:{old_proxy['port']} encountered an error. Switching to {self.current_proxy['host']}:{self.current_proxy['port']}")

    def get_working_proxy(self) -> Optional[Dict]:
        """Get a working proxy"""
        for _ in range(len(self.proxies)):
            proxy = self.get_next_proxy()
            if self.test_proxy(proxy):
                self.update_proxy_status(proxy, True)
                return proxy
            self.update_proxy_status(proxy, False)
        return None 