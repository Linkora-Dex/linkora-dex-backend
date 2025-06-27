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
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WEBSOCKET_URL = "ws://localhost:8022/ws"
SYMBOL = "BTCUSDT"
# ["1", "5", "15", "30", "1H", "4H", "1D"]
TIMEFRAMES = {
    "1": 1, "3": 3, "5": 5, "15": 15, "30": 30, "45": 45,
    "1H": 60, "2H": 120, "3H": 180, "4H": 240,
    "1D": 1440, "1W": 10080, "1M": 43200
}

TIMEFRAME = "5"  # Можно изменить на "1", "5", "15", "30", "60", "240", "480", "720", "1440"


async def websocket_client():
    uri = f"{WEBSOCKET_URL}?symbol={SYMBOL}&timeframe={TIMEFRAME}"

    try:
        logger.info(f"Connecting to {uri}")
        async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as websocket:
            logger.info(f"Connected to WebSocket for {SYMBOL} {TIMEFRAME}m timeframe")

            async for message in websocket:
                try:
                    data = json.loads(message)

                    # Обработка heartbeat сообщений
                    if data.get('type') == 'heartbeat':
                        logger.debug("Received heartbeat, sending pong")
                        pong_response = json.dumps({"type": "pong"})
                        await websocket.send(pong_response)
                        continue

                    # Обработка свечных данных
                    if 'timestamp' in data and 'symbol' in data:
                        timestamp = datetime.fromtimestamp(data['timestamp'] / 1000)

                        print(f"\n[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {data['symbol']} ({TIMEFRAME}m)")
                        print(f"  Open:   {data['open']}")
                        print(f"  High:   {data['high']}")
                        print(f"  Low:    {data['low']}")
                        print(f"  Close:  {data['close']}")
                        print(f"  Volume: {data['volume']}")
                        print(f"  Trades: {data['trades']}")
                        print("-" * 50)
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


async def multi_timeframe_client():
    """Демо клиент для множественных таймфреймов"""
    timeframes = ["1H"]
    #["1", "5", "15", "30", "1H", "4H", "1D"]

    async def single_connection(tf):
        uri = f"{WEBSOCKET_URL}?symbol={SYMBOL}&timeframe={tf}"
        try:
            async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as websocket:
                logger.info(f"Connected to {SYMBOL} {tf}m")

                async for message in websocket:
                    try:
                        data = json.loads(message)

                        if data.get('type') == 'heartbeat':
                            pong_response = json.dumps({"type": "pong"})
                            await websocket.send(pong_response)
                            continue

                        if 'timestamp' in data and 'symbol' in data:
                            timestamp = datetime.fromtimestamp(data['timestamp'] / 1000)
                            print(f"[{tf}m] {timestamp.strftime('%H:%M:%S')} | {data['symbol']} | C: {data['close']} | V: {data['volume']}")

                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error in {tf}m connection: {e}")

    # Запускаем все соединения параллельно
    tasks = [single_connection(tf) for tf in timeframes]
    await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    print(f"Starting WebSocket demo client for {SYMBOL}")
    print(f"Timeframe: {TIMEFRAME} minutes")
    print("Available options:")
    print("  1. Single timeframe client (current)")
    print("  2. Multi timeframe client")
    print("Press Ctrl+C to stop")
    print("-" * 50)

    mode = input("Choose mode (1 or 2, default 1): ").strip()

    while True:
        try:
            if mode == "2":
                await multi_timeframe_client()
            else:
                await websocket_client()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())


"""
## ОБНОВЛЕННЫЙ ДЕМО СКРИПТ С ПОДДЕРЖКОЙ ТАЙМФРЕЙМОВ## КЛЮЧЕВЫЕ ОБНОВЛЕНИЯ ДЕМО СКРИПТА

### 1. **Поддержка таймфреймов**
- Добавлен параметр `TIMEFRAME = "5"`
- URL формируется как `ws://localhost:8022/ws?symbol=BTCUSDT&timeframe=5`

### 2. **Heartbeat/Pong обработка**
- Автоматический ответ на heartbeat сообщения
- Отправка `{"type": "pong"}` в ответ на heartbeat

### 3. **Улучшенный вывод**
- Показывает таймфрейм в выводе: `BTCUSDT (5m)`
- Полный timestamp с датой и временем
- Более читаемое форматирование

### 4. **Мульти-таймфрейм режим**
- Режим 2: одновременное подключение к 1m, 5m, 15m
- Параллельное отображение данных разных таймфреймов
- Компактный вывод для сравнения

### 5. **Отключение автоматического ping**
- `ping_interval=None, ping_timeout=None`
- Используется кастомный heartbeat протокол сервера

### ИСПОЛЬЗОВАНИЕ

**Режим 1** - Один таймфрейм:
```bash
python websocket_demo_updated.py
# Выберите 1, будет подключение к 5-минутному таймфрейму
```

**Режим 2** - Множественные таймфреймы:
```bash
python websocket_demo_updated.py
# Выберите 2, одновременно 1m, 5m, 15m
```

**Изменение таймфрейма:**
```python
TIMEFRAME = "15"  # для 15-минутных свечей
TIMEFRAME = "60"  # для часовых свечей
```

Теперь демо корректно работает с новым API и показывает агрегированные данные нужного таймфрейма.
"""