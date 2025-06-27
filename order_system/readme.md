# Linkora DEX Order System

Высокопроизводительная микросервисная система сбора, хранения и мониторинга ордеров DEX с автоматическим восстановлением состояния и real-time синхронизацией с блокчейном.

## Ключевые особенности

- **Микросервисная архитектура** с Docker контейнерами
- **100% надежность восстановления** после сбоев без потери данных
- **Параллельная обработка блоков** с ускорением в 5-10 раз
- **TimescaleDB** для оптимального хранения временных данных
- **Транзакционная безопасность** всех операций
- **Real-time мониторинг** статусов ордеров
- **REST API** с пагинацией и корректным форматированием данных
- **Graceful shutdown** с корректным завершением всех операций

## Архитектура

```
order_system/
├── config.py                 # Конфигурация системы
├── database.py              # TimescaleDB управление с асинхронными операциями
├── event_processor.py       # Обработка blockchain событий
├── event_main.py            # Точка входа для event processor
├── status_monitor.py        # Мониторинг здоровья компонентов
├── api.py                   # Оригинальный API (legacy)
├── app.py                   # Основной REST API сервис
├── main.py                  # Точка входа для всей системы
├── database_diagnostics.py  # Диагностические утилиты
├── artifacts/               # ABI контрактов и конфиги
├── requirements.txt         # Python зависимости
├── Dockerfile.api          # Контейнер для API сервиса
└── Dockerfile.event        # Контейнер для Event Processor
```

## Технологический стек

- **Python 3.11+** с asyncio
- **TimescaleDB** (PostgreSQL) для персистентного хранения временных данных
- **Web3.py** для взаимодействия с блокчейном (Hardhat/Ethereum)
- **Starlette** для REST API
- **asyncpg** для асинхронной работы с БД
- **Docker & Docker Compose** для контейнеризации

## Быстрый старт

### 1. Клонирование и запуск

```bash
git clone <repository>
cd Linkora-Dex-Backend

# Запуск всей системы
docker-compose up -d

# Проверка статуса
docker-compose ps
```

### 2. Структура сервисов

```yaml
services:
  timescaledb:     # TimescaleDB база данных
  order-api:       # REST API сервис
  order-events:    # Event Processor сервис
```

### 3. Проверка работы

```bash
# Проверка API
curl http://localhost:8080/health

# Проверка executed ордеров
curl http://localhost:8080/orders/executed

# Проверка статистики
curl http://localhost:8080/statistics
```

## Компоненты системы

### Order API Service (app.py)

**Основной REST API сервис с полной поддержкой пагинации:**

**Endpoints:**
```http
# Ордера по статусам
GET /orders/pending?limit=100&offset=0         # PENDING ордера с пагинацией
GET /orders/executed?limit=100&offset=0        # EXECUTED ордера с пагинацией
GET /orders/cancelled?limit=100&offset=0       # CANCELLED ордера с пагинацией
GET /orders/all?status=executed&limit=100&offset=0  # Все ордера с фильтрацией по статусу

# Пользовательские ордера
GET /users/{user_address}/orders?status=executed&limit=100&offset=0  # Ордера пользователя

# Детали ордеров
GET /orders/{order_id}                         # Детали конкретного ордера
GET /orders/{order_id}/events                  # События ордера

# Системная информация
GET /health                                    # Статус системы
GET /statistics                               # Статистика ордеров
```

**Параметры пагинации:**
- `limit` - количество записей (по умолчанию 100, максимум 1000)
- `offset` - смещение (по умолчанию 0)
- `status` - фильтр по статусу (pending, executed, cancelled)

**Особенности:**
- Корректное форматирование Decimal без научной нотации
- Нормализация типов ордеров (`STOP_LOSS` → `STOP`)
- Полная обработка событий ордеров с деталями
- Транзакционная безопасность запросов
- Универсальная пагинация для всех списковых эндпоинтов
- Валидация входных параметров с соответствующими HTTP кодами

### Event Processor Service (event_processor.py)

**Функции:**
- Сканирование blockchain событий (OrderCreated, OrderExecuted, OrderCancelled)
- Параллельная обработка блоков при восстановлении
- Автоматическое восстановление после сбоев
- Предотвращение дубликатов событий

