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
import json
import logging
from datetime import datetime, timedelta
import sys
import os

# Обработчик для websockets импорта
try:
    import websockets
except ImportError:
    websockets = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8022"
WEBSOCKET_URL = "ws://localhost:8022/ws"

# Настройки по умолчанию
DEFAULT_SYMBOL = "BTCUSDT"
TIMEFRAMES = ["1", "5", "15", "30", "1H", "4H", "1D"]

# Цвета для вывода в терминал
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "PURPLE": "\033[95m",
    "CYAN": "\033[96m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m"
}

def colored(text, color):
    """Добавляет цветовое оформление к тексту"""
    return f"{COLORS.get(color, '')}{text}{COLORS['ENDC']}"

def print_header(text):
    """Выводит заголовок теста"""
    print("\n" + "=" * 80)
    print(colored(f" {text} ", "BOLD").center(80, "="))
    print("=" * 80)

def print_test_result(test_name, success, message=""):
    """Выводит результат теста"""
    result = colored("✓ УСПЕХ", "GREEN") if success else colored("✗ ОШИБКА", "RED")
    print(f"{colored(test_name, 'BOLD')} - {result}")
    if message:
        print(f"  {message}")

async def test_health_endpoint():
    """Тестирование эндпоинта проверки здоровья системы"""
    print_header("Тест эндпоинта /health")
    success = False
    message = ""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    success = data.get("status") in ["healthy", "degraded"]
                    message = f"Статус системы: {data.get('status')}"
                else:
                    message = f"Код ответа: {response.status}, Ответ: {await response.text()}"
    except Exception as e:
        message = f"Ошибка запроса: {e}"

    print_test_result("Проверка здоровья системы", success, message)
    return success

async def test_symbols_endpoint():
    """Тестирование эндпоинта списка символов"""
    print_header("Тест эндпоинта /symbols")
    success = False
    message = ""
    symbols = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/symbols") as response:
                if response.status == 200:
                    data = await response.json()
                    symbols = data.get("symbols", [])
                    print(f"Доступные символы: {len(symbols)}")
                    for i, symbol in enumerate(symbols[:5]):
                        print(f"  {i+1}. {symbol}")
                    if len(symbols) > 5:
                        print(f"  ... и еще {len(symbols) - 5}")
                    success = len(symbols) > 0
                    message = f"Получено {len(symbols)} символов"
                else:
                    message = f"Код ответа: {response.status}, Ответ: {await response.text()}"
    except Exception as e:
        message = f"Ошибка запроса: {e}"

    print_test_result("Получение списка символов", success, message)
    return success, symbols

async def test_candles_endpoint(symbol=DEFAULT_SYMBOL, timeframes=None):
    """Тестирование эндпоинта свечей"""
    if timeframes is None:
        timeframes = ["1", "15", "1H"]

    print_header(f"Тест эндпоинта /candles для {symbol}")
    all_success = True

    for timeframe in timeframes:
        success = False
        message = ""

        try:
            url = f"{API_BASE_URL}/candles?symbol={symbol}&timeframe={timeframe}&limit=5"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        candles = await response.json()

                        if candles and len(candles) > 0:
                            print(f"\n{colored(f'Таймфрейм {timeframe}', 'CYAN')} (получено {len(candles)} свечей)")
                            for i, candle in enumerate(candles[:3]):
                                open_time = datetime.fromisoformat(candle["open_time"].replace('Z', '+00:00'))
                                print(f"  {i+1}. {open_time.strftime('%Y-%m-%d %H:%M')} - "
                                      f"O: {candle['open_price']}, H: {candle['high_price']}, "
                                      f"L: {candle['low_price']}, C: {candle['close_price']}, "
                                      f"V: {candle['volume']}")
                            success = True
                            message = f"Получено {len(candles)} свечей"
                        else:
                            message = "Получен пустой список свечей"
                    else:
                        message = f"Код ответа: {response.status}, Ответ: {await response.text()}"
        except Exception as e:
            message = f"Ошибка запроса: {e}"

        test_name = f"Свечи {symbol} ({timeframe})"
        print_test_result(test_name, success, message)
        all_success = all_success and success

    return all_success

