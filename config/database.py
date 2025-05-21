import sqlite3
from typing import List, Optional
from datetime import datetime
import logging
from ..models import Trademark, Notification

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, config):
        self.db_path = config.db_path
        self.init_db()
        
    def init_db(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create trademarks table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trademarks (
                        number TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        filing_date TEXT NOT NULL,
                        registration_date TEXT,
                        owner TEXT NOT NULL,
                        owner_address TEXT NOT NULL,
                        classes TEXT NOT NULL,
                        description TEXT NOT NULL,
                        images TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # Create notifications table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trademark_number TEXT NOT NULL,
                        type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        is_read INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (trademark_number) REFERENCES trademarks (number)
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
            
    def add_trademark(self, trademark: Trademark):
        """Add a new trademark to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trademarks (
                        number, name, status, filing_date, registration_date,
                        owner, owner_address, classes, description, images,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trademark.number,
                    trademark.name,
                    trademark.status,
                    trademark.filing_date.isoformat(),
                    trademark.registration_date.isoformat() if trademark.registration_date else None,
                    trademark.owner,
                    trademark.owner_address,
                    ','.join(trademark.classes),
                    trademark.description,
                    ','.join(trademark.images),
                    trademark.created_at.isoformat(),
                    trademark.updated_at.isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error adding trademark: {str(e)}")
            raise
            
    def get_trademark(self, number: str) -> Optional[Trademark]:
        """Get trademark by number"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM trademarks WHERE number = ?', (number,))
                row = cursor.fetchone()
                
                if row:
                    return Trademark(
                        number=row[0],
                        name=row[1],
                        status=row[2],
                        filing_date=datetime.fromisoformat(row[3]),
                        registration_date=datetime.fromisoformat(row[4]) if row[4] else None,
                        owner=row[5],
                        owner_address=row[6],
                        classes=row[7].split(','),
                        description=row[8],
                        images=row[9].split(','),
                        created_at=datetime.fromisoformat(row[10]),
                        updated_at=datetime.fromisoformat(row[11])
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting trademark: {str(e)}")
            return None
            
    def update_trademark(self, trademark: Trademark):
        """Update existing trademark"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE trademarks SET
                        name = ?,
                        status = ?,
                        filing_date = ?,
                        registration_date = ?,
                        owner = ?,
                        owner_address = ?,
                        classes = ?,
                        description = ?,
                        images = ?,
                        updated_at = ?
                    WHERE number = ?
                ''', (
                    trademark.name,
                    trademark.status,
                    trademark.filing_date.isoformat(),
                    trademark.registration_date.isoformat() if trademark.registration_date else None,
                    trademark.owner,
                    trademark.owner_address,
                    ','.join(trademark.classes),
                    trademark.description,
                    ','.join(trademark.images),
                    datetime.now().isoformat(),
                    trademark.number
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating trademark: {str(e)}")
            raise
            
    def add_notification(self, notification: Notification):
        """Add a new notification"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notifications (
                        trademark_number, type, message, created_at, is_read
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    notification.trademark_number,
                    notification.type,
                    notification.message,
                    notification.created_at.isoformat(),
                    1 if notification.is_read else 0
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error adding notification: {str(e)}")
            raise
            
    def get_unread_notifications(self) -> List[Notification]:
        """Get all unread notifications"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM notifications 
                    WHERE is_read = 0 
                    ORDER BY created_at DESC
                ''')
                rows = cursor.fetchall()
                
                return [
                    Notification(
                        id=row[0],
                        trademark_number=row[1],
                        type=row[2],
                        message=row[3],
                        created_at=datetime.fromisoformat(row[4]),
                        is_read=bool(row[5])
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")
            return []
            
    def mark_notification_read(self, notification_id: int):
        """Mark a notification as read"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE notifications 
                    SET is_read = 1 
                    WHERE id = ?
                ''', (notification_id,))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            raise 