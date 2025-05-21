import os
import random
import requests
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from src.crawlers.models import Proxy
from src.crawlers.database import get_db

class ProxyManager:
    def __init__(self):
        self.proxies: List[Dict] = []
        self.current_proxy_index = 0
        self.load_proxies()

    def load_proxies(self):
        """Load proxies from environment variables and database"""
        # Load from environment variables
        proxy_list = os.getenv('PROXY_LIST', '').split(',')
        proxy_username = os.getenv('PROXY_USERNAME', '')
        proxy_password = os.getenv('PROXY_PASSWORD', '')

        for proxy in proxy_list:
            if proxy.strip():
                host, port = proxy.strip().split(':')
                self.proxies.append({
                    'host': host,
                    'port': int(port),
                    'username': proxy_username,
                    'password': proxy_password
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
            proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
            response = requests.get(
                'https://publish.wipo.int',
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=10
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

    def get_working_proxy(self) -> Optional[Dict]:
        """Get a working proxy"""
        for _ in range(len(self.proxies)):
            proxy = self.get_next_proxy()
            if self.test_proxy(proxy):
                self.update_proxy_status(proxy, True)
                return proxy
            self.update_proxy_status(proxy, False)
        return None 