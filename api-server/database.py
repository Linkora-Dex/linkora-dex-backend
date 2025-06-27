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

import logging
import json
import asyncpg
from typing import List, Optional, Dict
from datetime import datetime
import config

logger = logging.getLogger(__name__)

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

    async def get_candles(self, symbol: str, timeframe: str, start_date: Optional[datetime], limit: int) -> List[dict]:
        try:
            async with self.pool.acquire() as conn:
                if timeframe == "1":
                    query = self._build_minute_query(start_date, limit)
                else:
                    query = self._build_aggregated_query(timeframe, start_date, limit)

                rows = await conn.fetch(query, symbol.upper())
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            raise

    async def get_orderbook(self, symbol: str, levels: int = None) -> Optional[dict]:
        try:
            async with self.pool.acquire() as conn:
                query = """
                        SELECT symbol, timestamp, last_update_id, bids, asks
                        FROM orderbook_data
                        WHERE symbol = $1
                        ORDER BY timestamp DESC
                        LIMIT 1
                        """
                result = await conn.fetchrow(query, symbol.upper())

                if result:
                    bids = json.loads(result['bids'])
                    asks = json.loads(result['asks'])

                    if levels and levels < len(bids):
                        bids = bids[:levels]
                    if levels and levels < len(asks):
                        asks = asks[:levels]

                    return {
                        'symbol': result['symbol'],
                        'timestamp': result['timestamp'],
                        'last_update_id': result['last_update_id'],
                        'bids': bids,
                        'asks': asks
                    }
                return None
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None

    def _build_minute_query(self, start_date: Optional[datetime], limit: int) -> str:
        if start_date:
            return f"""
                SELECT timestamp, open_time, close_time, open_price, high_price, low_price,
                    close_price, volume, quote_volume, trades, taker_buy_volume, taker_buy_quote_volume
                FROM candles
                WHERE symbol = $1 AND open_time >= '{start_date}'
                ORDER BY timestamp ASC
                LIMIT {limit}
            """
        else:
            return f"""
                SELECT timestamp, open_time, close_time, open_price, high_price, low_price,
                    close_price, volume, quote_volume, trades, taker_buy_volume, taker_buy_quote_volume
                FROM candles
                WHERE symbol = $1
                ORDER BY timestamp DESC
                LIMIT {limit}
            """

    def _build_aggregated_query(self, timeframe: str, start_date: Optional[datetime], limit: int) -> str:
        minutes = config.TIMEFRAMES.get(timeframe, 1)
        interval = f"{minutes} minutes"

        base_query = f"""
            SELECT
                EXTRACT(epoch FROM time_bucket('{interval}', open_time)) * 1000 as timestamp,
                time_bucket('{interval}', open_time) as open_time,
                time_bucket('{interval}', open_time) + interval '{interval}' - interval '1 second' as close_time,
                first(open_price, open_time) as open_price,
                max(high_price) as high_price,
                min(low_price) as low_price,
                last(close_price, open_time) as close_price,
                sum(volume) as volume,
                sum(quote_volume) as quote_volume,
                sum(trades) as trades,
                sum(taker_buy_volume) as taker_buy_volume,
                sum(taker_buy_quote_volume) as taker_buy_quote_volume
            FROM candles
            WHERE symbol = $1
        """

        if start_date:
            base_query += f" AND open_time >= '{start_date}'"

        base_query += f"""
            GROUP BY time_bucket('{interval}', open_time)
            ORDER BY time_bucket('{interval}', open_time) {'ASC' if start_date else 'DESC'}
            LIMIT {limit}
        """

        return base_query

    async def get_symbols(self) -> List[str]:
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT DISTINCT symbol FROM candles ORDER BY symbol")
                return [row['symbol'] for row in rows]
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            raise

    async def check_health(self) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except:
            return False
