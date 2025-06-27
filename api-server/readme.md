# API Server Documentation

## Архитектура

**Framework:** Starlette (ASGI) - асинхронный веб-фреймворк  
**Database:** TimescaleDB (PostgreSQL) с оптимизацией для временных рядов  
**Real-time:** WebSocket + Redis pub/sub для live обновлений  
**Data Sources:** Binance API через data-collector сервис  
**Language:** Python 3.11 с asyncio

### Компоненты системы

- **DatabaseManager** - асинхронная работа с TimescaleDB
- **WebSocketManager** - управление WebSocket соединениями и агрегация
- **CandleAggregator** - real-time агрегация свечей по таймфреймам
- **Redis pub/sub** - получение обновлений от data-collector

## Конфигурация

### Переменные окружения
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_data
DB_USER=crypto_user
DB_PASSWORD=crypto_pass

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# WebSocket
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_PONG_TIMEOUT=60
WEBSOCKET_CLEANUP_INTERVAL=120
```

### Поддерживаемые таймфреймы
```python
TIMEFRAMES = {
    "1": 1,        # 1 минута
    "3": 3,        # 3 минуты
    "5": 5,        # 5 минут
    "15": 15,      # 15 минут
    "30": 30,      # 30 минут
    "45": 45,      # 45 минут
    "1H": 60,      # 1 час
    "2H": 120,     # 2 часа
    "3H": 180,     # 3 часа
    "4H": 240,     # 4 часа
    "1D": 1440,    # 1 день
    "1W": 10080,   # 1 неделя
    "1M": 43200    # 1 месяц
}
```

## REST API Endpoints

### 1. Health Check
**GET** `/health`

Проверка состояния системы и подключений к базе данных.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-06-07T16:43:26.123456",
    "database": "healthy"
}
```

**Статусы:**
- `healthy` - все сервисы работают корректно
- `degraded` - есть проблемы с подключениями (database: "unhealthy")

---

### 2. Symbols List
**GET** `/symbols`

Получение списка доступных торговых пар.

**Response:**
```json
{
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
}
```

**Error Response:**
```json
{
    "error": "Database error"
}
```

---

### 3. Candle Data
**GET** `/candles`

Получение исторических свечных данных с поддержкой агрегации по таймфреймам.

**Parameters:**
- `symbol` (required) - торговая пара (например: BTCUSDT)
- `timeframe` (optional) - таймфрейм свечей (по умолчанию: "1")
- `limit` (optional) - количество записей (по умолчанию: 500, макс: 5000)
- `start_date` (optional) - начальная дата в ISO формате

**Example Requests:**
```bash
# Последние 100 минутных свечей для BTC/USDT
GET /candles?symbol=BTCUSDT&timeframe=1&limit=100

# Последние 50 часовых свечей для ETH/USDT
GET /candles?symbol=ETHUSDT&timeframe=1H&limit=50

# Данные с конкретной даты
GET /candles?symbol=BTCUSDT&timeframe=1D&start_date=2025-06-01T00:00:00Z&limit=30
```

**Response:**
```json
[
    {
        "timestamp": 1717524000000,
        "open_time": "2025-06-04T19:00:00",
        "close_time": "2025-06-04T19:59:59", 
        "open_price": "105200.45000000",
        "high_price": "105890.12000000",
        "low_price": "104987.33000000", 
        "close_price": "105654.78000000",
        "volume": "123.45678900",
        "quote_volume": "12345678.90123456",
        "trades": 1547,
        "taker_buy_volume": "62.34567890",
        "taker_buy_quote_volume": "6543210.12345678"
    }
]
```

**Error Responses:**
```json
// 400 - Missing symbol
{"error": "symbol parameter is required"}

// 400 - Invalid timeframe  
{"error": "Invalid timeframe. Supported: ['1', '3', '5', '15', '30', '45', '1H', '2H', '3H', '4H', '1D', '1W', '1M']"}

// 400 - Invalid limit
{"error": "limit must be between 1 and 5000"}

// 400 - Invalid date format
{"error": "Invalid start_date format"}

// 500 - Server error
{"error": "Internal server error"}
```

---

### 4. OrderBook Data
**GET** `/orderbook`

Получение данных стакана заявок (bids/asks) для торговой пары.

**Parameters:**
- `symbol` (required) - торговая пара (например: BTCUSDT)
- `levels` (optional) - количество уровней (5, 10, 20, по умолчанию: 20)

**Example Requests:**
```bash
# Полный orderbook для BTC/USDT (20 уровней)
GET /orderbook?symbol=BTCUSDT

# Топ 10 уровней orderbook для ETH/USDT
GET /orderbook?symbol=ETHUSDT&levels=10

# Топ 5 уровней orderbook для SOL/USDT
GET /orderbook?symbol=SOLUSDT&levels=5
```

