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
import websockets
import json
import logging
import aiohttp
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8022"
WEBSOCKET_URL = "ws://localhost:8022/ws"
SYMBOL = "BTCUSDT"


def format_orderbook_display(orderbook_data):
    print("\n" + "=" * 80)
    print(f"ORDER BOOK - {orderbook_data['symbol']}")
    print(f"Timestamp: {datetime.fromtimestamp(orderbook_data['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Update ID: {orderbook_data['last_update_id']}")
    print("=" * 80)

    print(f"{'ASKS (Sell Orders)':^40} | {'BIDS (Buy Orders)':^40}")
    print(f"{'Price':<20} {'Quantity':<15} | {'Price':<20} {'Quantity':<15}")
    print("-" * 80)

    asks = orderbook_data['asks']
    bids = orderbook_data['bids']

    max_len = max(len(asks), len(bids))

    for i in range(max_len):
        ask_line = ""
        bid_line = ""

        if i < len(asks):
            ask = asks[i]
            ask_line = f"{float(ask['price']):<20.2f} {float(ask['quantity']):<15.8f}"
        else:
            ask_line = f"{'':^35}"

        if i < len(bids):
            bid = bids[i]
            bid_line = f"{float(bid['price']):<20.2f} {float(bid['quantity']):<15.8f}"
        else:
            bid_line = f"{'':^35}"

        print(f"{ask_line} | {bid_line}")

    if len(bids) > 0 and len(asks) > 0:
        spread = float(asks[0]['price']) - float(bids[0]['price'])
        spread_percent = (spread / float(bids[0]['price'])) * 100
        print("-" * 80)
        print(f"Spread: {spread:.2f} ({spread_percent:.4f}%)")
    print("=" * 80)


async def test_orderbook_api():
    print("Testing Order Book REST API...")

    async with aiohttp.ClientSession() as session:
        url = f"{API_BASE_URL}/orderbook?symbol={SYMBOL}&levels=10"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    format_orderbook_display(data)
                    return True
                else:
                    print(f"API Error: {response.status}")
                    text = await response.text()
                    print(f"Response: {text}")
                    return False
        except Exception as e:
            print(f"API Request failed: {e}")
            return False


async def websocket_orderbook_client():
    uri = f"{WEBSOCKET_URL}?symbol={SYMBOL}&type=orderbook"

    try:
        logger.info(f"Connecting to {uri}")
        async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as websocket:
            logger.info(f"Connected to WebSocket for {SYMBOL} orderbook")

            async for message in websocket:
                try:
                    data = json.loads(message)

                    if data.get('type') == 'heartbeat':
                        logger.debug("Received heartbeat, sending pong")
                        pong_response = json.dumps({"type": "pong"})
                        await websocket.send(pong_response)
                        continue

                    if 'symbol' in data and 'bids' in data and 'asks' in data:
                        format_orderbook_display(data)
                    else:
                        logger.info(f"Unknown message format: {message}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    logger.error(f"Raw message: {message}")
                except KeyError as e:
                    logger.error(f"Missing key in data: {e}")
                    logger.error(f"Raw message: {message}")

    except websockets.exceptions.ConnectionClosed:
        logger.warning("WebSocket connection closed")
    except websockets.exceptions.InvalidURI:
        logger.error(f"Invalid WebSocket URI: {uri}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def combined_demo():
    print("=" * 80)
    print("CRYPTO ORDER BOOK DEMO")
    print("=" * 80)

    api_success = await test_orderbook_api()

    if api_success:
        print("\nStarting WebSocket real-time updates...")
        print("Press Ctrl+C to stop")
        await websocket_orderbook_client()
    else:
        print("API test failed. Check if the server is running.")


async def compare_symbols_demo():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    print("=" * 80)
    print("MULTI-SYMBOL ORDER BOOK COMPARISON")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        for symbol in symbols:
            url = f"{API_BASE_URL}/orderbook?symbol={symbol}&levels=5"

            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        print(f"\n{symbol} - Top 5 Levels")
                        print("-" * 50)

                        if data['bids'] and data['asks']:
                            best_bid = float(data['bids'][0]['price'])
                            best_ask = float(data['asks'][0]['price'])
                            spread = best_ask - best_bid
                            spread_percent = (spread / best_bid) * 100

                            print(f"Best Bid: {best_bid:.2f}")
                            print(f"Best Ask: {best_ask:.2f}")
                            print(f"Spread: {spread:.2f} ({spread_percent:.4f}%)")

                    else:
                        print(f"Failed to get data for {symbol}: {response.status}")

            except Exception as e:
                print(f"Error fetching {symbol}: {e}")


if __name__ == "__main__":
    print("Select demo mode:")
    print("1. Single symbol with WebSocket updates")
    print("2. Multi-symbol comparison")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        asyncio.run(combined_demo())
    elif choice == "2":
        asyncio.run(compare_symbols_demo())
    else:
        print("Invalid choice")
        asyncio.run(combined_demo())