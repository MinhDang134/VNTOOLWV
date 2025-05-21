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

        logger.info(f"Loaded {len(self.proxies)} proxies")

    def get_next_proxy(self) -> Optional[Dict]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy

    def get_random_proxy(self) -> Optional[Dict]:
        """Get random proxy from the list"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

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
        except:
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

    def increment_proxy_request_count(self, proxy: Dict):
        """Increment request count for proxy"""
        proxy_key = f"{proxy['host']}:{proxy['port']}"
        self.proxy_request_count[proxy_key] = self.proxy_request_count.get(proxy_key, 0) + 1

    def should_rotate_proxy(self, proxy: Dict) -> bool:
        """Check if proxy should be rotated based on request count"""
        proxy_key = f"{proxy['host']}:{proxy['port']}"
        return self.proxy_request_count.get(proxy_key, 0) >= config.proxy.max_requests

    def get_working_proxy(self) -> Optional[Dict]:
        """Get a working proxy"""
        for _ in range(len(self.proxies)):
            proxy = self.get_next_proxy()

            # Check if proxy needs rotation
            if self.should_rotate_proxy(proxy):
                logger.info(f"Rotating proxy {proxy['host']}:{proxy['port']} due to max requests")
                continue

            if self.test_proxy(proxy):
                self.update_proxy_status(proxy, True)
                self.increment_proxy_request_count(proxy)
                return proxy
            self.update_proxy_status(proxy, False)
        return None 