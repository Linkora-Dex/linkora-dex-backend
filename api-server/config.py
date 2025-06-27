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

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'crypto_data')
DB_USER = os.getenv('DB_USER', 'crypto_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'crypto_pass')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

WEBSOCKET_PING_INTERVAL = int(os.getenv('WEBSOCKET_PING_INTERVAL', 30))
WEBSOCKET_PONG_TIMEOUT = int(os.getenv('WEBSOCKET_PONG_TIMEOUT', 60))
WEBSOCKET_CLEANUP_INTERVAL = int(os.getenv('WEBSOCKET_CLEANUP_INTERVAL', 120))

TIMEFRAMES = {
    "1": 1,
    "3": 3,
    "5": 5,
    "15": 15,
    "30": 30,
    "45": 45,
    "1H": 60,
    "2H": 120,
    "3H": 180,
    "4H": 240,
    "1D": 1440,
    "1W": 10080,
    "1M": 43200
}

ORDERBOOK_SUPPORTED_LEVELS = [5, 10, 20]
ORDERBOOK_DEFAULT_LEVELS = 20