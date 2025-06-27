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
import aiohttp
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
import config

logger = logging.getLogger(__name__)


class OrderBookCollector:
    def __init__(self, db_manager, redis_manager):
        self.db = db_manager
        self.redis = redis_manager
        self.session = None

    async def create_session(self):
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def fetch_orderbook(self, symbol: str) -> Optional[Dict]:
        url = f"{config.BINANCE_BASE_URL}/api/v3/depth"
        params = {
            'symbol': symbol,
            'limit': config.ORDERBOOK_LEVELS
        }

        for attempt in range(config.ORDERBOOK_MAX_RETRIES):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.process_orderbook_data(symbol, data)
                    elif response.status == 429:
                        wait_time = config.ORDERBOOK_RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"Rate limit hit for {symbol} orderbook, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"HTTP {response.status} for {symbol} orderbook")
                        await asyncio.sleep(config.ORDERBOOK_RETRY_DELAY)
            except Exception as e:
                logger.error(f"Orderbook request failed for {symbol} (attempt {attempt + 1}): {e}")
                if attempt < config.ORDERBOOK_MAX_RETRIES - 1:
                    await asyncio.sleep(config.ORDERBOOK_RETRY_DELAY * (2 ** attempt))

        return None

    def process_orderbook_data(self, symbol: str, data: Dict) -> Dict:
        try:
            timestamp = int(time.time() * 1000)

            processed_bids = []
            for bid in data['bids']:
                processed_bids.append({
                    'price': str(Decimal(bid[0])),
                    'quantity': str(Decimal(bid[1]))
                })

            processed_asks = []
            for ask in data['asks']:
                processed_asks.append({
                    'price': str(Decimal(ask[0])),
                    'quantity': str(Decimal(ask[1]))
                })

            orderbook = {
                'symbol': symbol,
                'timestamp': timestamp,
                'last_update_id': data['lastUpdateId'],
                'bids': processed_bids,
                'asks': processed_asks
            }

            logger.debug(f"Processed orderbook for {symbol}: {len(processed_bids)} bids, {len(processed_asks)} asks")
            return orderbook

        except Exception as e:
            logger.error(f"Error processing orderbook data for {symbol}: {e}")
            return None

    async def collect_orderbook_data(self, symbol: str):
        logger.info(f"Starting orderbook collection for {symbol}")

        while True:
            try:
                orderbook = await self.fetch_orderbook(symbol)
                if orderbook:
                    # Используем await для асинхронного вызова
                    await self.db.insert_orderbook(orderbook)
                    await self.redis.publish_orderbook_update(symbol, orderbook)
                    logger.debug(f"Orderbook updated for {symbol}")
                else:
                    logger.warning(f"Failed to fetch orderbook for {symbol}")

                await asyncio.sleep(config.ORDERBOOK_UPDATE_INTERVAL)

            except Exception as e:
                logger.error(f"Error in orderbook collection for {symbol}: {e}")
                await asyncio.sleep(config.ORDERBOOK_RETRY_DELAY)


async def collect_orderbook_for_symbol(symbol: str, db_manager, redis_manager, collector: OrderBookCollector):
    try:
        await collector.collect_orderbook_data(symbol)
    except Exception as e:
        logger.error(f"Fatal error collecting orderbook for {symbol}: {e}")


async def run_orderbook_collector(db_manager, redis_manager):
    collector = OrderBookCollector(db_manager, redis_manager)
    await collector.create_session()

    try:
        tasks = [
            collect_orderbook_for_symbol(symbol, db_manager, redis_manager, collector)
            for symbol in config.ORDERBOOK_SYMBOLS
        ]
        await asyncio.gather(*tasks)
    finally:
        await collector.close_session()


