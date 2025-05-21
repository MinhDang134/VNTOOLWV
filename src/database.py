from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import logging
from typing import Optional, List
from .models import Base, Brand
from .config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, config: Config):
        self.engine = create_engine(config.get_database_url())
        self.Session = sessionmaker(bind=self.engine)
        self.config = config
        
    def init_db(self):
        """Initialize database and create tables"""
        Base.metadata.create_all(self.engine)
        self._setup_partitions()
        
    def _setup_partitions(self):
        """Setup table partitions for the next 12 months"""
        try:
            with self.engine.connect() as conn:
                # Create partition function if not exists
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION create_brand_partition()
                    RETURNS trigger AS $$
                    DECLARE
                        partition_date TEXT;
                        partition_name TEXT;
                    BEGIN
                        partition_date := to_char(NEW.filing_date, 'YYYY_MM');
                        partition_name := 'brand_' || partition_date;
                        
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE c.relname = partition_name
                            AND n.nspname = 'public'
                        ) THEN
                            EXECUTE format(
                                'CREATE TABLE %I (LIKE brand INCLUDING ALL) INHERITS (brand)',
                                partition_name
                            );
                            
                            -- Add partition-specific indexes
                            EXECUTE format(
                                'CREATE INDEX %I ON %I (filing_date)',
                                partition_name || '_filing_date_idx',
                                partition_name
                            );
                        END IF;
                        
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Create trigger if not exists
                conn.execute(text("""
                    DROP TRIGGER IF EXISTS brand_partition_trigger ON brand;
                    CREATE TRIGGER brand_partition_trigger
                        BEFORE INSERT ON brand
                        FOR EACH ROW
                        EXECUTE FUNCTION create_brand_partition();
                """))
                
                # Create partitions for next 12 months
                current_date = datetime.now()
                for i in range(12):
                    partition_date = current_date + timedelta(days=30*i)
                    partition_name = f"brand_{partition_date.strftime('%Y_%m')}"
                    
                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {partition_name} (
                            LIKE brand INCLUDING ALL
                        ) INHERITS (brand);
                        
                        CREATE INDEX IF NOT EXISTS {partition_name}_filing_date_idx 
                        ON {partition_name} (filing_date);
                    """))
                    
                conn.commit()
                logger.info("Successfully set up table partitions")
                
        except Exception as e:
            logger.error(f"Error setting up partitions: {str(e)}")
            raise
            
    def add_brand(self, brand: Brand) -> Optional[Brand]:
        """Add a new brand to database"""
        try:
            with self.Session() as session:
                session.add(brand)
                session.commit()
                return brand
        except Exception as e:
            logger.error(f"Error adding brand: {str(e)}")
            return None
            
    def get_brand(self, application_number: str) -> Optional[Brand]:
        """Get brand by application number"""
        try:
            with self.Session() as session:
                return session.query(Brand).filter_by(
                    original_application_number=application_number
                ).first()
        except Exception as e:
            logger.error(f"Error getting brand: {str(e)}")
            return None
            
    def update_brand(self, brand: Brand) -> bool:
        """Update existing brand"""
        try:
            with self.Session() as session:
                session.merge(brand)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating brand: {str(e)}")
            return False
            
    def get_brands_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Brand]:
        """Get brands within date range"""
        try:
            with self.Session() as session:
                return session.query(Brand).filter(
                    Brand.filing_date >= start_date,
                    Brand.filing_date <= end_date
                ).all()
        except Exception as e:
            logger.error(f"Error getting brands by date range: {str(e)}")
            return []
            
    def get_brands_by_status(self, status: str) -> List[Brand]:
        """Get brands by status"""
        try:
            with self.Session() as session:
                return session.query(Brand).filter_by(status=status).all()
        except Exception as e:
            logger.error(f"Error getting brands by status: {str(e)}")
            return []
            
    def get_brands_by_owner(self, owner_name: str) -> List[Brand]:
        """Get brands by owner name"""
        try:
            with self.Session() as session:
                return session.query(Brand).filter(
                    Brand.applicant_owner_name.ilike(f"%{owner_name}%")
                ).all()
        except Exception as e:
            logger.error(f"Error getting brands by owner: {str(e)}")
            return [] 