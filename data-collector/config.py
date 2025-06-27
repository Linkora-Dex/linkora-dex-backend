#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

import os
from datetime import datetime

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'crypto_data')
DB_USER = os.getenv('DB_USER', 'crypto_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'crypto_pass')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

BINANCE_BASE_URL = os.getenv('BINANCE_BASE_URL', 'https://api.binance.com')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT']
START_DATE = datetime(2025, 1, 1)
INTERVAL = '1m'
BATCH_SIZE = 1000
RETRY_DELAY = 1
MAX_RETRIES = 5
REALTIME_INTERVAL = 0.5

ORDERBOOK_SYMBOLS = os.getenv('ORDERBOOK_SYMBOLS', 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,BNBUSDT').split(',')
ORDERBOOK_LEVELS = int(os.getenv('ORDERBOOK_LEVELS', 20))
ORDERBOOK_UPDATE_INTERVAL = int(os.getenv('ORDERBOOK_UPDATE_INTERVAL', 1))
ORDERBOOK_RETRY_DELAY = int(os.getenv('ORDERBOOK_RETRY_DELAY', 1))
ORDERBOOK_MAX_RETRIES = int(os.getenv('ORDERBOOK_MAX_RETRIES', 3))


