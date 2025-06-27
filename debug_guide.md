# Диагностика Linkora DEX Backend

Минималистичный гид по диагностике проблем всей платформы.

## Быстрая диагностика

### Проверка системы
```bash
# Статус всех сервисов
docker-compose ps

# Health check всех API
curl -s http://localhost:8022/health | jq '.status'  # Market Data API
curl -s http://localhost:8080/health | jq '.overall_status'  # Order System API

# База данных
docker exec crypto_timescaledb pg_isready -U crypto_user -d crypto_data
```

### Проверка данных
```bash
# Количество записей во всех таблицах
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT 'candles' as table_name, COUNT(*) FROM candles
UNION ALL SELECT 'orderbook_data', COUNT(*) FROM orderbook_data  
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_events', COUNT(*) FROM order_events;"

# Состояние сборщиков данных
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT symbol, is_realtime, EXTRACT(epoch FROM (NOW() - last_updated)) as seconds_ago 
FROM collector_state;"
```

## Логи сервисов

### Мониторинг ошибок
```bash
# Все ошибки в реальном времени
docker-compose logs -f | grep -E "(ERROR|FATAL|exception)"

# Конкретные сервисы
docker-compose logs -f data-collector | grep ERROR
docker-compose logs -f api-server | grep ERROR  
docker-compose logs -f order-events | grep ERROR
```

### Проверка активности
```bash
# Data Collector - сбор данных
docker-compose logs data-collector --tail 20 | grep -E "(candles|orderbook|realtime)"

# API Server - WebSocket соединения
docker-compose logs api-server --tail 20 | grep -E "(WebSocket|connected|heartbeat)"

# Order System - blockchain события
docker-compose logs order-events --tail 20 | grep -E "(block|event|processed)"
```

## Типовые проблемы

### База данных

**"Database connection failed"**
```bash
docker-compose restart timescaledb
docker-compose logs timescaledb --tail 10
```

**"relation does not exist"**
```bash
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "\dt"
# Если таблиц нет:
docker-compose down && docker-compose up --build
```

**Зависшие соединения**
```bash
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT pid, state, query_start FROM pg_stat_activity 
WHERE datname = 'crypto_data' AND state LIKE '%transaction%';"

# Завершить зависшие процессы
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE state = 'idle in transaction (aborted)';"
```

### Data Collector

**"No data received"**
```bash
# Проверка Binance API
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1"

# Перезапуск collector
docker-compose restart data-collector
```

**"Scientific notation detected"**
```bash
# Нормально - автоматически обрабатывается normalize_decimal_value()
docker-compose logs data-collector | grep "Scientific notation" | tail 5
```

### API Server

**WebSocket не работает**
```bash
# Проверка Redis
docker exec crypto_redis redis-cli ping

# Проверка pub/sub
docker exec crypto_redis redis-cli monitor | head -10

# Перезапуск API
docker-compose restart api-server
```

**"No orderbook data available"**
```bash
# Проверка данных orderbook
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT symbol, COUNT(*), MAX(timestamp) FROM orderbook_data GROUP BY symbol;"

# Если пусто - перезапуск collector
docker-compose restart data-collector
```

### Order System

**"Events not processing"**
```bash
# Проверка blockchain подключения
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://127.0.0.1:8545

# Состояние event processor
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT * FROM system_state WHERE component_name = 'order_listener';"
```

**Recovery mode**
```bash
# Принудительный откат для переобработки
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
UPDATE system_state SET status = 'RECOVERY', last_processed_block = last_processed_block - 100 
WHERE component_name = 'order_listener';"

docker-compose restart order-events
```

## Экстренное восстановление

### Полный перезапуск
```bash
# Остановка всех сервисов
docker-compose down

# Завершение зависших процессов БД
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE datname = 'crypto_data' AND pid != pg_backend_pid();"

# Запуск системы
docker-compose up -d

# Проверка через 30 секунд
sleep 30 && curl http://localhost:8022/health && curl http://localhost:8080/health
```

### Очистка данных (ОПАСНО)
```bash
# Полная очистка с потерей данных
docker-compose down -v
docker-compose up --build
```

## Мониторинг производительности

### Размер данных
```bash
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(tablename)) 
FROM pg_tables WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(tablename) DESC;"
```

### Активные соединения
```bash
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT application_name, COUNT(*), state FROM pg_stat_activity 
WHERE datname = 'crypto_data' GROUP BY application_name, state;"
```

### Redis статистика
```bash
docker exec crypto_redis redis-cli info memory | grep used_memory_human
docker exec crypto_redis redis-cli info clients | grep connected_clients
```

## Профилактика

### Регулярные проверки
```bash
# Health check всех сервисов (каждые 5 минут)
*/5 * * * * curl -s http://localhost:8022/health > /dev/null && curl -s http://localhost:8080/health > /dev/null

# Проверка роста данных (каждый час)  
0 * * * * docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT COUNT(*) FROM candles;" >> /var/log/crypto_data.log
```

### Настройки производительности
```yaml
# docker-compose.yml - настройки БД
environment:
  - idle_in_transaction_session_timeout=300000
  - statement_timeout=30000
  - max_connections=100
```

## Контрольный список при проблемах

**Инфраструктура:**
- [ ] `docker-compose ps` - все сервисы запущены
- [ ] `curl http://localhost:8022/health` - Market Data API работает
- [ ] `curl http://localhost:8080/health` - Order System API работает

**База данных:**
- [ ] `pg_isready` - PostgreSQL доступен
- [ ] Проверить количество записей в таблицах
- [ ] Завершить зависшие транзакции

**Сервисы:**
- [ ] Проверить логи на ошибки
- [ ] Перезапустить проблемные сервисы
- [ ] Подождать 1-2 минуты и повторить проверку

**При критических проблемах:**
- [ ] Полный перезапуск системы
- [ ] Проверка через 30 секунд
- [ ] Если не помогает - очистка данных и пересборка