**Алгоритм восстановления:**
1. Получение `last_processed_block` из БД
2. Вычисление пропущенных блоков
3. Батчевая обработка с параллелизмом
4. Транзакционное сохранение событий
5. Контроль дубликатов через `processed_events`

### DatabaseManager (database.py)

**Особенности:**
- Асинхронные операции с TimescaleDB
- Контекстные менеджеры для транзакций
- Автоматическое создание схемы БД
- Оптимизированные индексы для временных данных
- Поддержка пагинации на уровне БД

**Схема БД:**
```sql
orders              # Основные данные ордеров с CHECK ограничениями
order_events        # История изменений ордеров  
system_state        # Состояние компонентов системы
processed_events    # Предотвращение дубликатов
```

**Ограничения данных:**
```sql
-- Типы ордеров
CHECK (order_type IN ('LIMIT', 'STOP'))

-- Статусы ордеров  
CHECK (status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED'))
```

### Status Monitor

**Мониторинг:**
- Проверка здоровья всех компонентов
- Отслеживание отставания от blockchain
- Health-check endpoint для внешних систем
- Диагностика состояния соединений

## Конфигурация

### Docker Compose настройки

```yaml
# docker-compose.yml
version: '3.8'
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: crypto_data
      POSTGRES_USER: crypto_user
      POSTGRES_PASSWORD: crypto_password
    ports:
      - "5432:5432"

  order-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8080:8080"
    depends_on:
      - timescaledb

  order-events:
    build:
      context: .
      dockerfile: Dockerfile.event
    depends_on:
      - timescaledb
```

### Переменные окружения

```python
# config.py
DB_CONFIG = {
    'host': 'timescaledb',
    'port': 5432,
    'database': 'crypto_data',
    'user': 'crypto_user',
    'password': 'crypto_password'
}

WEB3_PROVIDER = "http://127.0.0.1:8545"  # Hardhat local
TRADING_ADDRESS = "0x..."
ROUTER_ADDRESS = "0x..."
ORACLE_ADDRESS = "0x..."
```

## API Reference

### Примеры реальных ответов

**GET /orders/executed?limit=2&offset=0**
```json
{
  "orders": [
    {
      "id": 7,
      "user_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      "token_in": "0x0000000000000000000000000000000000000000",
      "token_out": "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0",
      "amount_in": "0.02",
      "target_price": "0.86035638",
      "min_amount_out": "0.000000000001464384",
      "order_type": "LIMIT",
      "is_long": true,
      "status": "EXECUTED",
      "created_at": "2025-06-07T09:38:45+00:00",
      "executed_at": "2025-06-07T09:35:52.247983+00:00"
    },
    {
      "id": 5,
      "user_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
      "token_in": "0x0000000000000000000000000000000000000000",
      "token_out": "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0",
      "amount_in": "0.05",
      "target_price": "0.8944299",
      "min_amount_out": "0.000000000003663159",
      "order_type": "LIMIT",
      "is_long": true,
      "status": "EXECUTED",
      "created_at": "2025-06-07T09:38:39+00:00",
      "executed_at": "2025-06-07T09:35:52.244466+00:00"
    }
  ],
  "total": 4,
  "limit": 2,
  "offset": 0,
  "has_more": true,
  "status": "success"
}
```

**GET /users/0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC/orders?status=cancelled&limit=1&offset=0**
```json
{
  "orders": [
    {
      "id": 6,
      "user_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
      "token_in": "0x0000000000000000000000000000000000000000",
      "token_out": "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0",
      "amount_in": "0.05",
      "target_price": "2685.48522214",
      "min_amount_out": "0.000000000001",
      "order_type": "STOP",
      "is_long": false,
      "status": "CANCELLED",
      "created_at": "2025-06-07T09:38:40+00:00",
      "executed_at": null
    }
  ],
  "total": 2,
  "limit": 1,
  "offset": 0,
  "has_more": true,
  "status": "success"
}
```

