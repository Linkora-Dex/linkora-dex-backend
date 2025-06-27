

проверить структуру базы
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "\dt"


# Перезапустите контейнеры для применения изменений
docker-compose restart crypto_order_api

# Подождите несколько секунд и проверьте логи API
docker-compose logs -f crypto_order_api

# В другом терминале протестируйте API
curl -s http://localhost:8080/orders/pending | jq
curl -s http://localhost:8080/health | jq
curl -s http://localhost:8080/statistics | jq


# Только структура таблицы
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "\d orders"

# Только типы ордеров
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT order_type, COUNT(*) FROM orders GROUP BY order_type;"

# Только статусы
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT status, COUNT(*) FROM orders GROUP BY status;"



# Перезапустить API
docker-compose restart order-api

# Проверить события для ордера 15 (должно быть 2 события)
curl http://localhost:8080/orders/15/events | jq '.'

# Проверить события для несуществующего ордера
curl http://localhost:8080/orders/999/events | jq '.'

# Проверить все endpoints
curl http://localhost:8080/orders/pending | jq '.orders | length'
curl http://localhost:8080/statistics | jq '.statistics'
curl http://localhost:8080/health | jq '.overall_status'











Проверим состояние в БД:
bashdocker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT * FROM system_state WHERE component_name = 'order_listener';
"
Если откат не сработал, выполним принудительный откат на блок 100:
bashdocker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
UPDATE system_state 
SET last_processed_block = 100, 
    status = 'RECOVERY',
    updated_at = CURRENT_TIMESTAMP 
WHERE component_name = 'order_listener';
"


