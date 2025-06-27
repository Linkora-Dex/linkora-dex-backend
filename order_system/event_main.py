#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2025 Linkora DEX
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing, contact: licensing@linkora.info

import asyncio
import logging
import signal
import sys
import time
from database import DatabaseManager
from event_processor import EventProcessor
from config import DB_CONFIG

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class EventService:
    def __init__(self):
        self.db_manager = None
        self.event_processor = None
        self.shutdown_event = asyncio.Event()
        self.start_time = time.time()

    async def start(self):
        logging.info("Starting Event Processor Service...")

        try:
            await self._init_database()
            await self._init_event_processor()
        except Exception as e:
            logging.critical(f"Failed to initialize services: {e}")
            raise

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        tasks = [
            asyncio.create_task(self.event_processor.start()),
            asyncio.create_task(self._cache_cleanup_task()),
            asyncio.create_task(self._heartbeat_task()),
            asyncio.create_task(self._wait_for_shutdown())
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(f"Event service error: {e}")
        finally:
            await self.cleanup()

    async def _init_database(self):
        logging.info("Initializing database connection...")
        try:
            self.db_manager = DatabaseManager(DB_CONFIG)
            await self.db_manager.init_pool()

            async with self.db_manager.transaction() as tx:
                await tx.fetchval("SELECT 1")

            logging.info("✅ Database connection established successfully")
        except Exception as e:
            logging.error(f"❌ Database connection failed: {e}")
            raise

    async def _init_event_processor(self):
        logging.info("Initializing event processor...")
        try:
            self.event_processor = EventProcessor(self.db_manager)
            await self.event_processor.test_connections()
            logging.info("✅ Event processor initialized successfully")
        except Exception as e:
            logging.error(f"❌ Event processor initialization failed: {e}")
            raise

    async def _cache_cleanup_task(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(3600)
            if self.event_processor:
                self.event_processor.clear_cache()
                logging.info("🧹 Cache cleanup completed")

    async def _heartbeat_task(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(300)
            if self.event_processor:
                uptime = time.time() - self.start_time
                uptime_hours = uptime / 3600
                current_block = self.event_processor.last_processed_block
                logging.info(f"💓 HEARTBEAT: Uptime {uptime_hours:.1f}h, Current block: {current_block}")

    async def _wait_for_shutdown(self):
        await self.shutdown_event.wait()

    def _signal_handler(self, signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        self.shutdown_event.set()

    async def cleanup(self):
        logging.info("Starting cleanup process...")
        if self.db_manager:
            await self.db_manager.close()
            logging.info("Database connection closed")
        logging.info("Event service shutdown completed")


async def main():
    service = EventService()
    try:
        await service.start()
    except Exception as e:
        logging.error(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())