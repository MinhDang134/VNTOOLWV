import os
from dotenv import load_dotenv
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

@dataclass
class ProxyConfig:
    list: List[Dict[str, str]]
    username: str
    password: str
    max_requests: int

@dataclass
class CrawlerConfig:
    start_year: int
    y_start_value_new_year: str
    request_delay_ms: int
    max_requests_per_minute: int
    max_retries: int
    request_timeout: int
    batch_size: int

class Config:
    def __init__(self):
        load_dotenv()
        
        # Database configuration
        self.database = DatabaseConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            name=os.getenv('DB_NAME', 'wipo_vn'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )

        # Proxy configuration
        proxy_list = []
        for proxy in os.getenv('PROXY_LIST', '').split(','):
            if proxy.strip():
                host, port = proxy.strip().split(':')
                proxy_list.append({
                    'host': host,
                    'port': int(port)
                })

        self.proxy = ProxyConfig(
            list=proxy_list,
            username=os.getenv('PROXY_USERNAME', ''),
            password=os.getenv('PROXY_PASSWORD', ''),
            max_requests=int(os.getenv('MAX_REQUESTS_PER_PROXY', '20'))
        )

        # Crawler configuration
        self.crawler = CrawlerConfig(
            start_year=int(os.getenv('X_START_YEAR', '1984')),
            y_start_value_new_year=os.getenv('Y_START_VALUE_NEW_YEAR', '00002'),
            request_delay_ms=int(os.getenv('REQUEST_DELAY_MS', '50')),
            max_requests_per_minute=int(os.getenv('MAX_REQUESTS_PER_MINUTE', '1000')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30')),
            batch_size=int(os.getenv('BATCH_SIZE', '100'))
        )

        # Application settings
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.schedule_interval = int(os.getenv('SCHEDULE_INTERVAL', '3600'))
        self.prometheus_port = int(os.getenv('PROMETHEUS_PORT', '9090'))

    def get_database_url(self) -> str:
        """Get database URL for SQLAlchemy"""
        return f"postgresql://{self.database.user}:{self.database.password}@{self.database.host}:{self.database.port}/{self.database.name}"

    def get_proxy_url(self, proxy: Dict[str, str]) -> str:
        """Get proxy URL for requests"""
        return f"http://{self.proxy.username}:{self.proxy.password}@{proxy['host']}:{proxy['port']}"

    def get_proxy_list(self) -> List[str]:
        """Get list of proxies from environment variable"""
        return [p.strip() for p in os.getenv('PROXY_LIST', '').split(',') if p.strip()]

# Create global config instance
config = Config() 