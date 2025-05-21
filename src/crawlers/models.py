from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()
class Brand(Base):
    __tablename__ = 'brand'

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_application_number = Column(String(50), unique=True, nullable=False)
    brand_name = Column(Text, nullable=False)
    label_sample_url = Column(Text, nullable=True)
    filing_date = Column(Date, nullable=True)
    publication_date = Column(Date, nullable=True)
    applicant_owner_name = Column(Text, nullable=True)
    applicant_owner_address = Column(Text, nullable=True)
    status = Column(String(255), nullable=True)

    # Metadata
    crawled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    data_source = Column(String(50), default='WIPO_VN', nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'original_application_number': self.original_application_number,
            'brand_name': self.brand_name,
            'label_sample_url': self.label_sample_url,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'applicant_owner_name': self.applicant_owner_name,
            'applicant_owner_address': self.applicant_owner_address,
            'status': self.status,
            'crawled_at': self.crawled_at.isoformat(),
            'data_source': self.data_source
        }

class TrademarkStatusHistory(Base):
    __tablename__ = 'trademark_status_history'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    trademark_id = Column(Integer, ForeignKey('public.trademarks.id'))
    status = Column(String(100))
    status_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trademark = relationship("Trademark", back_populates="status_history")

class CrawlLog(Base):
    __tablename__ = 'crawl_logs'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    trademark_id = Column(Integer, ForeignKey('public.trademarks.id'))
    trademark_code = Column(String(50))
    step = Column(String(50))  # validate, fetch_data
    status = Column(String(50))  # success, failed
    error_code = Column(String(50))
    error_message = Column(Text)
    response_data = Column(JSON)
    proxy_id = Column(Integer, ForeignKey('public.proxies.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trademark = relationship("Trademark", back_populates="crawl_logs")
    proxy = relationship("Proxy")

class Proxy(Base):
    __tablename__ = 'proxies'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255))
    password = Column(String(255))
    is_active = Column(Boolean, default=True)
    request_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Cookie(Base):
    __tablename__ = 'cookies'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    psusr = Column(String(255))
    jsessionid = Column(String(255))
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)