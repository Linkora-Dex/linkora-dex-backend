# Linkora DEX Backend Platform

Высокопроизводительная платформа для сбора, хранения и предоставления данных криптовалютных рынков в реальном времени с поддержкой DEX ордеров, множественных таймфреймов и WebSocket соединений.

## Архитектура платформы

### Основные компоненты
- **📊 Data Collector** - Асинхронный сбор данных с Binance API (candles, orderbook)
- **🚀 API Server** - REST API и WebSocket сервер с real-time агрегацией
- **📋 Order System** - Микросервисная система обработки DEX ордеров
- **🗄️ TimescaleDB** - Оптимизированная БД временных рядов
- **⚡ Redis** - Pub/sub брокер для real-time уведомлений

### Технологический стек
- **Backend**: Python 3.11+ с asyncio
- **API Framework**: Starlette (ASGI)
- **Database**: TimescaleDB (PostgreSQL) + asyncpg
- **Cache & Pub/Sub**: Redis
- **Blockchain**: Web3.py для Ethereum/Hardhat
- **Containerization**: Docker & Docker Compose

### Архитектурная диаграмма
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Collector│    │   API Server    │    │  Order System   │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Source    │ │    │ │    REST     │ │    │ │   Event     │ │
│ │     API     │ │    │ │     API     │ │    │ │ Processor   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ OrderBook   │ │    │ │  WebSocket  │ │    │ │   Order     │ │
│ │ Collector   │ │    │ │   Manager   │ │    │ │     API     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
            ┌─────────────────────┼─────────────────────┐
            │                    │                     │
    ┌───────▼────────┐   ┌───────▼────────┐   ┌───────▼────────┐
    │  TimescaleDB   │   │     Redis      │   │   Blockchain   │
    │   (Primary)    │   │   (Pub/Sub)    │   │   (Hardhat)    │
    └────────────────┘   └────────────────┘   └────────────────┘
```

## Быстрый старт

### Требования
- Docker & Docker Compose
- 4GB+ RAM
- 10GB+ свободного места

### Установка и запуск
```bash
# Клонирование репозитория
git clone <repository-url>
cd Linkora-Dex-Backend

# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Проверка здоровья системы
curl http://localhost:8022/health  # API Server
curl http://localhost:8080/health  # Order System
```

### Быстрая проверка функциональности
```bash
# Crypto Data API
curl "http://localhost:8022/symbols"                    # Доступные символы
curl "http://localhost:8022/candles?symbol=BTCUSDT"     # Свечные данные
curl "http://localhost:8022/orderbook?symbol=BTCUSDT"   # OrderBook данные

# Order System API  
curl "http://localhost:8080/orders/pending"             # Pending ордера
curl "http://localhost:8080/statistics"                 # Статистика ордеров
```

## Сервисы платформы

### 📊 Data Collector Service
> **Порт**: Внутренний сервис  
> **Назначение**: Сбор данных с Binance API  
> **Документация**: [data-collector/readme.md](data-collector/readme.md)

**Основные функции:**
- Асинхронный сбор klines/candles данных
- Параллельный сбор orderbook данных
- Автоматическое восстановление состояния
- Нормализация научной нотации (5E-8 → 0.00000005)
- Real-time публикация в Redis

**Конфигурация:**
```python
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT']
START_DATE = datetime(2025, 1, 1)
REALTIME_INTERVAL = 0.5  # секунды
ORDERBOOK_LEVELS = 20
```

**Алгоритм работы:**
1. **Исторический режим**: Сбор данных с START_DATE до текущего момента
2. **Real-time режим**: Обновления каждые 0.5 секунды
3. **Публикация**: Redis channels `candles:all`, `orderbook:all`

---

### 🚀 API Server
> **Порт**: 8022  
> **Назначение**: REST API + WebSocket сервер  
> **Документация**: [api-server/readme.md](api-server/readme.md)

**REST API Endpoints:**
```http
GET /health                              # Статус системы
GET /symbols                             # Список торговых пар  
GET /candles?symbol=BTCUSDT&timeframe=1H # Свечные данные с агрегацией
GET /orderbook?symbol=BTCUSDT&levels=10  # OrderBook данные
GET /price?symbol=BTCUSDT&timeframe=1H   # Текущая цена с аналитикой
```

**WebSocket API:**
```javascript
// Real-time свечи с агрегацией по таймфреймам
ws://localhost:8022/ws?symbol=BTCUSDT&timeframe=5&type=candles

