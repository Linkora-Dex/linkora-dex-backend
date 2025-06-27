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
import os
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from database import DatabaseManager
from config import DB_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_decimal_to_string(decimal_value):
    if decimal_value is None:
        return None
    normalized = decimal_value.normalize()
    str_value = str(normalized)
    if 'E' in str_value or 'e' in str_value:
        if decimal_value < 1:
            str_value = f"{decimal_value:.18f}".rstrip('0').rstrip('.')
        else:
            str_value = f"{decimal_value:.18f}".rstrip('0').rstrip('.')
    return str_value


class OrderAPI:
    def __init__(self):
        logger.info("🚀 Инициализация Order API")
        self.db_manager = None
        self.routes = self._create_routes()
        self.app = Starlette(debug=False, routes=self.routes, on_startup=[self.startup])

    async def startup(self):
        try:
            logger.info("📋 Конфигурация базы данных:")
            for key, value in DB_CONFIG.items():
                if key == 'password':
                    logger.info(f"  {key}: {'*' * len(str(value))}")
                else:
                    logger.info(f"  {key}: {value}")

            self.db_manager = DatabaseManager(DB_CONFIG)
            await self.db_manager.init_pool()
            logger.info("✅ База данных подключена успешно")

            await self._test_database_connection()

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            raise

    async def _test_database_connection(self):
        try:
            logger.info("🔍 Тестирование подключения к базе данных...")
            pending_orders = await self.db_manager.get_orders_by_status('PENDING', 5, 0)
            logger.info(f"📊 Найдено {pending_orders['total']} PENDING ордеров в базе")

            for order in pending_orders['orders'][:2]:
                logger.info(f"  📋 Order ID: {order['id']}, Status: {order['status']}, User: {order['user_address'][:10]}...")

        except Exception as e:
            logger.error(f"❌ Ошибка тестирования подключения: {e}")

    def _create_routes(self):
        return [
            Route('/health', self.get_health, methods=['GET']),
            Route('/statistics', self.get_statistics, methods=['GET']),
            Route('/orders/pending', self.get_pending_orders, methods=['GET']),
            Route('/orders/executed', self.get_executed_orders, methods=['GET']),
            Route('/orders/cancelled', self.get_cancelled_orders, methods=['GET']),
            Route('/orders/all', self.get_all_orders, methods=['GET']),
            Route('/users/{user_address}/orders', self.get_user_orders, methods=['GET']),
            Route('/orders/{order_id}/events', self.get_order_events, methods=['GET']),
            Route('/orders/{order_id}', self.get_order_details, methods=['GET'])
        ]

    def _get_pagination_params(self, request):
        try:
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
        except ValueError:
            limit = 100
            offset = 0

        limit = min(max(limit, 1), 1000)
        offset = max(offset, 0)

        return limit, offset

    def _format_orders_response(self, orders_data, limit, offset):
        orders = orders_data['orders']
        total = orders_data['total']

        formatted_orders = []
        for order in orders:
            formatted_order = {
                'id': order['id'],
                'user_address': order['user_address'],
                'token_in': order['token_in'],
                'token_out': order['token_out'],
                'amount_in': format_decimal_to_string(order['amount_in']),
                'target_price': format_decimal_to_string(order['target_price']),
                'min_amount_out': format_decimal_to_string(order['min_amount_out']),
                'order_type': 'STOP' if order['order_type'] == 'STOP_LOSS' else order['order_type'],
                'is_long': order['is_long'],
                'status': order['status'],
                'created_at': order['created_at'].isoformat() if order['created_at'] else None,
                'executed_at': order['executed_at'].isoformat() if order['executed_at'] else None
            }
            formatted_orders.append(formatted_order)

        return {
            "orders": formatted_orders,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(orders) < total,
            "status": "success"
        }

    async def get_pending_orders(self, request):
        try:
            logger.info("📋 Запрос PENDING ордеров")
            limit, offset = self._get_pagination_params(request)

            if not self.db_manager:
                raise Exception("Database not initialized")

            orders_data = await self.db_manager.get_orders_by_status('PENDING', limit, offset)
            logger.info(f"✅ Найдено {orders_data['total']} PENDING ордеров (показано {len(orders_data['orders'])})")

            return JSONResponse(self._format_orders_response(orders_data, limit, offset))

        except Exception as e:
            logger.error(f"❌ Ошибка получения PENDING ордеров: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_executed_orders(self, request):
        try:
            logger.info("📋 Запрос EXECUTED ордеров")
            limit, offset = self._get_pagination_params(request)

            if not self.db_manager:
                raise Exception("Database not initialized")

            orders_data = await self.db_manager.get_orders_by_status('EXECUTED', limit, offset)
            logger.info(f"✅ Найдено {orders_data['total']} EXECUTED ордеров (показано {len(orders_data['orders'])})")

            return JSONResponse(self._format_orders_response(orders_data, limit, offset))

        except Exception as e:
            logger.error(f"❌ Ошибка получения EXECUTED ордеров: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_cancelled_orders(self, request):
        try:
            logger.info("📋 Запрос CANCELLED ордеров")
            limit, offset = self._get_pagination_params(request)

            if not self.db_manager:
                raise Exception("Database not initialized")

            orders_data = await self.db_manager.get_orders_by_status('CANCELLED', limit, offset)
            logger.info(f"✅ Найдено {orders_data['total']} CANCELLED ордеров (показано {len(orders_data['orders'])})")

            return JSONResponse(self._format_orders_response(orders_data, limit, offset))

        except Exception as e:
            logger.error(f"❌ Ошибка получения CANCELLED ордеров: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_all_orders(self, request):
        try:
            status = request.query_params.get('status')
            if status:
                status = status.upper()
                if status not in ['PENDING', 'EXECUTED', 'CANCELLED']:
                    return JSONResponse({"error": "Invalid status. Use: pending, executed, cancelled"}, status_code=400)

            logger.info(f"📋 Запрос всех ордеров с фильтром status={status}")
            limit, offset = self._get_pagination_params(request)

            if not self.db_manager:
                raise Exception("Database not initialized")

            orders_data = await self.db_manager.get_orders_by_status(status, limit, offset)
            logger.info(f"✅ Найдено {orders_data['total']} ордеров с статусом {status or 'ALL'} (показано {len(orders_data['orders'])})")

            return JSONResponse(self._format_orders_response(orders_data, limit, offset))

        except Exception as e:
            logger.error(f"❌ Ошибка получения всех ордеров: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_user_orders(self, request):
        try:
            user_address = request.path_params.get('user_address')
            status = request.query_params.get('status')
            if status:
                status = status.upper()
                if status not in ['PENDING', 'EXECUTED', 'CANCELLED']:
                    return JSONResponse({"error": "Invalid status. Use: pending, executed, cancelled"}, status_code=400)

            logger.info(f"📋 Запрос ордеров для пользователя: {user_address[:10]}... с фильтром status={status}")
            limit, offset = self._get_pagination_params(request)

            if not self.db_manager:
                raise Exception("Database not initialized")

            orders_data = await self.db_manager.get_orders_by_user(user_address, status, limit, offset)
            logger.info(f"✅ Найдено {orders_data['total']} ордеров для пользователя {user_address[:10]}... (показано {len(orders_data['orders'])})")

            return JSONResponse(self._format_orders_response(orders_data, limit, offset))

        except Exception as e:
            logger.error(f"❌ Ошибка получения ордеров пользователя: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_order_details(self, request):
        try:
            order_id_str = request.path_params.get('order_id')
            try:
                order_id = int(order_id_str)
            except (ValueError, TypeError):
                return JSONResponse({
                    "error": "Invalid order_id format. Must be a number."
                }, status_code=400)

            logger.info(f"📋 Запрос деталей ордера: {order_id}")

            if not self.db_manager:
                raise Exception("Database not initialized")

            order = await self.db_manager.get_order_by_id(order_id)

            if not order:
                return JSONResponse({
                    "error": f"Order {order_id} not found"
                }, status_code=404)

            formatted_order = {
                'id': order['id'],
                'user_address': order['user_address'],
                'token_in': order['token_in'],
                'token_out': order['token_out'],
                'amount_in': format_decimal_to_string(order['amount_in']),
                'target_price': format_decimal_to_string(order['target_price']),
                'min_amount_out': format_decimal_to_string(order['min_amount_out']),
                'order_type': 'STOP' if order['order_type'] == 'STOP_LOSS' else order['order_type'],
                'is_long': order['is_long'],
                'status': order['status'],
                'self_executable': order['self_executable'],
                'created_at': order['created_at'].isoformat() if order['created_at'] else None,
                'updated_at': order['updated_at'].isoformat() if order['updated_at'] else None,
                'executed_at': order['executed_at'].isoformat() if order['executed_at'] else None,
                'tx_hash': order['tx_hash'],
                'block_number': order['block_number'],
                'executor_address': order['executor_address'],
                'amount_out': format_decimal_to_string(order['amount_out']),
                'execution_tx_hash': order['execution_tx_hash']
            }

            logger.info(f"✅ Получены детали ордера {order_id}")

            return JSONResponse({
                "order": formatted_order,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"❌ Ошибка получения деталей ордера: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_order_events(self, request):
        try:
            order_id_str = request.path_params.get('order_id')
            try:
                order_id = int(order_id_str)
            except (ValueError, TypeError):
                return JSONResponse({
                    "error": "Invalid order_id format. Must be a number."
                }, status_code=400)

            logger.info(f"📝 Запрос событий для ордера: {order_id}")

            if not self.db_manager:
                raise Exception("Database not initialized")

            check_query = "SELECT id FROM orders WHERE id = $1"
            async with self.db_manager.pool.acquire() as conn:
                order_exists = await conn.fetchval(check_query, order_id)

            if not order_exists:
                return JSONResponse({
                    "error": f"Order {order_id} not found"
                }, status_code=404)

            events_query = """
                           SELECT event_type, old_status, new_status, tx_hash, block_number, timestamp, event_data
                           FROM order_events
                           WHERE order_id = $1
                           ORDER BY timestamp ASC
                           """

            async with self.db_manager.pool.acquire() as conn:
                rows = await conn.fetch(events_query, order_id)

            formatted_events = []
            for row in rows:
                formatted_events.append({
                    'event_type': row['event_type'],
                    'old_status': row['old_status'],
                    'new_status': row['new_status'],
                    'tx_hash': row['tx_hash'],
                    'block_number': row['block_number'],
                    'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None,
                    'event_data': row['event_data'] if row['event_data'] else {}
                })

            logger.info(f"✅ Найдено {len(formatted_events)} событий для ордера {order_id}")

            return JSONResponse({
                "order_id": order_id,
                "events": formatted_events,
                "total": len(formatted_events),
                "status": "success"
            })

        except Exception as e:
            logger.error(f"❌ Ошибка получения событий ордера: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_health(self, request):
        try:
            logger.debug("🏥 Проверка здоровья системы")

            db_status = "HEALTHY" if self.db_manager and self.db_manager.pool else "UNHEALTHY"

            health_report = {
                "order_api": "HEALTHY",
                "database": db_status,
                "timestamp": datetime.now().isoformat()
            }

            if db_status == "HEALTHY":
                try:
                    await self.db_manager.get_orders_by_status('PENDING', 1, 0)
                    health_report["database_connection"] = "WORKING"
                except Exception as e:
                    health_report["database_connection"] = f"ERROR: {str(e)}"
                    health_report["database"] = "UNHEALTHY"

            overall_status = "healthy" if all(
                status == "HEALTHY" for key, status in health_report.items()
                if key not in ["timestamp", "database_connection"]
            ) else "unhealthy"

            return JSONResponse({
                "overall_status": overall_status,
                "components": health_report,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def get_statistics(self, request):
        try:
            logger.info("📊 Запрос статистики")

            if not self.db_manager:
                raise Exception("Database not initialized")

            query = """SELECT status,
                              COUNT(*) as count,
                      SUM(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 ELSE 0 END) as last_24h
                       FROM orders
                       GROUP BY status"""

            async with self.db_manager.pool.acquire() as conn:
                rows = await conn.fetch(query)

            statistics = {
                "PENDING": {"total": 0, "last_24h": 0},
                "EXECUTED": {"total": 0, "last_24h": 0},
                "CANCELLED": {"total": 0, "last_24h": 0}
            }

            for row in rows:
                status = row['status']
                statistics[status] = {
                    "total": int(row['count']),
                    "last_24h": int(row['last_24h'])
                }

            logger.info(f"✅ Статистика получена: {statistics}")

            return JSONResponse({
                "statistics": statistics,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)


api_instance = OrderAPI()
app = api_instance.app