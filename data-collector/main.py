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
import asyncpg
import redis.asyncio as redis
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal, InvalidOperation
import config
from orderbook_collector import run_orderbook_collector

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)


def normalize_decimal_value(value_str: str) -> Decimal:
    try:
        if isinstance(value_str, str) and ('E' in value_str.upper() or 'e' in value_str):
            return Decimal(str(float(value_str)))
        return Decimal(str(value_str))
    except (ValueError, InvalidOperation, TypeError):
        logger.warning(f"Invalid decimal value: {value_str}, using 0")
        return Decimal('0')


class DatabaseManager:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                min_size=2,
                max_size=10,
                command_timeout=30,
                server_settings={
                    'idle_in_transaction_session_timeout': '300000',
                    'statement_timeout': '30000',
                }
            )
            logger.info("Database connected")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def get_last_timestamp(self, symbol: str) -> Optional[int]:
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT last_timestamp FROM collector_state WHERE symbol = $1",
                    symbol
                )
                return result
        except Exception as e:
            logger.error(f"Error getting last timestamp for {symbol}: {e}")
            return None

    async def update_state(self, symbol: str, timestamp: int, is_realtime: bool = False):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO collector_state (symbol, last_timestamp, is_realtime, last_updated)
                                   VALUES ($1, $2, $3, NOW()) ON CONFLICT (symbol) DO
                                   UPDATE SET
                                       last_timestamp = EXCLUDED.last_timestamp,
                                       is_realtime = EXCLUDED.is_realtime,
                                       last_updated = NOW()
                                   """, symbol, timestamp, is_realtime)
        except Exception as e:
            logger.error(f"Error updating state for {symbol}: {e}")

    async def insert_candles(self, candles: List[Dict]):
        if not candles:
            return
        try:
            async with self.pool.acquire() as conn:
                values = []
                for candle in candles:
                    values.append((
                        candle['symbol'],
                        candle['timestamp'],
                        datetime.fromtimestamp(candle['timestamp'] / 1000),
                        datetime.fromtimestamp(candle['close_time'] / 1000),
                        candle['open'],
                        candle['high'],
                        candle['low'],
                        candle['close'],
                        candle['volume'],
                        candle['quote_volume'],
                        candle['trades'],
                        candle['taker_buy_volume'],
                        candle['taker_buy_quote_volume']
                    ))

                await conn.executemany("""
                                       INSERT INTO candles (symbol, timestamp, open_time, close_time, open_price, high_price,
                                                            low_price, close_price, volume, quote_volume, trades,
                                                            taker_buy_volume, taker_buy_quote_volume)
                                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) ON CONFLICT (symbol, timestamp) DO NOTHING
                                       """, values)

                logger.info(f"Inserted {len(candles)} candles for {candles[0]['symbol']}")
        except Exception as e:
            logger.error(f"Error inserting candles: {e}")

    async def insert_orderbook(self, orderbook: Dict):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO orderbook_data (symbol, timestamp, last_update_id, bids, asks)
                                   VALUES ($1, $2, $3, $4, $5) ON CONFLICT (symbol, timestamp) DO
                                   UPDATE SET
                                       last_update_id = EXCLUDED.last_update_id,
                                       bids = EXCLUDED.bids,
                                       asks = EXCLUDED.asks
                                   """,
                                   orderbook['symbol'],
                                   orderbook['timestamp'],
                                   orderbook['last_update_id'],
                                   json.dumps(orderbook['bids']),
                                   json.dumps(orderbook['asks'])
                                   )
                logger.debug(f"Inserted orderbook for {orderbook['symbol']}")
        except Exception as e:
            logger.error(f"Error inserting orderbook: {e}")


class RedisManager:
    def __init__(self):
        self.redis = None

    async def connect(self):
        try:
            self.redis = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def publish_candle_update(self, symbol: str, candle: Dict):
        try:
            if self.redis:
                channel = f"candles:{symbol}"
                message = json.dumps({
                    'symbol': symbol,
                    'timestamp': candle['timestamp'],
                    'open': str(candle['open']),
                    'high': str(candle['high']),
                    'low': str(candle['low']),
                    'close': str(candle['close']),
                    'volume': str(candle['volume']),
                    'quote_volume': str(candle['quote_volume']),
                    'trades': candle['trades']
                })
                await self.redis.publish(channel, message)
                await self.redis.publish("candles:all", message)
        except Exception as e:
            logger.error(f"Error publishing candle to Redis: {e}")

    async def publish_orderbook_update(self, symbol: str, orderbook: Dict):
        try:
            if self.redis:
                channel = f"orderbook:{symbol}"
                message = json.dumps({
                    'symbol': orderbook['symbol'],
                    'timestamp': orderbook['timestamp'],
                    'last_update_id': orderbook['last_update_id'],
                    'bids': orderbook['bids'],
                    'asks': orderbook['asks']
                })
                await self.redis.publish(channel, message)
                await self.redis.publish("orderbook:all", message)
                logger.debug(f"Published orderbook update for {symbol}")
        except Exception as e:
            logger.error(f"Error publishing orderbook to Redis: {e}")


