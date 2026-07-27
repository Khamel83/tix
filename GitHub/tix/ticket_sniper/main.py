import asyncio
import logging
from ticket_sniper.scheduler.engine import start_scheduler

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    logging.info("Starting Ticket-Sniper Engine...")
    start_scheduler()
