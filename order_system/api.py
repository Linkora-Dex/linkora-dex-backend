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

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import logging
from typing import List, Optional, Dict, Any
from database import DatabaseManager
import asyncio
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderAPI:
    def __init__(self, db_manager: DatabaseManager, status_monitor=None):
        self.db = db_manager
        self.status_monitor = status_monitor
        self.routes = self._create_routes()
        self.app = Starlette(debug=False, routes=self.routes)

    def _create_routes(self):
        return [
            Route('/orders/{user_address}', self.get_user_orders),
            Route('/orders/{order_id}/events', self.get_order_events),
            Route('/orders/pending', self.get_pending_orders),
            Route('/health', self.get_health),
            Route('/statistics', self.get_statistics)
        ]

    async def get_user_orders(self, request):
        start_time = time.time()
        logger.info(f"🔍 API Request: GET /orders/{request.path_params.get('user_address')}")

        try:
            user_address = request.path_params.get('user_address')
            status = request.query_params.get('status')
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))

            logger.info(f"📋 Query params: status={status}, limit={limit}, offset={offset}")

            limit = min(limit, 1000)
            offset = max(offset, 0)

            logger.info(f"🔗 Calling database for user orders...")
            orders = await self.db.get_orders_by_user(user_address, status)
            logger.info(f"✅ Database returned {len(orders)} orders")

            for order in orders:
                for key, value in order.items():
                    if hasattr(value, 'isoformat'):
                        order[key] = value.isoformat()
                    elif str(type(value)) == "<class 'decimal.Decimal'>":
                        order[key] = str(value)

            response_data = {
                "orders": orders[offset:offset + limit],
                "total": len(orders),
                "status": "success"
            }

            duration = time.time() - start_time
            logger.info(f"⏱️  Request completed in {duration:.3f}s")
            return JSONResponse(response_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Error getting user orders after {duration:.3f}s: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_order_events(self, request):
        start_time = time.time()
        logger.info(f"🔍 API Request: GET /orders/{request.path_params.get('order_id')}/events")

        try:
            order_id = int(request.path_params.get('order_id'))
            query = """SELECT event_type, old_status, new_status, tx_hash, block_number, timestamp
                       FROM order_events \
                       WHERE order_id = $1 \
                       ORDER BY timestamp ASC"""

            logger.info(f"🔗 Acquiring database connection...")
            async with self.db.pool.acquire() as conn:
                logger.info(f"💾 Executing query for order_id={order_id}")
                rows = await conn.fetch(query, order_id)
                logger.info(f"✅ Query returned {len(rows)} events")

                formatted_events = []
                for row in rows:
                    formatted_events.append({
                        'event_type': row['event_type'],
                        'old_status': row['old_status'],
                        'new_status': row['new_status'],
                        'tx_hash': row['tx_hash'],
                        'block_number': row['block_number'],
                        'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None
                    })

            response_data = {
                "order_id": order_id,
                "events": formatted_events,
                "status": "success"
            }

            duration = time.time() - start_time
            logger.info(f"⏱️  Request completed in {duration:.3f}s")
            return JSONResponse(response_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Error getting order events after {duration:.3f}s: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_pending_orders(self, request):
        start_time = time.time()
        logger.info(f"🔍 API Request: GET /orders/pending")

        try:
            logger.info(f"🔗 Calling database for pending orders...")

            # Проверяем состояние подключения к базе
            if not self.db.pool:
                logger.error("❌ Database pool is None!")
                return JSONResponse({"error": "Database not connected"}, status_code=500)

            logger.info(f"📊 Database pool status: {self.db.pool._queue.qsize()} connections available")

            orders = await self.db.get_pending_orders()
            logger.info(f"✅ Database returned {len(orders)} pending orders")

            if orders:
                logger.info(f"📋 Sample order: {orders[0]}")

            for order in orders:
                for key, value in order.items():
                    if hasattr(value, 'isoformat'):
                        order[key] = value.isoformat()
                    elif str(type(value)) == "<class 'decimal.Decimal'>":
                        order[key] = str(value)

            response_data = {
                "orders": orders,
                "count": len(orders),
                "status": "success"
            }

            duration = time.time() - start_time
            logger.info(f"⏱️  Pending orders request completed in {duration:.3f}s")
            return JSONResponse(response_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Error getting pending orders after {duration:.3f}s: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_health(self, request):
        start_time = time.time()
        logger.info(f"🔍 API Request: GET /health")

        try:
            logger.info(f"🏥 Checking health status...")

            # Проверим состояние базы данных
            db_status = "UNKNOWN"
            try:
                if self.db.pool:
                    async with self.db.pool.acquire() as conn:
                        await conn.execute("SELECT 1")
                    db_status = "HEALTHY"
                    logger.info(f"✅ Database connection test successful")
                else:
                    db_status = "NO_POOL"
                    logger.error(f"❌ Database pool is None")
            except Exception as db_e:
                db_status = "ERROR"
                logger.error(f"❌ Database connection test failed: {db_e}")

            if self.status_monitor:
                health_report = await self.status_monitor.get_health_report()
                health_report["database_direct_test"] = db_status
            else:
                health_report = {
                    "order_api": "HEALTHY",
                    "database": db_status,
                    "database_direct_test": db_status
                }

            overall_status = "healthy"
            for component, status in health_report.items():
                if status in ['ERROR', 'NOT_INITIALIZED', 'NO_POOL']:
                    overall_status = "unhealthy"
                    break

            response_data = {
                "overall_status": overall_status,
                "components": health_report,
                "status": "success"
            }

            duration = time.time() - start_time
            logger.info(f"⏱️  Health check completed in {duration:.3f}s")
            return JSONResponse(response_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Error getting health status after {duration:.3f}s: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_statistics(self, request):
        start_time = time.time()
        logger.info(f"🔍 API Request: GET /statistics")

        try:
            query = """SELECT status, \
                              COUNT(*) as count,
                       SUM(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 ELSE 0 END) as last_24h
                       FROM orders \
                       GROUP BY status"""

            logger.info(f"🔗 Acquiring database connection for statistics...")
            async with self.db.pool.acquire() as conn:
                logger.info(f"💾 Executing statistics query...")
                rows = await conn.fetch(query)
                logger.info(f"✅ Statistics query returned {len(rows)} status groups")

                stats = {}
                for row in rows:
                    stats[row['status']] = {
                        'total': row['count'],
                        'last_24h': row['last_24h']
                    }
                    logger.info(f"📊 Status {row['status']}: {row['count']} total, {row['last_24h']} last 24h")

            response_data = {
                "statistics": stats,
                "status": "success"
            }

            duration = time.time() - start_time
            logger.info(f"⏱️  Statistics request completed in {duration:.3f}s")
            return JSONResponse(response_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Error getting statistics after {duration:.3f}s: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)