class BinanceCollector:
    def __init__(self, db_manager: DatabaseManager, redis_manager: RedisManager):
        self.db = db_manager
        self.redis = redis_manager
        self.session = None

    async def create_session(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def fetch_klines(self, symbol: str, start_time: int, end_time: int) -> List[Dict]:
        url = f"{config.BINANCE_BASE_URL}/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': config.INTERVAL,
            'startTime': start_time,
            'endTime': end_time,
            'limit': config.BATCH_SIZE
        }

        for attempt in range(config.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.parse_klines(symbol, data)
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limit hit for {symbol}, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"HTTP {response.status} for {symbol}")
                        await asyncio.sleep(config.RETRY_DELAY)
            except Exception as e:
                logger.error(f"Request failed for {symbol} (attempt {attempt + 1}): {e}")
                if attempt < config.MAX_RETRIES - 1:
                    await asyncio.sleep(config.RETRY_DELAY * (2 ** attempt))

        return []

    def parse_klines(self, symbol: str, data: List) -> List[Dict]:
        candles = []
        for item in data:
            try:
                open_price = normalize_decimal_value(item[1])
                high_price = normalize_decimal_value(item[2])
                low_price = normalize_decimal_value(item[3])
                close_price = normalize_decimal_value(item[4])
                volume = normalize_decimal_value(item[5])
                quote_volume = normalize_decimal_value(item[7])
                taker_buy_volume = normalize_decimal_value(item[9])
                taker_buy_quote_volume = normalize_decimal_value(item[10])

                if any(str(val).upper().endswith('E-8') or str(val).upper().endswith('E+') for val in [item[1], item[5], item[7], item[9], item[10]]):
                    logger.debug(f"Scientific notation detected for {symbol}: volume={item[5]}, quote_volume={item[7]}")

                candle = {
                    'symbol': symbol,
                    'timestamp': int(item[0]),
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume,
                    'close_time': int(item[6]),
                    'quote_volume': quote_volume,
                    'trades': int(item[8]),
                    'taker_buy_volume': taker_buy_volume,
                    'taker_buy_quote_volume': taker_buy_quote_volume
                }
                candles.append(candle)
            except Exception as e:
                logger.error(f"Error parsing candle data for {symbol}: {e}, data: {item}")
                continue

        return candles

    async def collect_historical_data(self, symbol: str):
        last_timestamp = await self.db.get_last_timestamp(symbol)
        start_time = last_timestamp + 60000 if last_timestamp else int(config.START_DATE.timestamp() * 1000)
        current_time = int(datetime.now().timestamp() * 1000)

        logger.info(f"Starting historical collection for {symbol} from {datetime.fromtimestamp(start_time / 1000)}")

        while start_time < current_time:
            end_time = min(start_time + (config.BATCH_SIZE * 60000), current_time)
            candles = await self.fetch_klines(symbol, start_time, end_time)

            if candles:
                await self.db.insert_candles(candles)
                last_timestamp = candles[-1]['timestamp']
                await self.db.update_state(symbol, last_timestamp)
                start_time = last_timestamp + 60000
            else:
                logger.warning(f"No data received for {symbol}, skipping batch")
                start_time = end_time + 60000

            await asyncio.sleep(0.1)

        logger.info(f"Historical collection completed for {symbol}")
        return True

    async def collect_realtime_data(self, symbol: str):
        logger.info(f"Starting realtime collection for {symbol}")

        while True:
            try:
                current_time = int(datetime.now().timestamp() * 1000)
                start_time = current_time - 300000

                candles = await self.fetch_klines(symbol, start_time, current_time)
                if candles:
                    await self.db.insert_candles(candles)
                    last_timestamp = candles[-1]['timestamp']
                    await self.db.update_state(symbol, last_timestamp, True)

                    for candle in candles:
                        await self.redis.publish_candle_update(symbol, candle)

                await asyncio.sleep(config.REALTIME_INTERVAL)
            except Exception as e:
                logger.error(f"Error in realtime collection for {symbol}: {e}")
                await asyncio.sleep(5)


async def collect_symbol_data(symbol: str, db_manager: DatabaseManager, redis_manager: RedisManager, collector: BinanceCollector):
    try:
        historical_complete = await collector.collect_historical_data(symbol)
        if historical_complete:
            await collector.collect_realtime_data(symbol)
    except Exception as e:
        logger.error(f"Fatal error collecting data for {symbol}: {e}")


async def main():
    db_manager = DatabaseManager()
    await db_manager.connect()

    redis_manager = RedisManager()
    await redis_manager.connect()

    collector = BinanceCollector(db_manager, redis_manager)
    await collector.create_session()

    try:
        candle_tasks = [collect_symbol_data(symbol, db_manager, redis_manager, collector) for symbol in config.SYMBOLS]
        orderbook_task = run_orderbook_collector(db_manager, redis_manager)

        await asyncio.gather(*candle_tasks, orderbook_task)
    finally:
        await collector.close_session()
        await redis_manager.close()
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())