// Real-time orderbook
ws://localhost:8022/ws?symbol=BTCUSDT&type=orderbook
```

**Поддерживаемые таймфреймы:**
`1`, `3`, `5`, `15`, `30`, `45`, `1H`, `2H`, `3H`, `4H`, `1D`, `1W`, `1M`

**Ключевые особенности:**
- Real-time агрегация минутных свечей в крупные таймфреймы
- WebSocket heartbeat протокол (30 сек)
- Автоматическая очистка неактивных соединений
- TimescaleDB integration с connection pooling

---

### 📋 Order System  
> **Порт**: 8080  
> **Назначение**: Обработка DEX ордеров  
> **Документация**: [order_system/readme.md](order_system/readme.md)

**Микросервисы:**
- **Order API** (port 8080) - REST API для ордеров
- **Event Processor** (internal) - Blockchain events scanner

**Order API Endpoints:**
```http
GET /orders/pending?limit=100&offset=0                    # PENDING ордера
GET /orders/executed?limit=100&offset=0                   # EXECUTED ордера  
GET /orders/cancelled?limit=100&offset=0                  # CANCELLED ордера
GET /users/{address}/orders?status=executed               # Ордера пользователя
GET /orders/{id}                                          # Детали ордера
GET /orders/{id}/events                                   # События ордера
GET /statistics                                           # Статистика ордеров
```

**Event Processor функции:**
- Сканирование blockchain событий (OrderCreated, OrderExecuted, OrderCancelled)
- Параллельная обработка блоков при восстановлении
- Автоматическое восстановление после сбоев (recovery mode)
- 100% предотвращение дубликатов событий

**Схема ордера:**
```json
{
  "id": 5,
  "user_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
  "token_in": "0x0000000000000000000000000000000000000000",
  "token_out": "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0",
  "amount_in": "0.05",
  "target_price": "0.8944299",
  "order_type": "LIMIT",
  "status": "EXECUTED",
  "created_at": "2025-06-07T09:38:39+00:00",
  "executed_at": "2025-06-07T09:35:52.244466+00:00"
}
```

## Database Schema

### TimescaleDB Tables

**Crypto Market Data:**
```sql
-- Свечные данные (hypertable, сжатие 7 дней)
candles (symbol, timestamp, OHLCV, trades, taker_buy_*)

-- OrderBook данные (hypertable, сжатие 1 день)  
orderbook_data (symbol, timestamp, last_update_id, bids JSONB, asks JSONB)

-- Состояние сборщика данных
collector_state (symbol, last_timestamp, is_realtime, last_updated)
```

**Order System Data:**
```sql
-- Основные данные ордеров
orders (id, user_address, token_in, token_out, amount_in, target_price, 
        order_type, status, created_at, executed_at, ...)

-- История событий ордеров (hypertable)
order_events (order_id, event_type, old_status, new_status, timestamp, ...)

-- Состояние blockchain scanner
system_state (component_name, last_processed_block, status, updated_at)

-- Обработанные события (предотвращение дубликатов)
processed_events (tx_hash, log_index, event_type, processed_at)
```

## Configuration

### Environment Variables
```bash
# Database
DB_HOST=timescaledb
DB_PORT=5432
DB_NAME=crypto_data
DB_USER=crypto_user
DB_PASSWORD=crypto_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# API Servers
API_HOST=0.0.0.0
API_PORT=8000        # API Server
ORDER_API_PORT=8080  # Order System API

# Binance Data Collection
BINANCE_BASE_URL=https://api.binance.com
SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,BNBUSDT
START_DATE=2025-01-01
REALTIME_INTERVAL=0.5

