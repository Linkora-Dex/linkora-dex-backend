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

import asyncpg
import asyncio
import logging
import json
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.pool = None
        self._lock = asyncio.Lock()

    async def init_pool(self):
        dsn = f"postgresql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
        logger.info(f"🔗 Инициализация пула подключений к базе данных")
        logger.debug(f"DSN: postgresql://{self.config['user']}:***@{self.config['host']}:{self.config['port']}/{self.config['database']}")

        self.pool = await asyncpg.create_pool(
            dsn,
            min_size=10,
            max_size=50,
            command_timeout=30,
            server_settings={
                'idle_in_transaction_session_timeout': '300000',
                'statement_timeout': '30000',
            }
        )
        await self._create_tables()
        logger.info(f"✅ PostgreSQL pool initialized for database: {self.config['database']}")

    async def _create_tables(self):
        tables = [
            """CREATE TABLE IF NOT EXISTS orders
            (
                id
                BIGINT
                PRIMARY
                KEY,
                user_address
                VARCHAR
               (
                42
               ) NOT NULL,
                token_in VARCHAR
               (
                   42
               ) NOT NULL,
                token_out VARCHAR
               (
                   42
               ) NOT NULL,
                amount_in DECIMAL
               (
                   36,
                   18
               ) NOT NULL,
                target_price DECIMAL
               (
                   36,
                   18
               ) NOT NULL,
                min_amount_out DECIMAL
               (
                   36,
                   18
               ) NOT NULL,
                order_type VARCHAR
               (
                   20
               ) NOT NULL,
                is_long BOOLEAN,
                status VARCHAR
               (
                   20
               ) NOT NULL,
                self_executable BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP NULL,
                tx_hash VARCHAR
               (
                   66
               ),
                block_number BIGINT,
                executor_address VARCHAR
               (
                   42
               ) NULL,
                amount_out DECIMAL
               (
                   36,
                   18
               ) NULL,
                execution_tx_hash VARCHAR
               (
                   66
               ) NULL
                )""",
            """CREATE INDEX IF NOT EXISTS idx_user_status ON orders (user_address, status)""",
            """CREATE INDEX IF NOT EXISTS idx_status_type ON orders (status, order_type)""",
            """CREATE INDEX IF NOT EXISTS idx_created_at ON orders (created_at)""",
            """CREATE INDEX IF NOT EXISTS idx_status_created ON orders (status, created_at DESC)""",
            """CREATE TABLE IF NOT EXISTS order_events
            (
                id
                BIGSERIAL
                PRIMARY
                KEY,
                order_id
                BIGINT
                NOT
                NULL,
                event_type
                VARCHAR
               (
                30
               ) NOT NULL,
                old_status VARCHAR
               (
                   20
               ),
                new_status VARCHAR
               (
                   20
               ),
                tx_hash VARCHAR
               (
                   66
               ),
                block_number BIGINT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_data JSONB
                )""",
            """CREATE INDEX IF NOT EXISTS idx_order_events ON order_events (order_id, timestamp)""",
            """CREATE TABLE IF NOT EXISTS system_state
            (
                id
                SERIAL
                PRIMARY
                KEY,
                component_name
                VARCHAR
               (
                50
               ) UNIQUE NOT NULL,
                last_processed_block BIGINT NOT NULL,
                last_processed_tx_hash VARCHAR
               (
                   66
               ),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR
               (
                   20
               ) DEFAULT 'ACTIVE'
                )""",
            """CREATE INDEX IF NOT EXISTS idx_component ON system_state (component_name)""",
            """CREATE TABLE IF NOT EXISTS processed_events
            (
                id
                BIGSERIAL
                PRIMARY
                KEY,
                tx_hash
                VARCHAR
               (
                66
               ) NOT NULL,
                log_index INTEGER NOT NULL,
                event_type VARCHAR
               (
                   30
               ) NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE
               (
                   tx_hash,
                   log_index
               )
                )""",
            """CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_events (processed_at)"""
        ]

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for table_sql in tables:
                    await conn.execute(table_sql)

    async def _execute_with_retry(self, func, *args, max_retries=3, **kwargs):
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(0.1 * (2 ** attempt))
            except Exception as e:
                logger.error(f"Non-retryable database error: {e}")
                raise

    @asynccontextmanager
    async def transaction(self):
        async with self._lock:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    yield conn

    async def get_component_state(self, component_name: str) -> Optional[Dict]:
        query = """SELECT last_processed_block, last_processed_tx_hash, status, updated_at
                   FROM system_state
                   WHERE component_name = $1"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, component_name)
            if row:
                result = dict(row)
                logger.debug(f"Retrieved component state for {component_name}: {result}")
                return result
            return None

    async def save_component_state(self, component_name: str, block_number: int,
                                   status: str, tx_hash: Optional[str] = None, conn=None):
        query = """INSERT INTO system_state (component_name, last_processed_block, last_processed_tx_hash, status)
                   VALUES ($1, $2, $3, $4) ON CONFLICT (component_name) DO
        UPDATE SET
            last_processed_block = EXCLUDED.last_processed_block,
            last_processed_tx_hash = EXCLUDED.last_processed_tx_hash,
            status = EXCLUDED.status,
            updated_at = CURRENT_TIMESTAMP"""

        logger.debug(f"Saving component state: {component_name}, block: {block_number}, status: {status}")

        if conn:
            await conn.execute(query, component_name, block_number, tx_hash, status)
        else:
            async with self.pool.acquire() as connection:
                await connection.execute(query, component_name, block_number, tx_hash, status)

    async def check_event_processed(self, tx_hash: str, log_index: int, conn=None) -> bool:
        query = "SELECT 1 FROM processed_events WHERE tx_hash = $1 AND log_index = $2"

        if conn:
            result = await conn.fetchval(query, tx_hash, log_index)
        else:
            async with self.pool.acquire() as connection:
                result = await connection.fetchval(query, tx_hash, log_index)

        is_processed = result is not None
        logger.debug(f"Event {tx_hash[:10]}...:{log_index} already processed: {is_processed}")
        return is_processed

    async def mark_event_processed(self, tx_hash: str, log_index: int, event_type: str, conn=None):
        if not await self.check_event_processed(tx_hash, log_index, conn):
            query = """INSERT INTO processed_events (tx_hash, log_index, event_type)
                       VALUES ($1, $2, $3)"""
            if conn:
                await conn.execute(query, tx_hash, log_index, event_type)
            else:
                async with self.pool.acquire() as connection:
                    await connection.execute(query, tx_hash, log_index, event_type)

        logger.debug(f"Marking event as processed: {tx_hash[:10]}...:{log_index} ({event_type})")

    async def insert_order(self, order_data: Dict[str, Any], conn=None):
        query = """INSERT INTO orders (id, user_address, token_in, token_out, amount_in, target_price,
                                       min_amount_out, order_type, is_long, status, self_executable,
                                       created_at, tx_hash, block_number)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14) ON CONFLICT (id) DO NOTHING"""

        values = (
            order_data['id'], order_data['user_address'], order_data['token_in'],
            order_data['token_out'], order_data['amount_in'], order_data['target_price'],
            order_data['min_amount_out'], order_data['order_type'], order_data['is_long'],
            order_data['status'], order_data['self_executable'], order_data['created_at'],
            order_data['tx_hash'], order_data['block_number']
        )

        logger.info(
            f"💾 Inserting order into database: ID={order_data['id']}, User={order_data['user_address'][:10]}..., Status={order_data['status']}, Type={order_data['order_type']}")

        if conn:
            await conn.execute(query, *values)
        else:
            async with self.pool.acquire() as connection:
                await connection.execute(query, *values)

        logger.info(f"✅ Order {order_data['id']} successfully saved to database")

    async def update_order(self, order_id: int, update_data: Dict[str, Any], conn=None):
        set_clauses = []
        values = []
        param_count = 1

        for key, value in update_data.items():
            set_clauses.append(f"{key} = ${param_count}")
            values.append(value)
            param_count += 1

        values.append(order_id)
        query = f"UPDATE orders SET {', '.join(set_clauses)} WHERE id = ${param_count}"

        logger.info(f"🔄 Updating order {order_id}: {update_data}")

        if conn:
            await conn.execute(query, *values)
        else:
            async with self.pool.acquire() as connection:
                await connection.execute(query, *values)

        logger.info(f"✅ Order {order_id} successfully updated in database")

    async def insert_order_event(self, order_id: int, event_type: str, old_status: Optional[str],
                                 new_status: str, event_data: Dict[str, Any], conn=None):
        query = """INSERT INTO order_events (order_id, event_type, old_status, new_status,
                                             tx_hash, block_number, event_data)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)"""

        tx_hash = None
        if 'transactionHash' in event_data and hasattr(event_data['transactionHash'], 'hex'):
            tx_hash = event_data['transactionHash'].hex()

        event_json = json.dumps(dict(event_data), default=str)

        values = (
            order_id, event_type, old_status, new_status,
            tx_hash, event_data.get('blockNumber'), event_json
        )

        logger.info(f"📝 Inserting order event: Order={order_id}, Event={event_type}, Status={old_status}->{new_status}")

        if conn:
            await conn.execute(query, *values)
        else:
            async with self.pool.acquire() as connection:
                await connection.execute(query, *values)

        logger.info(f"✅ Order event for order {order_id} successfully saved to database")

    async def get_orders_by_status(self, status: Optional[str], limit: int, offset: int) -> Dict[str, Any]:
        if status:
            count_query = "SELECT COUNT(*) FROM orders WHERE status = $1"
            data_query = "SELECT * FROM orders WHERE status = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3"
            params_count = [status]
            params_data = [status, limit, offset]
        else:
            count_query = "SELECT COUNT(*) FROM orders"
            data_query = "SELECT * FROM orders ORDER BY created_at DESC LIMIT $1 OFFSET $2"
            params_count = []
            params_data = [limit, offset]

        logger.debug(f"📋 Querying orders with status={status}, limit={limit}, offset={offset}")

        async with self.pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params_count)
            rows = await conn.fetch(data_query, *params_data)
            orders = [dict(row) for row in rows]

        logger.debug(f"✅ Found {total} total orders, returned {len(orders)} orders")
        return {"orders": orders, "total": total}

    async def get_orders_by_user(self, user_address: str, status: Optional[str], limit: int, offset: int) -> Dict[str, Any]:
        if status:
            count_query = "SELECT COUNT(*) FROM orders WHERE user_address = $1 AND status = $2"
            data_query = "SELECT * FROM orders WHERE user_address = $1 AND status = $2 ORDER BY created_at DESC LIMIT $3 OFFSET $4"
            params_count = [user_address, status]
            params_data = [user_address, status, limit, offset]
        else:
            count_query = "SELECT COUNT(*) FROM orders WHERE user_address = $1"
            data_query = "SELECT * FROM orders WHERE user_address = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3"
            params_count = [user_address]
            params_data = [user_address, limit, offset]

        logger.debug(f"📋 Querying orders for user {user_address[:10]}... with status={status}, limit={limit}, offset={offset}")

        async with self.pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params_count)
            rows = await conn.fetch(data_query, *params_data)
            orders = [dict(row) for row in rows]

        logger.debug(f"✅ Found {total} total orders for user, returned {len(orders)} orders")
        return {"orders": orders, "total": total}

    async def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        query = "SELECT * FROM orders WHERE id = $1"
        logger.debug(f"📋 Querying order by id={order_id}")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, order_id)
            if row:
                result = dict(row)
                logger.debug(f"✅ Found order {order_id}")
                return result

        logger.debug(f"❌ Order {order_id} not found")
        return None

    async def get_pending_orders(self) -> List[Dict]:
        query = "SELECT * FROM orders WHERE status = 'PENDING' ORDER BY created_at ASC"
        logger.info("📋 Querying pending orders")
        logger.debug(f"SQL: {query}")

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                result = [dict(row) for row in rows]

            logger.info(f"✅ Found {len(result)} pending orders")

            if len(result) > 0:
                for order in result[:3]:
                    logger.info(f"  📋 Order ID: {order['id']}, Status: {order['status']}, User: {order['user_address'][:10]}...")

            return result

        except Exception as e:
            logger.error(f"❌ Error in get_pending_orders: {e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL pool closed")