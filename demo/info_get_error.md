## ДИАГНОСТИКА ПРОБЛЕМЫ WEBSOCKET

Соединение установлено, но данные не поступают. Проверим причины пошагово.

### ВАРИАНТЫ ДИАГНОСТИКИ

#### Вариант 1: Проверка состояния data-collector
**Проблема**: data-collector не работает или не публикует в Redis
**Проверка**:
```bash
docker-compose logs data-collector
```

#### Вариант 2: Проверка Redis подключения и сообщений
**Проблема**: Redis не получает сообщения или API server не подписан
**Проверка**:
```bash
docker exec -it crypto_redis redis-cli monitor
```

#### Вариант 3: Проверка API server логов
**Проблема**: API server не обрабатывает Redis сообщения
**Проверка**:
```bash
docker-compose logs api-server
```

#### Вариант 4: Проверка данных в базе
**Проблема**: Нет актуальных данных в БД
**Проверка**:
```bash
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT symbol, MAX(timestamp) FROM candles GROUP BY symbol;"
```

#### Вариант 5: Проверка состояния collector_state
**Проблема**: Collector завис на историческом режиме
**Проверка**:
```bash
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT * FROM collector_state;"
```

### НАИБОЛЕЕ ВЕРОЯТНЫЕ ПРИЧИНЫ

1. **Data-collector не достиг realtime режима** - застрял на сборе исторических данных
2. **Redis не получает сообщения** - проблема в publish_candle_update
3. **API server не подписался на Redis** - ошибка в startup или подключении
4. **Нет новых данных от Binance** - выходные/праздники или проблемы API

### РЕКОМЕНДУЕМАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ПРОВЕРКИ

1. Проверить логи data-collector на наличие сообщений "Starting realtime collection"
2. Проверить Redis monitor на наличие publish команд
3. Проверить API server логи на ошибки Redis подключения
4. Проверить актуальность данных в БД

**Какую проверку выполнить первой?**












## ДИАГНОСТИКА: REDIS РАБОТАЕТ, НО WEBSOCKET НЕ ПОЛУЧАЕТ ДАННЫЕ

### АНАЛИЗ ПРОБЛЕМЫ

**Redis публикация работает корректно:**
- Data-collector публикует в `candles:BTCUSDT` 
- Data-collector публикует в `candles:all`
- Данные актуальные и свежие

**Проблема в API server** - не получает или не ретранслирует сообщения Redis.

### ВАРИАНТЫ ДИАГНОСТИКИ API SERVER

#### Вариант 1: Проверка логов API server
```bash
docker-compose logs api-server
```

#### Вариант 2: Проверка Redis подключения в API server
```bash
docker exec crypto_api_server python -c "
import redis.asyncio as redis
import asyncio

async def test():
    r = redis.Redis(host='redis', port=6379, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe('candles:all')
    print('Subscribed to candles:all')
    async for message in pubsub.listen():
        if message['type'] == 'message':
            print(f'Received: {message}')
            break

asyncio.run(test())
"
```

#### Вариант 3: Проверка состояния WebSocket connections
Добавить отладочную информацию в WebSocketManager

#### Вариант 4: Проверка совместимости форматов данных
Сравнить ожидаемый формат в API server с публикуемым

### НАИБОЛЕЕ ВЕРОЯТНЫЕ ПРИЧИНЫ

1. **API server не подписался на Redis** - ошибка в startup или подключении
2. **Redis подключение не работает в API server** - конфигурация или сеть
3. **Ошибка в broadcast_update** - не находит соединения или ошибка отправки
4. **WebSocketManager не инициализирован** - проблема в startup sequence

### ПЕРВООЧЕРЕДНАЯ ПРОВЕРКА

Выполни команду для проверки логов API server:
```bash
docker-compose logs api-server | grep -E "(Redis|WebSocket|connected|error)"
```

Это покажет:
- Подключился ли API server к Redis
- Запустились ли WebSocket задачи  
- Есть ли ошибки в broadcast или connections

**Результат этой команды поможет точно определить причину.**