async def test_orderbook_endpoint(symbol=DEFAULT_SYMBOL, levels=None):
    """Тестирование эндпоинта стакана заявок"""
    if levels is None:
        levels = [5, 10, 20]

    print_header(f"Тест эндпоинта /orderbook для {symbol}")
    all_success = True

    for level in levels:
        success = False
        message = ""

        try:
            url = f"{API_BASE_URL}/orderbook?symbol={symbol}&levels={level}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        if 'bids' in data and 'asks' in data:
                            bids_count = len(data['bids'])
                            asks_count = len(data['asks'])
                            print(f"\n{colored(f'Уровни: {level}', 'CYAN')} "
                                  f"(получено bids: {bids_count}, asks: {asks_count})")

                            print(f"  {colored('Продажи (Asks)', 'RED')}:")
                            for i, ask in enumerate(data['asks'][:3]):
                                print(f"    {i+1}. Цена: {ask['price']}, Объем: {ask['quantity']}")

                            print(f"  {colored('Покупки (Bids)', 'GREEN')}:")
                            for i, bid in enumerate(data['bids'][:3]):
                                print(f"    {i+1}. Цена: {bid['price']}, Объем: {bid['quantity']}")

                            success = True
                            message = f"Получено bids: {bids_count}, asks: {asks_count}"
                        else:
                            message = "Некорректный формат стакана"
                    else:
                        message = f"Код ответа: {response.status}, Ответ: {await response.text()}"
        except Exception as e:
            message = f"Ошибка запроса: {e}"

        test_name = f"Стакан {symbol} (уровни: {level})"
        print_test_result(test_name, success, message)
        all_success = all_success and success

    return all_success

async def test_price_endpoint(symbol=DEFAULT_SYMBOL, timeframes=None):
    """Тестирование эндпоинта цен"""
    if timeframes is None:
        timeframes = ["1", "1H"]

    print_header(f"Тест эндпоинта /price для {symbol}")
    all_success = True

    for timeframe in timeframes:
        success = False
        message = ""

        try:
            url = f"{API_BASE_URL}/price?symbol={symbol}&timeframe={timeframe}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        if 'current_price' in data and 'trend' in data:
                            trend_color = 'GREEN' if data['trend'] == 'up' else 'RED' if data['trend'] == 'down' else 'YELLOW'
                            print(f"\n{colored(f'Таймфрейм {timeframe}', 'CYAN')}")
                            print(f"  Текущая цена: {colored(data['current_price'], trend_color)}")
                            print(f"  Предыдущая цена: {data['previous_price']}")
                            print(f"  Изменение: {colored(data['change_absolute'], trend_color)} "
                                  f"({colored(data['change_percent'] + '%', trend_color)})")
                            print(f"  Тренд: {colored(data['trend'], trend_color)}")
                            print(f"  Объем: {data['volume']}")

                            success = True
                            message = f"Цена: {data['current_price']}, Тренд: {data['trend']}"
                        else:
                            message = "Некорректный формат данных о цене"
                    else:
                        message = f"Код ответа: {response.status}, Ответ: {await response.text()}"
        except Exception as e:
            message = f"Ошибка запроса: {e}"

        test_name = f"Цена {symbol} ({timeframe})"
        print_test_result(test_name, success, message)
        all_success = all_success and success

    return all_success

async def test_websocket_candles(symbol=DEFAULT_SYMBOL, timeframe="1", duration=10):
    """Тестирование WebSocket соединения для свечей"""
    print_header(f"Тест WebSocket для свечей {symbol} (таймфрейм {timeframe})")
    success = False
    message = ""
    candle_count = 0
    heartbeat_count = 0

    uri = f"{WEBSOCKET_URL}?symbol={symbol}&timeframe={timeframe}&type=candles"
    print(f"Подключение к {uri}")
    print(f"Ожидание данных в течение {duration} секунд...")

    try:
        # Проверяем, установлен ли websockets
        try:
            import websockets
        except ImportError:
            print(f"  {colored('⚠ Пакет websockets не установлен', 'YELLOW')}")
            print(f"  {colored('⚠ Установите его командой: pip install websockets', 'YELLOW')}")
            return False

        start_time = asyncio.get_event_loop().time()
        async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as websocket:
            while asyncio.get_event_loop().time() - start_time < duration:
                try:
                    task = asyncio.create_task(websocket.recv())
                    message_data = await asyncio.wait_for(task, timeout=1.0)
                    data = json.loads(message_data)

                    if data.get('type') == 'heartbeat':
                        heartbeat_count += 1
                        # Отправляем pong в ответ
                        pong_response = json.dumps({"type": "pong"})
                        await websocket.send(pong_response)
                        print(f"  {colored('♥ Heartbeat получен', 'PURPLE')} (всего: {heartbeat_count})")
                    elif 'timestamp' in data and 'symbol' in data:
                        candle_count += 1
                        timestamp = datetime.fromtimestamp(data['timestamp'] / 1000)
                        print(f"  {colored('📊 Свеча получена', 'BLUE')} (всего: {candle_count})")
                        print(f"    Время: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"    Символ: {data['symbol']}")
                        print(f"    OHLC: {data['open']} / {data['high']} / {data['low']} / {data['close']}")
                        print(f"    Объем: {data['volume']}, Сделки: {data['trades']}")
                    else:
                        print(f"  Получено неизвестное сообщение: {message_data[:100]}...")
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"  Ошибка обработки сообщения: {e}")

            # Корректное закрытие соединения
            await websocket.close()
            success = candle_count > 0 or heartbeat_count > 0
            message = f"Получено свечей: {candle_count}, heartbeat: {heartbeat_count}"

    except ConnectionRefusedError:
        message = "Соединение отклонено. Убедитесь, что сервер запущен и порт верный."
    except Exception as e:
        message = f"Ошибка WebSocket: {e}"
        if "server rejected WebSocket connection" in str(e):
            message += "\nСовет: Установите websockets в api-server: pip install websockets"

    print_test_result(f"WebSocket свечи {symbol} ({timeframe})", success, message)
    return success

