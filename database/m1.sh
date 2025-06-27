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

docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
CREATE TABLE IF NOT EXISTS orderbook_data (
    symbol TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    last_update_id BIGINT NOT NULL,
    bids JSONB NOT NULL,
    asks JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp)
);

SELECT create_hypertable('orderbook_data', 'timestamp', chunk_time_interval => 86400000, if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_orderbook_symbol_timestamp ON orderbook_data (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orderbook_update_id ON orderbook_data (symbol, last_update_id DESC);

ALTER TABLE orderbook_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('orderbook_data', compress_after => 86400000, if_not_exists => TRUE);
"