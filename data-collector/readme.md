# Data Collector Service

Асинхронный сервис сбора, обработки и хранения данных криптовалютных рынков с Binance API в режиме реального времени.

## Архитектура

### Основные компоненты
- **BinanceCollector** - сбор klines/candles данных
- **OrderBookCollector** - сбор orderbook данных 
- **DatabaseManager** - асинхронная работа с TimescaleDB
- **RedisManager** - pub/sub для real-time уведомлений

### Технологический стек
- Python 3.11+ с asyncio
- aiohttp для HTTP запросов
- asyncpg для PostgreSQL/TimescaleDB
- redis.asyncio для pub/sub
- Decimal для точных финансовых вычислений

## Функциональность

### Сбор Candles данных
- **Исторический режим**: Сбор данных с START_DATE до текущего момента
- **Real-time режим**: Обновления каждые 0.5 секунды
- **Автоматическое восстановление**: Продолжение с последнего обработанного timestamp
- **Batch processing**: Обработка до 1000 записей за запрос

### Сбор OrderBook данных
- **Параллельный сбор**: Независимо от candles данных
- **Configurable levels**: 5, 10, 20 уровней orderbook
- **Real-time updates**: Обновления каждую секунду
- **JSON storage**: Сохранение bids/asks в JSONB формате

### Обработка данных
- **Нормализация научной нотации**: 5E-8 → 0.00000005
- **Decimal precision**: Точные финансовые вычисления
- **Конфликт-безопасность**: ON CONFLICT DO NOTHING/UPDATE
- **Error handling**: Логирование и retry механизмы

## Конфигурация

### Переменные окружения
```python
# Database
DB_HOST=timescaledb
DB_PORT=5432
DB_NAME=crypto_data
DB_USER=crypto_user
DB_PASSWORD=crypto_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Binance API
BINANCE_BASE_URL=https://api.binance.com
SYMBOLS=['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT']
START_DATE=2025-01-01
INTERVAL=1m
BATCH_SIZE=1000

# Candles Collection
RETRY_DELAY=1
MAX_RETRIES=5
REALTIME_INTERVAL=0.5

# OrderBook Collection
ORDERBOOK_LEVELS=20
ORDERBOOK_UPDATE_INTERVAL=1
ORDERBOOK_RETRY_DELAY=1
ORDERBOOK_MAX_RETRIES=3
```

## Алгоритм работы

### 1. Инициализация
```python
# Создание подключений
db_manager = DatabaseManager()
redis_manager = RedisManager()
collector = BinanceCollector(db_manager, redis_manager)

# Параллельный запуск задач
candle_tasks = [collect_symbol_data(symbol, db_manager, redis_manager, collector) 
                for symbol in SYMBOLS]
orderbook_task = run_orderbook_collector(db_manager, redis_manager)
```

### 2. Сбор исторических данных
```python
async def collect_historical_data(self, symbol: str):
    last_timestamp = await self.db.get_last_timestamp(symbol)
    start_time = last_timestamp + 60000 if last_timestamp else START_DATE
    
    while start_time < current_time:
        end_time = min(start_time + (BATCH_SIZE * 60000), current_time)
        candles = await self.fetch_klines(symbol, start_time, end_time)
        
        if candles:
            await self.db.insert_candles(candles)
            await self.db.update_state(symbol, last_timestamp)
            start_time = last_timestamp + 60000
```

### 3. Real-time режим
```python
async def collect_realtime_data(self, symbol: str):
    while True:
        current_time = int(datetime.now().timestamp() * 1000)
        start_time = current_time - 300000  # Последние 5 минут
        
        candles = await self.fetch_klines(symbol, start_time, current_time)
        if candles:
            await self.db.insert_candles(candles)
            await self.db.update_state(symbol, last_timestamp, True)
            
            # Публикация в Redis
            for candle in candles:
                await self.redis.publish_candle_update(symbol, candle)
                
        await asyncio.sleep(REALTIME_INTERVAL)
```

## Data Flow

### Candles Pipeline
```
Binance API → BinanceCollector → normalize_decimal_value() → TimescaleDB → Redis pub/sub
```

### OrderBook Pipeline
```
Binance API → OrderBookCollector → process_orderbook_data() → TimescaleDB → Redis pub/sub
```

### Redis Channels
- `candles:SYMBOL` - обновления для конкретного символа
- `candles:all` - все обновления candles
- `orderbook:SYMBOL` - обновления orderbook для символа
- `orderbook:all` - все обновления orderbook

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