async def test_websocket_orderbook(symbol=DEFAULT_SYMBOL, duration=10):
    """Тестирование WebSocket соединения для стакана заявок"""
    print_header(f"Тест WebSocket для стакана {symbol}")
    success = False
    message = ""
    orderbook_count = 0
    heartbeat_count = 0

    uri = f"{WEBSOCKET_URL}?symbol={symbol}&type=orderbook"
    print(f"Подключение к {uri}")
    print(f"Ожидание данных в течение {duration} секунд...")
    logger.info(f"Тестирование WebSocket стакана: {uri}")

    try:
        # Проверяем, установлен ли websockets
        if websockets is None:
            print(f"  {colored('⚠ Пакет websockets не установлен', 'YELLOW')}")
            print(f"  {colored('⚠ Установите его командой: pip install websockets', 'YELLOW')}")
            return False

        start_time = asyncio.get_event_loop().time()
        async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as websocket:
            while asyncio.get_event_loop().time() - start_time < duration:
                try:
                    task = asyncio.create_task(websocket.recv())
                    message_data = await asyncio.wait_for(task, timeout=1.0)
                    data = json.loads(message_data)

                    if data.get('type') == 'heartbeat':
                        heartbeat_count += 1
                        # Отправляем pong в ответ
                        pong_response = json.dumps({"type": "pong"})
                        await websocket.send(pong_response)
                        print(f"  {colored('♥ Heartbeat получен', 'PURPLE')} (всего: {heartbeat_count})")
                    elif 'bids' in data and 'asks' in data:
                        orderbook_count += 1
                        bids_count = len(data['bids'])
                        asks_count = len(data['asks'])
                        print(f"  {colored('📚 Стакан получен', 'BLUE')} (всего: {orderbook_count})")
                        print(f"    Символ: {data['symbol']}")
                        print(f"    Уровни: bids={bids_count}, asks={asks_count}")
                        if bids_count > 0 and asks_count > 0:
                            best_bid = float(data['bids'][0]['price'])
                            best_ask = float(data['asks'][0]['price'])
                            spread = best_ask - best_bid
                            spread_pct = (spread / best_bid) * 100
                            print(f"    Лучший бид: {best_bid}, Лучший аск: {best_ask}")
                            print(f"    Спред: {spread:.8f} ({spread_pct:.4f}%)")
                    else:
                        print(f"  Получено неизвестное сообщение: {message_data[:100]}...")
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"  Ошибка обработки сообщения: {e}")

            # Корректное закрытие соединения
            await websocket.close()
            success = orderbook_count > 0 or heartbeat_count > 0
            message = f"Получено обновлений стакана: {orderbook_count}, heartbeat: {heartbeat_count}"

    except ConnectionRefusedError:
        message = "Соединение отклонено. Убедитесь, что сервер запущен и порт верный."
    except Exception as e:
        message = f"Ошибка WebSocket: {e}"
        if "server rejected WebSocket connection" in str(e):
            message += "\nСовет: Установите websockets в api-server: pip install websockets"

    print_test_result(f"WebSocket стакан {symbol}", success, message)
    return success

