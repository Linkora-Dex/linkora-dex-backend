#!/bin/bash

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


echo "Проверка базы данных crypto_data для order_system..."

DB_EXISTS=$(docker exec crypto_timescaledb psql -U crypto_user -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='crypto_data'")

if [ "$DB_EXISTS" = "1" ]; then
    echo "База данных crypto_data уже существует"
else
    if docker exec crypto_timescaledb psql -U crypto_user -d postgres -c "CREATE DATABASE crypto_data;"; then
        echo "База данных crypto_data создана успешно"
    else
        echo "Ошибка создания базы данных crypto_data"
        exit 1
    fi
fi

echo "Настройка расширения TimescaleDB..."

if docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"; then
    echo "Расширение TimescaleDB установлено успешно"
else
    echo "Ошибка установки расширения TimescaleDB"
    exit 1
fi

echo "Создание функций для compression policies..."

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE OR REPLACE FUNCTION integer_now_func() RETURNS BIGINT
LANGUAGE SQL STABLE AS \$\$
SELECT EXTRACT(epoch FROM NOW())::BIGINT * 1000;
\$\$;

CREATE OR REPLACE FUNCTION timestamp_now_func() RETURNS TIMESTAMP
LANGUAGE SQL STABLE AS \$\$
SELECT NOW()::TIMESTAMP;
\$\$;"

if [ $? -eq 0 ]; then
    echo "✅ Функции для compression policies созданы"
else
    echo "❌ Ошибка создания функций"
    exit 1
fi

echo "Создание таблиц order_system..."

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE TABLE IF NOT EXISTS orders
(
    id BIGINT PRIMARY KEY,
    user_address VARCHAR(42) NOT NULL,
    token_in VARCHAR(42) NOT NULL,
    token_out VARCHAR(42) NOT NULL,
    amount_in DECIMAL(36,18) NOT NULL,
    target_price DECIMAL(36,18) NOT NULL,
    min_amount_out DECIMAL(36,18) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    is_long BOOLEAN,
    status VARCHAR(20) NOT NULL,
    self_executable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL,
    tx_hash VARCHAR(66),
    block_number BIGINT,
    executor_address VARCHAR(42) NULL,
    amount_out DECIMAL(36,18) NULL,
    execution_tx_hash VARCHAR(66) NULL
);"

if [ $? -eq 0 ]; then
    echo "✅ Таблица orders создана"
else
    echo "❌ Ошибка создания таблицы orders"
    exit 1
fi

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE INDEX IF NOT EXISTS idx_user_status ON orders (user_address, status);
CREATE INDEX IF NOT EXISTS idx_status_type ON orders (status, order_type);
CREATE INDEX IF NOT EXISTS idx_created_at ON orders (created_at);"

echo "✅ Индексы для orders созданы"

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE TABLE IF NOT EXISTS order_events
(
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    tx_hash VARCHAR(66),
    block_number BIGINT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_data JSONB
);"

if [ $? -eq 0 ]; then
    echo "✅ Таблица order_events создана"
else
    echo "❌ Ошибка создания таблицы order_events"
    exit 1
fi

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE INDEX IF NOT EXISTS idx_order_events ON order_events (order_id, timestamp);"

echo "✅ Индексы для order_events созданы"

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE TABLE IF NOT EXISTS system_state
(
    id SERIAL PRIMARY KEY,
    component_name VARCHAR(50) UNIQUE NOT NULL,
    last_processed_block BIGINT NOT NULL,
    last_processed_tx_hash VARCHAR(66),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE'
);"

if [ $? -eq 0 ]; then
    echo "✅ Таблица system_state создана"
else
    echo "❌ Ошибка создания таблицы system_state"
    exit 1
fi

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE INDEX IF NOT EXISTS idx_component ON system_state (component_name);"

echo "✅ Индексы для system_state созданы"

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE TABLE IF NOT EXISTS processed_events
(
    id BIGSERIAL PRIMARY KEY,
    tx_hash VARCHAR(66) NOT NULL,
    log_index INTEGER NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tx_hash, log_index)
);"

if [ $? -eq 0 ]; then
    echo "✅ Таблица processed_events создана"
else
    echo "❌ Ошибка создания таблицы processed_events"
    exit 1
fi

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_events (processed_at);"

echo "✅ Индексы для processed_events созданы"

HYPERTABLE_EXISTS=$(docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -tAc "SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name='order_events'")

if [ "$HYPERTABLE_EXISTS" != "1" ]; then
    docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
    SELECT create_hypertable('order_events', 'timestamp', if_not_exists => TRUE);"

    if [ $? -eq 0 ]; then
        echo "✅ TimescaleDB hypertable для order_events создана"
    else
        echo "❌ Ошибка создания hypertable для order_events"
    fi
else
    echo "✅ TimescaleDB hypertable для order_events уже существует"
fi

HYPERTABLE_EXISTS=$(docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -tAc "SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name='processed_events'")

if [ "$HYPERTABLE_EXISTS" != "1" ]; then
    docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
    SELECT create_hypertable('processed_events', 'processed_at', if_not_exists => TRUE);"

    if [ $? -eq 0 ]; then
        echo "✅ TimescaleDB hypertable для processed_events создана"
    else
        echo "❌ Ошибка создания hypertable для processed_events"
    fi
else
    echo "✅ TimescaleDB hypertable для processed_events уже существует"
fi

echo "Настройка compression для hypertables..."

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
ALTER TABLE order_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'order_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE processed_events SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'processed_at DESC'
);"

if [ $? -eq 0 ]; then
    echo "✅ Compression настройки применены"
else
    echo "❌ Ошибка настройки compression"
fi

echo "Добавление compression policies..."

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT add_compression_policy('order_events', INTERVAL '7 days');
SELECT add_compression_policy('processed_events', INTERVAL '7 days');"

if [ $? -eq 0 ]; then
    echo "✅ Compression policies добавлены"
else
    echo "❌ Ошибка добавления compression policies"
fi

echo ""
echo "🔍 Проверка созданных таблиц:"
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;"

echo ""
echo "✅ База данных crypto_data успешно настроена для order_system"
echo "📊 Все таблицы order_system созданы с необходимыми индексами"
echo "⚡ TimescaleDB оптимизация применена для временных данных"
echo "🗜️ Compression policies настроены для эффективного хранения"