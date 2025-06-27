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
import asyncio
import json
import time
import redis.asyncio as redis
from typing import Dict, Set, Optional
from starlette.websockets import WebSocket
import config
from aggregators import CandleAggregator

logger = logging.getLogger(__name__)

PERIODIC_UPDATE_INTERVAL = int(asyncio.get_event_loop().get_debug() and 5 or 5)

PERIODIC_UPDATE_INTERVAL = int(asyncio.get_event_loop().get_debug() and 5 or 5)

class ConnectionInfo:
    def __init__(self, websocket: WebSocket, symbol: str, timeframe: str = "1", data_type: str = "candles"):
        self.websocket = websocket
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_type = data_type
        self.last_pong = time.time()
        self.is_alive = True
        self.connection_key = f"{symbol}:{timeframe}:{data_type}"

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Set[ConnectionInfo]] = {}
        self.aggregators: Dict[str, CandleAggregator] = {}
        self.last_update_times: Dict[str, float] = {}
        self.redis = None
        self.ping_task = None
        self.cleanup_task = None
        self.periodic_task = None

    async def connect_redis(self):
        try:
            self.redis = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
            logger.info("Redis connected for WebSocket manager")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")

    async def start_ping_pong_tasks(self):
        self.ping_task = asyncio.create_task(self._ping_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.periodic_task = asyncio.create_task(self._periodic_update_loop())
        logger.info("WebSocket ping/pong and periodic update tasks started")

    async def _ping_loop(self):
        while True:
            try:
                await asyncio.sleep(config.WEBSOCKET_PING_INTERVAL)
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")

    async def _periodic_update_loop(self):
        while True:
            try:
                await asyncio.sleep(PERIODIC_UPDATE_INTERVAL)
                await self._send_periodic_updates()
            except Exception as e:
                logger.error(f"Error in periodic update loop: {e}")

    async def _send_periodic_updates(self):
        current_time = time.time()

        for connection_key in list(self.connections.keys()):
            if connection_key.endswith(":candles") and connection_key != "all:1:candles":
                if connection_key in self.aggregators:
                    aggregator = self.aggregators[connection_key]
                    current_candle = aggregator.get_current_candle()

                    if current_candle:
                        last_update = self.last_update_times.get(connection_key, 0)
                        if current_time - last_update >= PERIODIC_UPDATE_INTERVAL:
                            message = json.dumps(current_candle)
                            await self._broadcast_to_connections(
                                self.connections[connection_key],
                                message
                            )
                            self.last_update_times[connection_key] = current_time
                            logger.debug(f"Periodic update sent for {connection_key}")

    async def _send_heartbeat(self):
        heartbeat_msg = json.dumps({"type": "heartbeat", "timestamp": int(time.time() * 1000)})
        for connection_key in list(self.connections.keys()):
            for conn_info in list(self.connections[connection_key]):
                try:
                    await conn_info.websocket.send_text(heartbeat_msg)
                    logger.debug(f"Heartbeat sent to {connection_key}")
                except Exception as e:
                    logger.warning(f"Failed to send heartbeat to {connection_key}: {e}")
                    conn_info.is_alive = False

    async def _cleanup_loop(self):
        while True:
            try:
                await asyncio.sleep(config.WEBSOCKET_CLEANUP_INTERVAL)
                await self._cleanup_stale_connections()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_connections(self):
        current_time = time.time()
        timeout = config.WEBSOCKET_PONG_TIMEOUT

        for connection_key in list(self.connections.keys()):
            for conn_info in list(self.connections[connection_key]):
                if not conn_info.is_alive or current_time - conn_info.last_pong > timeout:
                    logger.info(f"Removing stale connection for {connection_key}")
                    await self._remove_connection_info(conn_info, connection_key)

    async def subscribe_to_updates(self):
        if not self.redis:
            return

        pubsub = self.redis.pubsub()
        await pubsub.subscribe("candles:all", "orderbook:all")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    if message["channel"] == "candles:all":
                        await self.broadcast_candle_update(message["data"])
                    elif message["channel"] == "orderbook:all":
                        await self.broadcast_orderbook_update(message["data"])
        except Exception as e:
            logger.error(f"Error in Redis subscription: {e}")

    async def add_connection(self, websocket: WebSocket, symbol: str = "all", timeframe: str = "1", data_type: str = "candles"):
        connection_key = f"{symbol}:{timeframe}:{data_type}"

        if connection_key not in self.connections:
            self.connections[connection_key] = set()

        if connection_key not in self.aggregators and symbol != "all" and data_type == "candles":
            self.aggregators[connection_key] = CandleAggregator(symbol, timeframe)

        conn_info = ConnectionInfo(websocket, symbol, timeframe, data_type)
        self.connections[connection_key].add(conn_info)
        logger.info(f"WebSocket connected for {connection_key} (total: {len(self.connections[connection_key])})")

    async def remove_connection(self, websocket: WebSocket, symbol: str = "all", timeframe: str = "1", data_type: str = "candles"):
        connection_key = f"{symbol}:{timeframe}:{data_type}"

        if connection_key in self.connections:
            for conn_info in list(self.connections[connection_key]):
                if conn_info.websocket == websocket:
                    await self._remove_connection_info(conn_info, connection_key)
                    break

    async def _remove_connection_info(self, conn_info: ConnectionInfo, connection_key: str):
        if connection_key in self.connections:
            self.connections[connection_key].discard(conn_info)
            if not self.connections[connection_key]:
                del self.connections[connection_key]
                if connection_key in self.aggregators:
                    del self.aggregators[connection_key]
                if connection_key in self.last_update_times:
                    del self.last_update_times[connection_key]
            logger.info(f"WebSocket disconnected for {connection_key}")

    async def handle_pong(self, websocket: WebSocket):
        for connection_key in self.connections:
            for conn_info in self.connections[connection_key]:
                if conn_info.websocket == websocket:
                    conn_info.last_pong = time.time()
                    conn_info.is_alive = True
                    logger.debug(f"Pong received from {connection_key}")
                    return

    async def broadcast_candle_update(self, message: str):
        try:
            data = json.loads(message)
            symbol = data.get("symbol", "")
            current_time = time.time()

            all_key = "all:1:candles"
            if all_key in self.connections:
                await self._broadcast_to_connections(self.connections[all_key], message)

            for connection_key in list(self.connections.keys()):
                if connection_key.startswith(f"{symbol}:") and connection_key.endswith(":candles") and connection_key in self.aggregators:
                    aggregator = self.aggregators[connection_key]
                    aggregated_candle = aggregator.add_minute_candle(data)

                    if aggregated_candle:
                        aggregated_message = json.dumps(aggregated_candle)
                        await self._broadcast_to_connections(
                            self.connections[connection_key],
                            aggregated_message
                        )
                        self.last_update_times[connection_key] = current_time
                    else:
                        last_update = self.last_update_times.get(connection_key, 0)
                        if current_time - last_update >= PERIODIC_UPDATE_INTERVAL:
                            current_candle = aggregator.get_current_candle()
                            if current_candle:
                                current_message = json.dumps(current_candle)
                                await self._broadcast_to_connections(
                                    self.connections[connection_key],
                                    current_message
                                )
                                self.last_update_times[connection_key] = current_time

        except Exception as e:
            logger.error(f"Error broadcasting candle update: {e}")

    async def broadcast_orderbook_update(self, message: str):
        try:
            data = json.loads(message)
            symbol = data.get("symbol", "")

            all_key = "all:1:orderbook"
            if all_key in self.connections:
                await self._broadcast_to_connections(self.connections[all_key], message)

            symbol_key = f"{symbol}:1:orderbook"
            if symbol_key in self.connections:
                await self._broadcast_to_connections(self.connections[symbol_key], message)

        except Exception as e:
            logger.error(f"Error broadcasting orderbook update: {e}")

    async def _broadcast_to_connections(self, connections: Set[ConnectionInfo], message: str):
        dead_connections = []
        for conn_info in connections:
            try:
                await conn_info.websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send message to {conn_info.connection_key}: {e}")
                dead_connections.append(conn_info)

        for conn_info in dead_connections:
            await self._remove_connection_info(conn_info, conn_info.connection_key)
