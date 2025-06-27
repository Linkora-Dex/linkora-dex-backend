Проблема с научной нотацией в данных от Binance API. Значение 0E-8 означает 0 × 10^-8 = 0, но записано в экспоненциальной форме


# Создание бэкапа
docker exec crypto_timescaledb pg_dump -U crypto_user crypto_data > backup_before_migration.sql

# Выполнение миграции
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -f data-collector/fix/sql_fix_1.sql

# Проверка результата
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT COUNT(*) FROM candles WHERE volume::text LIKE '%E%'"




# Подключение к Redis
docker exec -it crypto_redis redis-cli

# Очистка всего кэша
FLUSHALL

# Или очистка только ключей свечей
KEYS "candles:*"
DEL candles:BTCUSDT candles:ETHUSDT candles:ADAUSDT candles:SOLUSDT candles:BNBUSDT

# Выход
exit





# Подключение к базе данных
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data

# Выполнение миграции
UPDATE candles 
SET 
    taker_buy_volume = CASE 
        WHEN taker_buy_volume::text LIKE '%E%' THEN (taker_buy_volume::float)::decimal(20,8)
        ELSE taker_buy_volume 
    END,
    taker_buy_quote_volume = CASE 
        WHEN taker_buy_quote_volume::text LIKE '%E%' THEN (taker_buy_quote_volume::float)::decimal(20,8)
        ELSE taker_buy_quote_volume 
    END
WHERE taker_buy_volume::text LIKE '%E%' 
   OR taker_buy_quote_volume::text LIKE '%E%';

# Проверка результата
SELECT COUNT(*) FROM candles WHERE taker_buy_volume::text LIKE '%E%';



Команда выполнилась, но обновлено 0 записей. Проверим актуальное состояние базы:
sql-- Проверка наличия записей с научной нотацией
SELECT COUNT(*) FROM candles WHERE taker_buy_volume::text LIKE '%E%';
sql-- Проверка всех полей с научной нотацией  
SELECT COUNT(*) FROM candles WHERE 
    volume::text LIKE '%E%' OR 
    quote_volume::text LIKE '%E%' OR 
    taker_buy_volume::text LIKE '%E%' OR 
    taker_buy_quote_volume::text LIKE '%E%';
sql-- Посмотреть примеры проблемных записей
SELECT symbol, timestamp, volume, quote_volume, taker_buy_volume, taker_buy_quote_volume 
FROM candles 
WHERE taker_buy_volume::text LIKE '%E%' OR taker_buy_quote_volume::text LIKE '%E%'
LIMIT 5;
