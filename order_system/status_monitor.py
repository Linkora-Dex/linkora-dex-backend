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

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from database import DatabaseManager
from web3 import Web3
from config import WEB3_PROVIDER


class StatusMonitor:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
        self.component_name = 'status_monitor'

    async def start(self):
        while True:
            try:
                await self._check_system_health()
                await self._check_expired_orders()
                await self._update_component_status('ACTIVE')
                await asyncio.sleep(60)

            except Exception as e:
                logging.error(f"Status monitor error: {e}")
                await self._update_component_status('ERROR')
                await asyncio.sleep(120)

    async def _check_system_health(self):
        components = ['order_listener']
        current_block = self.w3.eth.block_number

        for component in components:
            state = await self.db.get_component_state(component)

            if state is None:
                logging.warning(f"Component {component} not initialized")
                continue

            if state['status'] == 'ERROR':
                logging.error(f"Component {component} in ERROR state")
                continue

            block_lag = current_block - state['last_processed_block']
            if block_lag > 100:
                logging.warning(f"Component {component} lagging by {block_lag} blocks")

            time_since_update = datetime.now() - state['updated_at']
            if time_since_update > timedelta(minutes=10):
                logging.warning(f"Component {component} last updated {time_since_update} ago")

    async def _check_expired_orders(self):
        cutoff_date = datetime.now() - timedelta(days=30)

        query = """UPDATE orders \
                   SET status     = 'EXPIRED', \
                       updated_at = CURRENT_TIMESTAMP
                   WHERE status = 'PENDING' \
                     AND created_at < $1"""

        async with self.db.pool.acquire() as conn:
            result = await conn.execute(query, cutoff_date)

            if result.startswith('UPDATE'):
                expired_count = int(result.split()[1])
                if expired_count > 0:
                    logging.info(f"Expired {expired_count} old orders")

    async def _update_component_status(self, status: str):
        await self.db.save_component_state(self.component_name, 0, status)

    async def get_health_report(self) -> Dict[str, str]:
        components = ['order_listener', 'status_monitor']
        health_report = {}
        current_block = self.w3.eth.block_number

        for component in components:
            state = await self.db.get_component_state(component)

            if state is None:
                health_report[component] = 'NOT_INITIALIZED'
            elif state['status'] == 'ERROR':
                health_report[component] = 'ERROR'
            elif state['status'] == 'ACTIVE':
                if component == 'order_listener':
                    lag = current_block - state['last_processed_block']
                    if lag > 100:
                        health_report[component] = f'LAGGING_{lag}_BLOCKS'
                    else:
                        health_report[component] = 'HEALTHY'
                else:
                    health_report[component] = 'HEALTHY'
            else:
                health_report[component] = state['status']

        return health_report