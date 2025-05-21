from dotenv import load_dotenv
from src.crawlers.crawler import WIPOCrawler
from schedules.scheduler import scheduler
from logs.logger import logger
from src.crawlers.database import engine, get_db
from src.crawlers.models import Base, Trademark


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

def crawl_job():
    """Job to crawl new trademarks"""
    try:
        crawler = WIPOCrawler()
        # Get last crawled number from database or start from 1
        start_number = 1  # TODO: Implement getting last crawled number
        end_number = start_number + 100  # Crawl 100 trademarks per job
        crawler.crawl_trademarks(start_number, end_number)
    except Exception as e:
        logger.error(f"Error in crawl job: {str(e)}")

def monitor_job():
    """Job to monitor pending trademarks"""
    try:
        crawler = WIPOCrawler()
        db = next(get_db())
        pending_trademarks = db.query(Trademark).filter(
            Trademark.status == 'PENDING'
        ).all()

        for trademark in pending_trademarks:
            try:
                trademark_data = crawler.get_trademark_details(trademark.application_number)
                if trademark_data and trademark_data['status'] != trademark.status:
                    crawler.save_trademark(trademark_data, db)
            except Exception as e:
                logger.error(f"Error monitoring trademark {trademark.application_number}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error in monitor job: {str(e)}")

def main():
    """Main function to start the application"""
    try:
        # Load environment variables
        load_dotenv()

        # Initialize database
        init_db()

        # Add jobs to scheduler
        scheduler.add_crawl_job(crawl_job)
        scheduler.add_monitor_job(monitor_job)

        # Start scheduler
        scheduler.start()

        # Keep the main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
