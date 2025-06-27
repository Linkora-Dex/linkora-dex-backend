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
import asyncio
from datetime import datetime
from typing import Optional
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect
import config
from database import DatabaseManager
from websocket_manager import WebSocketManager
from utils import normalize_decimal_for_api

logger = logging.getLogger(__name__)

async def health_check(request):
    db_status = "healthy" if await db_manager.check_health() else "unhealthy"
    response_data = {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }
    return JSONResponse(response_data)

async def get_candles(request):
    try:
        symbol = request.query_params.get("symbol")
        timeframe = request.query_params.get("timeframe", "1")
        start_date_str = request.query_params.get("start_date")
        limit = int(request.query_params.get("limit", 500))

        if not symbol:
            return JSONResponse({"error": "symbol parameter is required"}, status_code=400)

        if timeframe not in config.TIMEFRAMES:
            return JSONResponse({
                "error": f"Invalid timeframe. Supported: {list(config.TIMEFRAMES.keys())}"
            }, status_code=400)

        if limit < 1 or limit > 5000:
            return JSONResponse({"error": "limit must be between 1 and 5000"}, status_code=400)

        start_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse({"error": "Invalid start_date format"}, status_code=400)

        candles = await db_manager.get_candles(symbol, timeframe, start_date, limit)

        formatted_candles = []
        for candle in candles:
            formatted_candles.append({
                "timestamp": int(candle["timestamp"]),
                "open_time": candle["open_time"].isoformat(),
                "close_time": candle["close_time"].isoformat(),
                "open_price": normalize_decimal_for_api(candle["open_price"]),
                "high_price": normalize_decimal_for_api(candle["high_price"]),
                "low_price": normalize_decimal_for_api(candle["low_price"]),
                "close_price": normalize_decimal_for_api(candle["close_price"]),
                "volume": normalize_decimal_for_api(candle["volume"]),
                "quote_volume": normalize_decimal_for_api(candle["quote_volume"]),
                "trades": candle["trades"],
                "taker_buy_volume": normalize_decimal_for_api(candle["taker_buy_volume"]),
                "taker_buy_quote_volume": normalize_decimal_for_api(candle["taker_buy_quote_volume"])
            })

        return JSONResponse(formatted_candles)

    except Exception as e:
        logger.error(f"Error in get_candles: {e}")
        return JSONResponse({"error": "Internal server error"}, status_code=500)

async def get_orderbook(request):
    try:
        symbol = request.query_params.get("symbol")
        levels = request.query_params.get("levels")

        if not symbol:
            return JSONResponse({"error": "symbol parameter is required"}, status_code=400)

        if levels:
            try:
                levels = int(levels)
                if levels not in config.ORDERBOOK_SUPPORTED_LEVELS:
                    return JSONResponse({
                        "error": f"Invalid levels. Supported: {config.ORDERBOOK_SUPPORTED_LEVELS}"
                    }, status_code=400)
            except ValueError:
                return JSONResponse({"error": "levels must be an integer"}, status_code=400)
        else:
            levels = config.ORDERBOOK_DEFAULT_LEVELS

        orderbook = await db_manager.get_orderbook(symbol, levels)

        if not orderbook:
            return JSONResponse({"error": "No orderbook data available for this symbol"}, status_code=404)

        return JSONResponse(orderbook)

    except Exception as e:
        logger.error(f"Error in get_orderbook: {e}")
        return JSONResponse({"error": "Internal server error"}, status_code=500)

async def get_symbols(request):
    try:
        symbols = await db_manager.get_symbols()
        return JSONResponse({"symbols": symbols})
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        return JSONResponse({"error": "Database error"}, status_code=500)

async def get_price(request):
    try:
        symbol = request.query_params.get("symbol")
        timeframe = request.query_params.get("timeframe", "1")

        if not symbol:
            return JSONResponse({"error": "symbol parameter is required"}, status_code=400)

        if timeframe not in config.TIMEFRAMES:
            return JSONResponse({
                "error": f"Invalid timeframe. Supported: {list(config.TIMEFRAMES.keys())}"
            }, status_code=400)

        connection_key = f"{symbol}:{timeframe}:candles"
        current_candle = None
        previous_candle = None

        if connection_key in ws_manager.aggregators:
            current_candle = ws_manager.aggregators[connection_key].get_current_candle()

        if timeframe == "1":
            candles = await db_manager.get_candles(symbol, timeframe, None, 2)
        else:
            candles = await db_manager.get_candles(symbol, timeframe, None, 1)

        if not candles and not current_candle:
            return JSONResponse({"error": "No data available for this symbol"}, status_code=404)

        if current_candle:
            current_price = float(current_candle["close"])
            current_timestamp = current_candle["timestamp"]
            current_volume = float(current_candle["volume"])

            if candles:
                previous_price = float(normalize_decimal_for_api(candles[0]["close_price"]))
            else:
                previous_price = current_price
        else:
            if len(candles) >= 2:
                current_candle_data = candles[0]
                previous_candle_data = candles[1]
            else:
                current_candle_data = candles[0]
                previous_candle_data = candles[0]

            current_price = float(normalize_decimal_for_api(current_candle_data["close_price"]))
            current_timestamp = int(current_candle_data["timestamp"])
            current_volume = float(normalize_decimal_for_api(current_candle_data["volume"]))
            previous_price = float(normalize_decimal_for_api(previous_candle_data["close_price"]))

        change_absolute = current_price - previous_price
        change_percent = (change_absolute / previous_price * 100) if previous_price != 0 else 0

        if change_absolute > 0:
            trend = "up"
        elif change_absolute < 0:
            trend = "down"
        else:
            trend = "neutral"

        response_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": f"{current_price:.8f}",
            "previous_price": f"{previous_price:.8f}",
            "change_absolute": f"{change_absolute:.8f}",
            "change_percent": f"{change_percent:.2f}",
            "trend": trend,
            "timestamp": current_timestamp,
            "volume": f"{current_volume:.8f}"
        }

        return JSONResponse(response_data)

    except Exception as e:
        logger.error(f"Error in get_price: {e}")
        return JSONResponse({"error": "Internal server error"}, status_code=500)

async def websocket_endpoint(websocket):
    await websocket.accept()
    symbol = websocket.query_params.get("symbol", "all")
    timeframe = websocket.query_params.get("timeframe", "1")
    data_type = websocket.query_params.get("type", "candles")

    if timeframe not in config.TIMEFRAMES:
        await websocket.close(code=1008, reason=f"Invalid timeframe: {timeframe}")
        return

    if data_type not in ["candles", "orderbook"]:
        await websocket.close(code=1008, reason=f"Invalid type: {data_type}")
        return

    await ws_manager.add_connection(websocket, symbol, timeframe, data_type)

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if message:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "pong":
                            await ws_manager.handle_pong(websocket)
                    except json.JSONDecodeError:
                        pass
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}:{timeframe}:{data_type}: {e}")
    finally:
        await ws_manager.remove_connection(websocket, symbol, timeframe, data_type)

# Инициализация глобальных объектов (будут заполнены в main.py)
db_manager = None
ws_manager = None

def initialize(database_manager, websocket_manager):
    global db_manager, ws_manager
    db_manager = database_manager
    ws_manager = websocket_manager
