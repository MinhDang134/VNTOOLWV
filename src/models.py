from sqlalchemy import Column, Integer, String, Text, Date, DateTime, JSON, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import json

Base = declarative_base()

class Brand(Base):
    __tablename__ = 'brand'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Unique identifier and indexes
    original_application_number = Column(String(50), unique=True, index=True, nullable=False)
    
    # Brand information
    brand_name = Column(Text, nullable=False)
    label_sample_url = Column(Text, nullable=True)
    label_sample_base64 = Column(Text, nullable=True)
    trademark_text = Column(Text, nullable=True)
    
    # Dates
    filing_date = Column(Date, nullable=True, index=True)
    publication_date = Column(Date, nullable=True)
    grant_date = Column(Date, nullable=True)
    
    # Certificate information
    certificate_number = Column(String(100), nullable=True)
    
    # Owner information
    applicant_owner_name = Column(Text, nullable=True)
    applicant_owner_address = Column(Text, nullable=True)
    
    # Classification and status
    nice_classes = Column(JSONB, nullable=True)  # Using JSONB for PostgreSQL
    status = Column(String(255), nullable=True)
    
    # Metadata
    crawled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_checked_at = Column(DateTime, nullable=True)
    data_source = Column(String(50), default='WIPO_VN', nullable=False)
    
    # Additional indexes
    __table_args__ = (
        Index('idx_brand_dates', 'filing_date', 'publication_date', 'grant_date'),
        Index('idx_brand_status', 'status'),
        Index('idx_brand_owner', 'applicant_owner_name'),
    )
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'original_application_number': self.original_application_number,
            'brand_name': self.brand_name,
            'label_sample_url': self.label_sample_url,
            'label_sample_base64': self.label_sample_base64,
            'trademark_text': self.trademark_text,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'grant_date': self.grant_date.isoformat() if self.grant_date else None,
            'certificate_number': self.certificate_number,
            'applicant_owner_name': self.applicant_owner_name,
            'applicant_owner_address': self.applicant_owner_address,
            'nice_classes': self.nice_classes,
            'status': self.status,
            'crawled_at': self.crawled_at.isoformat(),
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'data_source': self.data_source
        } 