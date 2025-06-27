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
import json
from typing import Dict

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), 'artifacts')


def load_contract_abi(contract_name: str) -> list:
    abi_path = os.path.join(ARTIFACTS_DIR, 'contracts', 'core', f'{contract_name}.sol', f'{contract_name}.json')

    try:
        with open(abi_path, 'r') as f:
            contract_data = json.load(f)
            return contract_data['abi']
    except FileNotFoundError:
        raise FileNotFoundError(f"ABI file not found: {abi_path}")
    except KeyError:
        raise KeyError(f"'abi' key not found in contract file: {abi_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in contract file: {abi_path}")



DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'crypto_data')
DB_USER = os.getenv('DB_USER', 'crypto_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'crypto_pass')


DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,

}

CONTRACT_ADDRESSES = {
    'Router': os.getenv('ROUTER_ADDRESS', '0x8A791620dd6260079BF849Dc5567aDC3F2FdC318'),
    'Trading': os.getenv('TRADING_ADDRESS', '0x610178dA211FEF7D417bC0e6FeD39F05609AD788'),
    'Oracle': os.getenv('ORACLE_ADDRESS', '0xa513E6E4b8f2a923D98304ec87F64353C4D5C853')
}

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

WEB3_PROVIDER = os.getenv('WEB3_PROVIDER', 'http://localhost:8545')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 1000))

API_PORT = int(os.getenv('API_PORT', 8080))

TRADING_ABI = load_contract_abi('Trading')
ROUTER_ABI = load_contract_abi('Router')
ORACLE_ABI = load_contract_abi('Oracle')