**GET /orders/5**
```json
{
  "order": {
    "id": 5,
    "user_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    "token_in": "0x0000000000000000000000000000000000000000",
    "token_out": "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0",
    "amount_in": "0.05",
    "target_price": "0.8944299",
    "min_amount_out": "0.000000000003663159",
    "order_type": "LIMIT",
    "is_long": true,
    "status": "EXECUTED",
    "self_executable": false,
    "created_at": "2025-06-07T09:38:39+00:00",
    "updated_at": "2025-06-07T09:38:39+00:00",
    "executed_at": "2025-06-07T09:35:52.244466+00:00",
    "tx_hash": "0x...",
    "block_number": 1234,
    "executor_address": "0x...",
    "amount_out": "0.000000000003663159",
    "execution_tx_hash": "0x..."
  },
  "status": "success"
}
```

**GET /orders/5/events**
```json
{
  "order_id": 5,
  "events": [
    {
      "event_type": "CREATED",
      "old_status": null,
      "new_status": "PENDING",
      "tx_hash": "0x...",
      "block_number": 1230,
      "timestamp": "2025-06-07T09:38:39+00:00",
      "event_data": {}
    },
    {
      "event_type": "EXECUTED",
      "old_status": "PENDING",
      "new_status": "EXECUTED",
      "tx_hash": "0x...",
      "block_number": 1234,
      "timestamp": "2025-06-07T09:35:52.244466+00:00",
      "event_data": {}
    }
  ],
  "total": 2,
  "status": "success"
}
```

**GET /statistics**
```json
{
  "statistics": {
    "PENDING": {"total": 0, "last_24h": 0},
    "EXECUTED": {"total": 4, "last_24h": 4},
    "CANCELLED": {"total": 3, "last_24h": 3}
  },
  "status": "success"
}
```

**Обработка ошибок:**

```json
# GET /orders/99999 (несуществующий ордер)
{
  "error": "Order 99999 not found"
}

# GET /orders/all?status=invalid_status (невалидный статус)
{
  "error": "Invalid status. Use: pending, executed, cancelled"
}

# GET /orders/abc123 (невалидный ID)
{
  "error": "Invalid order_id format. Must be a number."
}
```

## Производительность

### Оптимизации данных

**Форматирование чисел:**
- Устранена научная нотация (`5e-11` → `0.00000000005`)
- Функция `format_decimal_to_string()` для корректного отображения
- Оптимизированное преобразование Decimal в строки

**Нормализация данных:**
- Автоматическое преобразование `STOP_LOSS` → `STOP`
- Унифицированные статусы ордеров
- Консистентные поля во всех endpoints

**Пагинация:**
- Эффективные LIMIT/OFFSET запросы
- Отдельные COUNT запросы для точного подсчета
- Валидация параметров пагинации (limit ≤ 1000, offset ≥ 0)
- Индексы для оптимизации сортировки

**Валидация и безопасность:**
- HTTP 400 для невалидных параметров
- HTTP 404 для несуществующих ресурсов
- HTTP 500 только для внутренних ошибок сервера
- Строгая типизация order_id

### TimescaleDB преимущества

**Для временных данных:**
- Автоматическое партиционирование по времени
- Сжатие старых данных
- Оптимизированные запросы по временным диапазонам
- Высокая производительность для аналитики

## Мониторинг и диагностика

### Health Check

```bash
curl http://localhost:8080/health
```

**Ответ:**
```json
{
  "overall_status": "healthy",
  "components": {
    "order_api": "HEALTHY",
    "database": "HEALTHY",
    "timestamp": "2025-06-07T12:19:08.544914",
    "database_connection": "WORKING"
  },
  "status": "success"
}
```

### Тестирование API

```bash
# Полное тестирование всех эндпоинтов
./test_api.sh

# Быстрая проверка основных функций
curl -s http://localhost:8080/statistics | jq '.statistics'
curl -s http://localhost:8080/orders/executed | jq '.total'
curl -s "http://localhost:8080/orders/all?limit=1&offset=0" | jq '.has_more'
```

### Логи контейнеров

```bash
# Логи API сервиса
docker-compose logs -f order-api

# Логи Event Processor
docker-compose logs -f order-events

# Логи базы данных
docker-compose logs -f timescaledb
```

