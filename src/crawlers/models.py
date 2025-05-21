from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Trademark(Base):
    __tablename__ = 'trademarks'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    trademark_code = Column(String(50), unique=True, nullable=False)  # VN-4-XXXX-YYYYY
    trademark_name = Column(String(255))
    trademark_image = Column(Text)  # Base64 or URL
    trademark_text = Column(Text)
    filing_date = Column(DateTime)
    publication_date = Column(DateTime)
    registration_number = Column(String(50))
    registration_date = Column(DateTime)
    applicant_name = Column(String(255))
    applicant_address = Column(Text)
    nice_class = Column(String(50))
    nice_description = Column(Text)
    status = Column(String(100))
    raw_data = Column(JSON)  # Store complete XML response
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    status_history = relationship("TrademarkStatusHistory", back_populates="trademark")
    crawl_logs = relationship("CrawlLog", back_populates="trademark")

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