# Blockchain (Order System)
WEB3_PROVIDER=http://127.0.0.1:8545
TRADING_ADDRESS=0x...
ROUTER_ADDRESS=0x...
```

### Docker Compose Services
```yaml
services:
  timescaledb:       # Основная база данных
  redis:             # Pub/sub и кэширование
  data-collector:    # Сбор данных с Binance  
  api-server:        # REST API + WebSocket (port 8022)
  order-api:         # Order System API (port 8080)
  order-events:      # Blockchain events processor
```

## Data Flow Architecture

### 1. Market Data Pipeline
```
Binance API → Data Collector → TimescaleDB → Redis pub/sub → API Server → WebSocket clients
```

### 2. Order Processing Pipeline  
```
Blockchain → Event Processor → TimescaleDB → Order API → REST clients
```

### 3. Real-time Aggregation
```
1m candles → CandleAggregator → 5m/1H/1D candles → WebSocket broadcast
```

## Monitoring & Diagnostics

### Health Checks
```bash
# Все сервисы
curl http://localhost:8022/health  # API Server
curl http://localhost:8080/health  # Order System

# Проверка данных
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT 'candles' as table_name, COUNT(*) FROM candles
UNION ALL  
SELECT 'orderbook_data', COUNT(*) FROM orderbook_data
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;"
```

### Диагностические утилиты
```bash
# Создание monitoring скриптов
./monitoring/setup_monitoring.sh

# Быстрая диагностика
./quick_check.sh

# Полная диагностика
./full_diagnostics.sh

# При критических проблемах
./emergency_fix.sh
```

### Логи сервисов
```bash
# Мониторинг в реальном времени
docker-compose logs -f data-collector  # Сбор данных
docker-compose logs -f api-server      # API сервер
docker-compose logs -f order-events    # Blockchain scanner

# Фильтрация ошибок
docker-compose logs data-collector | grep -E "(ERROR|WARN|orderbook)"
```

## Performance Features

### Database Optimization
- **TimescaleDB hypertables** с автоматическим партиционированием
- **Connection pooling** (2-10 соединений на сервис)
- **Сжатие данных**: 7 дней (candles), 1 день (orderbook)
- **Индексы** по symbol, timestamp для быстрых запросов

### Real-time Processing
- **Асинхронная архитектура** с параллельной обработкой
- **Redis pub/sub** для real-time уведомлений
- **WebSocket throttling** (5 сек интервал обновлений)
- **Batch operations** до 1000 записей за запрос

### Scalability
- **Горизонтальное масштабирование** через дополнительные символы
- **Микросервисная архитектура** с независимыми компонентами
- **Docker containers** для простого развертывания
- **Load balancing** поддержка для API endpoints

## API Examples

### Market Data API
```bash
# Получение символов
curl "http://localhost:8022/symbols"

# Часовые свечи BTC
curl "http://localhost:8022/candles?symbol=BTCUSDT&timeframe=1H&limit=24"

# OrderBook с 10 уровнями
curl "http://localhost:8022/orderbook?symbol=ETHUSDT&levels=10"

# Текущая цена с трендом
curl "http://localhost:8022/price?symbol=BTCUSDT&timeframe=1H"
```

### Order System API
```bash
# Статистика ордеров
curl "http://localhost:8080/statistics"

# Executed ордера с пагинацией
curl "http://localhost:8080/orders/executed?limit=10&offset=0"

# Ордера пользователя
curl "http://localhost:8080/users/0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC/orders"

# События ордера
curl "http://localhost:8080/orders/5/events"
```

### WebSocket Examples
```javascript
// Real-time 5-минутные свечи BTCUSDT
const ws1 = new WebSocket('ws://localhost:8022/ws?symbol=BTCUSDT&timeframe=5&type=candles');

// Real-time orderbook ETHUSDT
const ws2 = new WebSocket('ws://localhost:8022/ws?symbol=ETHUSDT&type=orderbook');

// Обработка сообщений
ws1.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'heartbeat') {
        ws1.send(JSON.stringify({type: 'pong'}));
    } else {
        console.log(`${data.symbol} Price: ${data.close}`);
    }
};
```

## Demo Clients

### Тестирование функциональности
```bash
# Market Data Demo
cd demo
python orderbook_demo.py    # OrderBook WebSocket demo
python websocket_demo.py    # Candles WebSocket demo  
python api_test.py          # Comprehensive API testing