### Collector State Table
```sql
CREATE TABLE collector_state (
    symbol TEXT PRIMARY KEY,
    last_timestamp BIGINT NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    is_realtime BOOLEAN DEFAULT FALSE
);
```

## Error Handling

### Rate Limiting
```python
async def fetch_klines(self, symbol: str, start_time: int, end_time: int):
    for attempt in range(MAX_RETRIES):
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    wait_time = 2 ** attempt  # Экспоненциальный backoff
                    logger.warning(f"Rate limit hit for {symbol}, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
```

### Connection Failures
```python
async def connect(self):
    try:
        self.pool = await asyncpg.create_pool(
            server_settings={
                'idle_in_transaction_session_timeout': '300000',
                'statement_timeout': '30000',
            }
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
```

### Data Normalization
```python
def normalize_decimal_value(value_str: str) -> Decimal:
    try:
        if isinstance(value_str, str) and ('E' in value_str.upper() or 'e' in value_str):
            return Decimal(str(float(value_str)))  # Конвертация научной нотации
        return Decimal(str(value_str))
    except (ValueError, InvalidOperation, TypeError):
        logger.warning(f"Invalid decimal value: {value_str}, using 0")
        return Decimal('0')
```

## Мониторинг и диагностика

### Логирование
- **INFO**: Основные операции и статистика
- **DEBUG**: Детальная информация для отладки
- **WARNING**: Rate limits и retry операции
- **ERROR**: Ошибки запросов и парсинга данных

### Ключевые метрики
- Количество собранных candles за период
- Статус real-time режима для каждого символа
- Частота rate limit событий
- Ошибки подключения к API/БД

### Состояние сбора данных
```sql
-- Проверка состояния коллектора
SELECT symbol, last_timestamp, is_realtime, last_updated 
FROM collector_state;

-- Статистика собранных данных
SELECT symbol, COUNT(*) as candles_count, 
       MIN(timestamp) as first_candle, 
       MAX(timestamp) as last_candle
FROM candles 
GROUP BY symbol;
```

## Производительность

### Асинхронная архитектура
- Параллельный сбор данных для всех символов
- Независимые задачи для candles и orderbook
- Connection pooling для базы данных
- Session pooling для HTTP запросов

### Оптимизации
- Batch INSERT операции (до 1000 записей)
- Конфликт-безопасные операции (ON CONFLICT)
- Decimal нормализация для точности вычислений
- Экспоненциальный backoff для retry логики

### Scalability
- Горизонтальное масштабирование через дополнительные символы
- Вертикальное масштабирование через увеличение BATCH_SIZE
- TimescaleDB партиционирование по времени
- Redis pub/sub для real-time распределения

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Docker Compose
```yaml
data-collector:
  build: ./data-collector
  environment:
    - DB_HOST=timescaledb
    - REDIS_HOST=redis
  depends_on:
    - timescaledb
    - redis
  restart: unless-stopped
```

### Проверка работоспособности
```bash
# Логи сервиса
docker-compose logs -f data-collector

# Проверка состояния сбора
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT symbol, is_realtime, 
       EXTRACT(epoch FROM (NOW() - last_updated)) as seconds_ago
FROM collector_state;"

# Статистика данных
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT symbol, COUNT(*) FROM candles GROUP BY symbol;"
```

## Troubleshooting

### Частые проблемы

**1. "Database connection failed"**
- Проверить доступность TimescaleDB контейнера
- Убедиться в корректности DB_* переменных
- Проверить сетевое подключение

**2. "Rate limit hit"**
- Увеличить RETRY_DELAY и REALTIME_INTERVAL
- Проверить лимиты Binance API
- Рассмотреть использование API ключей

**3. "Scientific notation detected"**
- Нормальное поведение для малых значений volume
- normalize_decimal_value() автоматически обрабатывает
- Проверить корректность сохранения в БД

**4. "No data received"**
- Проверить доступность Binance API
- Убедиться в корректности SYMBOLS списка
- Проверить START_DATE и временные диапазоны

### Диагностические команды
```bash
# Проверка подключения к Binance API
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1"

# Проверка Redis pub/sub
docker exec crypto_redis redis-cli monitor

# Проверка последних записей
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT * FROM candles WHERE symbol = 'BTCUSDT' ORDER BY timestamp DESC LIMIT 5;"
```