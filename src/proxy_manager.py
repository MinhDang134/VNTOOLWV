import json
import logging
from typing import List, Optional
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self, proxy_list: List[str], max_requests: int = 20):
        self.proxy_list = proxy_list
        self.max_requests = max_requests
        self.current_proxy_index = 0
        self.request_count = 0
        self.current_proxy = self.proxy_list[0] if proxy_list else None
        
    def get_next_proxy(self) -> str:
        """Get next proxy in rotation"""
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        self.current_proxy = self.proxy_list[self.current_proxy_index]
        self.request_count = 0
        logger.info(f"Switching to next proxy: {self.current_proxy}")
        return self.current_proxy
        
    def get_current_proxy(self) -> Optional[str]:
        """Get current proxy"""
        return self.current_proxy
        
    def increment_request_count(self):
        """Increment request count for current proxy"""
        self.request_count += 1
        if self.request_count >= self.max_requests:
            old_proxy = self.current_proxy
            self.get_next_proxy()
            logger.info(f"Proxy {old_proxy} reached max requests ({self.max_requests}). Switching to {self.current_proxy}")
            
    def test_proxy(self, proxy: str, timeout: int = 10) -> bool:
        """Test if proxy is working"""
        try:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            response = requests.get('https://publish.wipo.int', 
                                 proxies=proxies, 
                                 timeout=timeout)
            return response.status_code == 200
        except RequestException as e:
            logger.error(f"Proxy {proxy} test failed: {str(e)}")
            return False
            
    def handle_proxy_error(self):
        """Handle proxy error by switching to next proxy"""
        old_proxy = self.current_proxy
        self.get_next_proxy()
        logger.warning(f"Proxy {old_proxy} encountered an error. Switching to {self.current_proxy}")
        
    @classmethod
    def from_env(cls, proxy_list_str: str, max_requests: int = 20) -> 'ProxyManager':
        """Create ProxyManager from environment variable string"""
        try:
            # Remove any whitespace and split by comma
            proxy_list = [p.strip() for p in proxy_list_str.split(',')]
            return cls(proxy_list, max_requests)
        except Exception as e:
            logger.error(f"Error parsing proxy list: {str(e)}")
            return cls([], max_requests) 