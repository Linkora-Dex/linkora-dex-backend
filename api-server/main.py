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
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

import config
from models import CandleResponse, HealthResponse
from database import DatabaseManager
from websocket_manager import WebSocketManager
from api_handlers import (
    health_check, get_candles, get_orderbook, get_symbols, 
    get_price, websocket_endpoint, initialize
)

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Создаем менеджеры для работы с базой данных и WebSocket
db_manager = DatabaseManager()
ws_manager = WebSocketManager()

async def startup():
    await db_manager.connect()
    await ws_manager.connect_redis()
    await ws_manager.start_ping_pong_tasks()
    asyncio.create_task(ws_manager.subscribe_to_updates())

    # Инициализируем обработчики API, передавая им доступ к менеджерам
    initialize(db_manager, ws_manager)

# Определяем маршруты приложения
routes = [
    Route("/health", health_check, methods=["GET"]),
    Route("/candles", get_candles, methods=["GET"]),
    Route("/orderbook", get_orderbook, methods=["GET"]),
    Route("/symbols", get_symbols, methods=["GET"]),
    Route("/price", get_price, methods=["GET"]),
    WebSocketRoute("/ws", websocket_endpoint),
]

# Настраиваем middleware для CORS
middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

# Создаем приложение Starlette
app = Starlette(routes=routes, middleware=middleware, on_startup=[startup])

# Запуск приложения при выполнении main.py напрямую
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)