### Диагностические утилиты

```bash
# Проверка данных в БД
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT COUNT(*) as total, status FROM orders GROUP BY status;"

# Статистика обработки событий
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT event_type, COUNT(*) 
FROM order_events 
GROUP BY event_type;"
```

## Устойчивость к сбоям

### Автоматическое восстановление

**Event Processor при перезапуске:**
1. Читает `last_processed_block` из system_state
2. Вычисляет пропущенные блоки
3. Обрабатывает пропущенные события
4. Продолжает нормальную работу

**API Service при перезапуске:**
1. Инициализация пула соединений к БД
2. Тестирование подключения
3. Готовность к обработке запросов

### Graceful Shutdown

```bash
# Корректная остановка
docker-compose down

# Перезапуск только API для обновления кода
docker-compose restart order-api
```

## Развертывание

### Production окружение

**Docker настройки:**
```yaml
# docker-compose.prod.yml
services:
  timescaledb:
    restart: unless-stopped
    volumes:
      - timescale_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${STRONG_PASSWORD}

  order-api:
    restart: unless-stopped
    environment:
      - DB_PASSWORD=${STRONG_PASSWORD}
      - WEB3_PROVIDER=${MAINNET_RPC}

volumes:
  timescale_data:
```

**Scaling:**
```bash
# Масштабирование API
docker-compose up -d --scale order-api=3

# Load balancer (nginx)
upstream api_backend {
    server order-api:8080;
    server order-api:8080;
    server order-api:8080;
}
```

## Безопасность

### Конфигурация

**Переменные окружения:**
```bash
# Никогда не коммитить в репозиторий
export DB_PASSWORD=strong_random_password
export WEB3_PROVIDER=https://secure-rpc-endpoint
export API_SECRET_KEY=random_secret_key
```

**Firewall правила:**
```bash
# Только необходимые порты
ufw allow 8080/tcp  # API
ufw allow 5432/tcp  # PostgreSQL (только для внутренней сети)
```

## Troubleshooting

### Частые проблемы

**1. "Database connection failed"**
```bash
# Проверить статус контейнера
docker-compose ps timescaledb

# Логи базы данных
docker-compose logs timescaledb

# Тест подключения
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data
```

**2. "Events not processing"**
```bash
# Проверить Hardhat node
curl -X POST -H "Content-Type: application/json" \
     --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
     http://127.0.0.1:8545

# Логи event processor
docker-compose logs order-events
```

**3. "API returning empty results"**
```bash
# Проверка данных в БД
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT COUNT(*) FROM orders;"

# Перезапуск API
docker-compose restart order-api

# Проверка логов API
docker logs crypto_order-api --tail 20
```

**4. "Маршрутизация не работает"**
```bash
# Проверка конкретных эндпоинтов
curl -v http://localhost:8080/orders/5
curl -v http://localhost:8080/users/0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC/orders

# Полное тестирование
./test_api.sh
```

### Диагностика производительности

**SQL запросы для анализа:**
```sql
-- Статистика ордеров
SELECT status, COUNT(*), 
       AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/3600) as avg_age_hours
FROM orders 
GROUP BY status;

-- Активность событий
SELECT DATE(timestamp), event_type, COUNT(*)
FROM order_events 
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY 1, 2 
ORDER BY 1 DESC, 3 DESC;

-- Производительность БД
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Эффективность индексов для пагинации
EXPLAIN ANALYZE SELECT * FROM orders WHERE status = 'EXECUTED' ORDER BY created_at DESC LIMIT 100 OFFSET 0;
```

**Проверка API производительности:**
```bash
# Измерение времени ответа
time curl -s 'http://localhost:8080/orders/all?limit=1000&offset=0' > /dev/null

# Нагрузочное тестирование
ab -n 100 -c 10 http://localhost:8080/orders/executed
```

## Контакты и поддержка

- **Репозиторий:** [GitHub Link]
- **Документация API:** Автоматически генерируется на основе тестов
- **Мониторинг:** `http://localhost:8080/health`
- **Тестирование:** `./test_api.sh`

## Лицензия

MIT License - см. LICENSE файл для деталей.