async def run_comprehensive_tests():
    """Запуск всех тестов по порядку"""
    print_header("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ API И WEBSOCKET")

    results = {}

    # Тестирование статуса системы
    results["health"] = await test_health_endpoint()

    # Получение списка символов
    symbols_success, symbols = await test_symbols_endpoint()
    results["symbols"] = symbols_success

    # Если у нас есть символы, используем первый для тестов или BTCUSDT по умолчанию
    test_symbol = symbols[0] if symbols_success and symbols else DEFAULT_SYMBOL

    # Тестирование REST API эндпоинтов
    results["candles"] = await test_candles_endpoint(test_symbol)
    results["orderbook"] = await test_orderbook_endpoint(test_symbol)
    results["price"] = await test_price_endpoint(test_symbol)

    # Тестирование WebSocket соединений
    results["ws_candles"] = await test_websocket_candles(test_symbol, "1", 10)
    results["ws_orderbook"] = await test_websocket_orderbook(test_symbol, 10)

    # Вывод итогового отчета
    print_header("ИТОГОВЫЙ ОТЧЕТ")
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)

    print(f"Всего тестов: {total_tests}")
    print(f"Успешно: {passed_tests}")
    print(f"Провалено: {total_tests - passed_tests}")

    success_rate = (passed_tests / total_tests) * 100
    success_color = "GREEN" if success_rate == 100 else "YELLOW" if success_rate >= 70 else "RED"
    print(f"Успешность: {colored(f'{success_rate:.1f}%', success_color)}")

    print("\nРезультаты по компонентам:")
    print(f"  REST API: {colored('✓', 'GREEN') if all([results.get(key, False) for key in ['health', 'symbols', 'candles', 'orderbook', 'price']]) else colored('✗', 'RED')}")
    print(f"  WebSocket: {colored('✓', 'GREEN') if all([results.get(key, False) for key in ['ws_candles', 'ws_orderbook']]) else colored('✗', 'RED')}")

    return success_rate == 100

async def run_single_test_menu():
    """Меню для запуска отдельных тестов"""
    while True:
        print_header("МЕНЮ ТЕСТИРОВАНИЯ")
        print("1. Проверка статуса системы (health)")
        print("2. Получение списка символов (symbols)")
        print("3. Тестирование API свечей (candles)")
        print("4. Тестирование API стакана заявок (orderbook)")
        print("5. Тестирование API текущей цены (price)")
        print("6. Тестирование WebSocket свечей (ws_candles)")
        print("7. Тестирование WebSocket стакана (ws_orderbook)")
        print("8. Запустить все тесты")
        print("0. Выход")

        choice = input("\nВыберите тест (0-8): ").strip()

        if choice == "0":
            return

        if choice == "1":
            await test_health_endpoint()
        elif choice == "2":
            success, symbols = await test_symbols_endpoint()
            if success and symbols:
                selected_index = input(f"\nВыберите символ (1-{len(symbols)}, Enter для пропуска): ").strip()
                if selected_index and selected_index.isdigit() and 1 <= int(selected_index) <= len(symbols):
                    global DEFAULT_SYMBOL
                    DEFAULT_SYMBOL = symbols[int(selected_index) - 1]
                    print(f"Выбран символ: {DEFAULT_SYMBOL}")
        elif choice == "3":
            await test_candles_endpoint(DEFAULT_SYMBOL, TIMEFRAMES)
        elif choice == "4":
            await test_orderbook_endpoint(DEFAULT_SYMBOL)
        elif choice == "5":
            await test_price_endpoint(DEFAULT_SYMBOL, TIMEFRAMES)
        elif choice == "6":
            tf = input(f"Введите таймфрейм ({', '.join(TIMEFRAMES)}, Enter для 1): ").strip() or "1"
            duration = int(input("Длительность в секундах (Enter для 10): ").strip() or "10")
            await test_websocket_candles(DEFAULT_SYMBOL, tf, duration)
        elif choice == "7":
            duration = int(input("Длительность в секундах (Enter для 10): ").strip() or "10")
            await test_websocket_orderbook(DEFAULT_SYMBOL, duration)
        elif choice == "8":
            await run_comprehensive_tests()
        else:
            print(colored("Некорректный выбор!", "RED"))

        input("\nНажмите Enter для продолжения...")

async def main():
    print_header("CRYPTO API & WEBSOCKET ТЕСТЕР")
    print("Этот инструмент проверяет работоспособность всех API и WebSocket функций")
    print(f"Базовый URL API: {API_BASE_URL}")
    print(f"URL WebSocket: {WEBSOCKET_URL}")
    print("\nДоступные режимы:")
    print("1. Запустить все тесты автоматически")
    print("2. Выбрать отдельные тесты")
    print("0. Выход")

    choice = input("\nВыберите режим (0-2): ").strip()

    if choice == "0":
        return
    elif choice == "1":
        await run_comprehensive_tests()
    elif choice == "2":
        await run_single_test_menu()
    else:
        print(colored("Некорректный выбор!", "RED"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nТестирование прервано пользователем.")
    except Exception as e:
        print(f"\n{colored('Критическая ошибка:', 'RED')} {e}")
