from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, create_engine, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Trademark(Base):
    __tablename__ = 'trademarks'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    application_number = Column(String(50), unique=True, nullable=False)
    filing_date = Column(DateTime)
    status = Column(String(100))
    applicant_name = Column(String(255))
    applicant_address = Column(Text)
    trademark_name = Column(String(255))
    trademark_description = Column(Text)
    class_number = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    status_history = relationship("TrademarkStatusHistory", back_populates="trademark")

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

class Proxy(Base):
    __tablename__ = 'proxies'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255))
    password = Column(String(255))
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CrawlLog(Base):
    __tablename__ = 'crawl_logs'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    application_number = Column(String(50))
    status = Column(String(50))
    error_message = Column(Text)
    proxy_id = Column(Integer, ForeignKey('public.proxies.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    proxy = relationship("Proxy")