**Response:**
```json
{
    "symbol": "BTCUSDT",
    "timestamp": 1749134109593,
    "last_update_id": 70466589812,
    "bids": [
        {
            "price": "104200.71000000",
            "quantity": "7.07062000"
        },
        {
            "price": "104200.70000000",
            "quantity": "0.01175000"
        }
    ],
    "asks": [
        {
            "price": "104200.72000000", 
            "quantity": "3.24960000"
        },
        {
            "price": "104200.73000000",
            "quantity": "0.00028000"
        }
    ]
}
```

**Error Responses:**
```json
// 400 - Missing symbol
{"error": "symbol parameter is required"}

// 400 - Invalid levels
{"error": "Invalid levels. Supported: [5, 10, 20]"}

// 400 - Non-integer levels
{"error": "levels must be an integer"}

// 404 - No data
{"error": "No orderbook data available for this symbol"}

// 500 - Server error
{"error": "Internal server error"}
```

---

### 5. Price Analytics
**GET** `/price`

Получение текущей цены с аналитикой изменений для указанного таймфрейма.

**Parameters:**
- `symbol` (required) - торговая пара (например: BTCUSDT)
- `timeframe` (optional) - таймфрейм для анализа (по умолчанию: "1")

**Example Requests:**
```bash
# Текущая цена BTC на часовом таймфрейме
GET /price?symbol=BTCUSDT&timeframe=1H

# Текущая цена ETH на 5-минутном таймфрейме
GET /price?symbol=ETHUSDT&timeframe=5

# По умолчанию минутный таймфрейм
GET /price?symbol=BTCUSDT
```

**Response:**
```json
{
    "symbol": "BTCUSDT",
    "timeframe": "1H", 
    "current_price": "105654.78000000",
    "previous_price": "105200.45000000",
    "change_absolute": "454.33000000",
    "change_percent": "0.43",
    "trend": "up",
    "timestamp": 1717524000000,
    "volume": "123.45678900"
}
```

**Trend Values:**
- `"up"` - цена выросла относительно предыдущего периода
- `"down"` - цена упала относительно предыдущего периода  
- `"neutral"` - цена не изменилась

**Logic:**
1. Проверяет текущую свечу в real-time агрегаторе
2. Если нет - берет последние данные из базы
3. Сравнивает с предыдущим периодом того же таймфрейма
4. Вычисляет абсолютное и процентное изменение

**Error Responses:**
```json
// 400 - Missing symbol
{"error": "symbol parameter is required"}

// 400 - Invalid timeframe
{"error": "Invalid timeframe. Supported: ['1', '3', '5', ...]"}

// 404 - No data
{"error": "No data available for this symbol"}

// 500 - Server error  
{"error": "Internal server error"}
```

## WebSocket API

### Connection URL
```
ws://localhost:8000/ws
```

### Connection Parameters
- `symbol` (optional) - торговая пара (по умолчанию: "all")
- `timeframe` (optional) - таймфрейм для агрегации (по умолчанию: "1") 
- `type` (optional) - тип данных: "candles" или "orderbook" (по умолчанию: "candles")

### Connection Examples
```javascript
// Подключение ко всем символам (1-минутные свечи)
const ws1 = new WebSocket('ws://localhost:8000/ws?symbol=all&timeframe=1&type=candles');

// Подключение к BTCUSDT с 5-минутной агрегацией
const ws2 = new WebSocket('ws://localhost:8000/ws?symbol=BTCUSDT&timeframe=5&type=candles');

// Подключение к orderbook BTC
const ws3 = new WebSocket('ws://localhost:8000/ws?symbol=BTCUSDT&type=orderbook');

// Подключение к часовым свечам BTC  
const ws4 = new WebSocket('ws://localhost:8000/ws?symbol=BTCUSDT&timeframe=1H&type=candles');
```

### Real-time Data Messages

#### Candle Update
Обновления свечей в реальном времени с автоматической агрегацией:

```json
{
    "symbol": "BTCUSDT",
    "timestamp": 1717524000000,
    "open": "105200.45000000",
    "high": "105890.12000000",
    "low": "104987.33000000", 
    "close": "105654.78000000",
    "volume": "123.45678900",
    "quote_volume": "12345678.90123456",
    "trades": 1547
}
```

#### OrderBook Update
Обновления orderbook в реальном времени:

