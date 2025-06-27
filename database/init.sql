CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ФУНКЦИИ ДЛЯ COMPRESSION POLICIES
CREATE OR REPLACE FUNCTION integer_now_func() RETURNS BIGINT
LANGUAGE SQL STABLE AS $$
SELECT EXTRACT(epoch FROM NOW())::BIGINT * 1000;
$$;

CREATE OR REPLACE FUNCTION timestamp_now_func() RETURNS TIMESTAMP
LANGUAGE SQL STABLE AS $$
SELECT NOW()::TIMESTAMP;
$$;

-- СУЩЕСТВУЮЩИЕ ТАБЛИЦЫ CRYPTO DATA COLLECTOR
CREATE TABLE IF NOT EXISTS candles (
    id BIGSERIAL,
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable('candles', 'timestamp', chunk_time_interval => 86400000);
SELECT set_integer_now_func('candles', 'integer_now_func');

CREATE INDEX IF NOT EXISTS idx_candles_symbol_open_time ON candles (symbol, open_time DESC);
CREATE INDEX IF NOT EXISTS idx_candles_open_time ON candles (open_time DESC);

CREATE TABLE IF NOT EXISTS collector_state (
    symbol TEXT PRIMARY KEY,
    last_timestamp BIGINT NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    is_realtime BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS orderbook_data (
    symbol TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    last_update_id BIGINT NOT NULL,
    bids JSONB NOT NULL,
    asks JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable('orderbook_data', 'timestamp', chunk_time_interval => 86400000);
SELECT set_integer_now_func('orderbook_data', 'integer_now_func');

CREATE INDEX IF NOT EXISTS idx_orderbook_symbol_timestamp ON orderbook_data (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orderbook_update_id ON orderbook_data (symbol, last_update_id DESC);

-- НОВЫЕ ТАБЛИЦЫ ORDER SYSTEM
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT PRIMARY KEY,
    user_address TEXT NOT NULL,
    token_in TEXT NOT NULL,
    token_out TEXT NOT NULL,
    amount_in DECIMAL(36,18) NOT NULL,
    target_price DECIMAL(36,18) NOT NULL,
    min_amount_out DECIMAL(36,18) NOT NULL,
    order_type TEXT NOT NULL,
    is_long BOOLEAN,
    status TEXT NOT NULL,
    self_executable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMPTZ NULL,
    tx_hash TEXT,
    block_number BIGINT,
    executor_address TEXT NULL,
    amount_out DECIMAL(36,18) NULL,
    execution_tx_hash TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_status ON orders (user_address, status);
CREATE INDEX IF NOT EXISTS idx_status_type ON orders (status, order_type);
CREATE INDEX IF NOT EXISTS idx_created_at ON orders (created_at);

CREATE TABLE IF NOT EXISTS order_events (
    id BIGSERIAL,
    order_id BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    tx_hash TEXT,
    block_number BIGINT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    event_data JSONB,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('order_events', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_order_events ON order_events (order_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_order_events_type ON order_events (event_type, timestamp DESC);

CREATE TABLE IF NOT EXISTS system_state (
    id SERIAL PRIMARY KEY,
    component_name TEXT UNIQUE NOT NULL,
    last_processed_block BIGINT NOT NULL,
    last_processed_tx_hash TEXT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'ACTIVE'
);

CREATE INDEX IF NOT EXISTS idx_component ON system_state (component_name);

CREATE TABLE IF NOT EXISTS processed_events (
    id BIGSERIAL,
    tx_hash TEXT NOT NULL,
    log_index INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, processed_at)
);

SELECT create_hypertable('processed_events', 'processed_at', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_events (processed_at);
CREATE INDEX IF NOT EXISTS idx_processed_tx ON processed_events (tx_hash, log_index);

-- TIMESCALEDB COMPRESSION НАСТРОЙКИ
ALTER TABLE candles SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE orderbook_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE order_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'order_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE processed_events SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'processed_at DESC'
);

-- COMPRESSION POLICIES
SELECT add_compression_policy('candles', 86400000 * 7);
SELECT add_compression_policy('orderbook_data', 86400000);
SELECT add_compression_policy('order_events', INTERVAL '7 days');
SELECT add_compression_policy('processed_events', INTERVAL '7 days');