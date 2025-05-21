from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import os
from dotenv import load_dotenv
from logs.logger import logger

load_dotenv()

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.schedule_interval = int(os.getenv('SCHEDULE_INTERVAL', 3600))

    def add_crawl_job(self, job_function):
        """Add crawl job to scheduler"""
        self.scheduler.add_job(
            job_function,
            trigger=IntervalTrigger(seconds=self.schedule_interval),
            id='crawl_job',
            name='WIPO Crawl Job',
            replace_existing=True
        )
        logger.info(f"Added crawl job with interval {self.schedule_interval} seconds")

    def add_monitor_job(self, job_function):
        """Add monitor job to scheduler"""
        self.scheduler.add_job(
            job_function,
            trigger=CronTrigger(hour='*/1'),  # Run every hour
            id='monitor_job',
            name='Trademark Monitor Job',
            replace_existing=True
        )
        logger.info("Added monitor job to run every hour")

    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")

# Create default scheduler
scheduler = TaskScheduler() 