```json
{
    "symbol": "BTCUSDT",
    "timestamp": 1749134109593,
    "last_update_id": 70466589812,
    "bids": [
        {
            "price": "104200.71000000",
            "quantity": "7.07062000"
        }
    ],
    "asks": [
        {
            "price": "104200.72000000", 
            "quantity": "3.24960000"
        }
    ]
}
```

#### Heartbeat Protocol
Система отправляет heartbeat каждые 30 секунд:

```json
{
    "type": "heartbeat",
    "timestamp": 1717524123456
}
```

Клиент должен отвечать pong сообщением:
```json
{
    "type": "pong"
}
```

**Connection Management:**
- Автоматическая очистка неактивных соединений через 60 секунд
- Периодические обновления каждые 5 секунд для текущих свечей
- Удаление соединений при отсутствии pong ответов

### WebSocket Error Codes
- `1008` - Invalid timeframe or data type parameter
- `1000` - Normal closure

## Data Flow Architecture

### 1. Data Collection
```
Binance API → data-collector → TimescaleDB
                ↓
            Redis pub/sub
```

### 2. Real-time Processing  
```
Redis → WebSocketManager → CandleAggregator → WebSocket clients
```

### 3. API Requests
```
HTTP Request → api_handlers → DatabaseManager → TimescaleDB
```

## Database Schema

### Candles Table
```sql
CREATE TABLE candles (
    symbol TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL, 
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    quote_volume DECIMAL(20,8) NOT NULL,
    trades INTEGER NOT NULL,
    taker_buy_volume DECIMAL(20,8) NOT NULL,
    taker_buy_quote_volume DECIMAL(20,8) NOT NULL,
    PRIMARY KEY (symbol, timestamp)
);
```

### OrderBook Data Table
```sql
CREATE TABLE orderbook_data (
    symbol TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    last_update_id BIGINT NOT NULL,
    bids JSONB NOT NULL,
    asks JSONB NOT NULL,
    PRIMARY KEY (symbol, timestamp)
);
```

## Aggregation Logic

### Timeframe Aggregation
Система автоматически агрегирует минутные свечи в более крупные таймфреймы:

**Database Aggregation (Historical Data):**
- Использует TimescaleDB `time_bucket()` функцию
- `first()` для open price, `last()` для close price
- `max()` и `min()` для high/low prices
- `sum()` для volume, quote_volume, trades

**Real-time Aggregation (Live Data):**
- `CandleAggregator` обрабатывает входящие минутные свечи
- Определяет начало периода на основе таймфрейма
- Обновляет текущую свечу или создает новую
- Отправляет завершенные свечи через WebSocket

### Period Calculation Examples
```python
# 5-минутные свечи: округление до 0, 5, 10, 15... минут
period_start = dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)

# Часовые свечи: округление до начала часа
period_start = dt.replace(minute=0, second=0, microsecond=0) 

# 4-часовые свечи: округление до 0, 4, 8, 12, 16, 20 часов
period_start = dt.replace(hour=(dt.hour // 4) * 4, minute=0, second=0, microsecond=0)
```

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (missing/invalid parameters)
- `404` - Not Found (no data available)
- `500` - Internal Server Error

### Logging
Все ошибки логируются с детальной информацией:
```python
logger.error(f"Error in get_candles: {e}")
logger.warning(f"Failed to send heartbeat to {connection_key}: {e}")
logger.info(f"WebSocket connected for {connection_key}")
```

## Performance Features

### Database Optimization
- Connection pooling (2-10 connections)
- Prepared statements через asyncpg
- TimescaleDB hypertables для эффективных временных запросов
- Индексы по symbol и timestamp

### WebSocket Optimization  
- Групповая рассылка сообщений
- Автоматическая очистка мертвых соединений
- Throttling обновлений (не чаще 5 секунд)
- Асинхронная обработка всех операций

### Memory Management
- Декимальные числа нормализуются для API ответов
- Ограничение на количество уровней orderbook
- Ограничение на лимит свечей (максимум 5000)

## Security & CORS

### CORS Configuration
```python
Middleware(CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)
```

### Input Validation
- Проверка существования required параметров
- Валидация таймфреймов против whitelist
- Ограничения на числовые параметры (limit, levels)
- Проверка формата дат

## Monitoring & Health

### Health Check Details
Endpoint `/health` проверяет:
- Подключение к базе данных (SELECT 1)
- Статус системы в целом
- Timestamp последней проверки

### Logging Levels
- `INFO` - подключения, операции, статистика  
- `DEBUG` - детальная информация WebSocket
- `ERROR` - ошибки подключений и обработки
- `WARNING` - проблемы с отправкой сообщений

### Metrics Available
- Количество активных WebSocket соединений
- Частота обновлений по каналам
- Статистика агрегаторов по таймфреймам
- Database connection pool status