# Order System Demo
cd order_system
./test_api.sh              # Order API testing script
```

## Troubleshooting

### Частые проблемы

**1. "Database connection failed"**
```bash
docker-compose ps timescaledb           # Проверить статус
docker-compose logs timescaledb         # Логи БД
docker-compose restart timescaledb      # Перезапуск
```

**2. "No orderbook data available"**
```bash
docker-compose logs data-collector | grep orderbook  # Проверить сбор
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT COUNT(*) FROM orderbook_data;"
```

**3. "WebSocket connection failed"**
```bash
docker-compose logs api-server | grep WebSocket     # Проверить WebSocket manager
curl http://localhost:8022/health                   # API health check
```

**4. "Events not processing"** 
```bash
docker-compose logs order-events                    # Event processor логи
curl http://localhost:8080/statistics               # Проверить Order API
```

### Диагностические команды
```bash
# Полная система
./full_diagnostics.sh

# Конкретные проблемы
./db_connections_check.sh    # База данных
./api_check.sh              # API endpoints  
./monitor_growth.sh         # Рост данных

# Recovery
./emergency_fix.sh          # Экстренное восстановление
```

## Development

### Локальная разработка
```bash
# Установка зависимостей
pip install -r data-collector/requirements.txt
pip install -r api-server/requirements.txt  
pip install -r order_system/requirements.txt

# Запуск отдельных сервисов
cd data-collector && python main.py
cd api-server && python main.py
cd order_system && python main.py
```

### Testing
```bash
# API тестирование
python demo/api_test.py

# Order System тестирование  
cd order_system && ./test_api.sh

# Load testing
ab -n 1000 -c 10 http://localhost:8022/health
```

## Production Deployment

### Docker Production
```yaml
# docker-compose.prod.yml
services:
  timescaledb:
    restart: unless-stopped
    volumes:
      - timescale_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${STRONG_PASSWORD}

  api-server:
    restart: unless-stopped
    deploy:
      replicas: 2
    environment:
      LOG_LEVEL: WARNING
```

### Scaling
```bash
# Горизонтальное масштабирование API
docker-compose up -d --scale api-server=3

# Load balancer (nginx)
upstream backend {
    server api-server:8000;
    server api-server:8000;
    server api-server:8000;
}
```

## Security

### Best Practices
- Переменные окружения для всех секретных данных
- Firewall правила для ограничения доступа к портам БД
- CORS настройки для продакшн
- Rate limiting для API endpoints
- SSL/TLS для внешних соединений

### Monitoring
- Health check endpoints для всех сервисов
- Logging всех критических операций  
- Metrics collection через TimescaleDB
- Alert система для критических ошибок

## Лицензирование

Linkora DEX Backend использует dual licensing модель:

- **Open Source**: GNU Affero General Public License v3.0 (AGPL v3)
- **Commercial**: Проприетарная лицензия для коммерческого использования

Подробности см. в [LICENSING.md](./LICENSING.md)

### Быстрый выбор лицензии

**Используйте AGPL v3 если:**
- Ваш проект тоже open source
- Готовы делиться всеми изменениями
- Соответствуете copyleft требованиям

**Нужна Commercial License если:**
- Разрабатываете проприетарное ПО
- Предоставляете закрытые SaaS сервисы
- Требуется enterprise поддержка

**Контакт**: licensing@linkora.info

---

## Useful Links

- **Data Collector**: [data-collector/readme.md](data-collector/readme.md) - Детальная документация сбора данных
- **API Server**: [api-server/readme.md](api-server/readme.md) - REST API и WebSocket документация  
- **Order System**: [order_system/readme.md](order_system/readme.md) - DEX ордера и blockchain интеграция
- **Demo Clients**: [demo/](demo/) - Примеры клиентов и тестирование
- **Monitoring**: [monitoring/](monitoring/) - Диагностические утилиты