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
import time
from web3 import Web3
from web3.exceptions import BlockNotFound, TransactionNotFound
from typing import Dict, List, Any, Tuple, Optional
from decimal import Decimal
from datetime import datetime
from database import DatabaseManager
from config import WEB3_PROVIDER, CONTRACT_ADDRESSES, TRADING_ABI, BATCH_SIZE


class EventProcessor:
    def __init__(self, db_manager: DatabaseManager):
        self.w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
        self.db = db_manager
        self.component_name = 'order_listener'
        self.batch_size = BATCH_SIZE
        self.last_processed_block = 0
        self.trading_contract = None
        self.token_cache = {}
        self.contract_cache = {}
        self.last_heartbeat = 0
        self.heartbeat_interval = 300
        self.blocks_processed_count = 0

    async def test_connections(self):
        await self._test_web3_connection()
        await self._test_contract_connection()

    async def _test_web3_connection(self):
        logging.info("Testing Web3 connection...")
        try:
            is_connected = self.w3.is_connected()
            current_block = self.w3.eth.block_number
            chain_id = self.w3.eth.chain_id

            if is_connected:
                logging.info(f"✅ Web3 connected: Chain ID {chain_id}, Current block: {current_block}")
                logging.info(f"📡 Provider: {WEB3_PROVIDER}")
            else:
                raise Exception("Web3 connection test failed")

        except Exception as e:
            logging.error(f"❌ Web3 connection failed: {e}")
            raise

    async def _test_contract_connection(self):
        logging.info("Testing contract connection...")
        try:
            contract_address = CONTRACT_ADDRESSES['Trading']
            logging.info(f"📋 Contract address: {contract_address}")

            self.trading_contract = self.w3.eth.contract(
                address=contract_address,
                abi=TRADING_ABI
            )

            code = self.w3.eth.get_code(contract_address)
            if code and code != '0x':
                logging.info(f"✅ Contract found at {contract_address}")
                logging.info(f"📊 Contract code size: {len(code)} bytes")
            else:
                raise Exception(f"No contract code found at {contract_address}")

        except Exception as e:
            logging.error(f"❌ Contract connection failed: {e}")
            raise

    async def start(self):
        logging.info("🚀 Starting event processor main loop...")
        await self._initialize_state()

        while True:
            try:
                current_time = time.time()

                if current_time - self.last_heartbeat > self.heartbeat_interval:
                    await self._log_heartbeat()
                    self.last_heartbeat = current_time

                await self._process_new_blocks()
                await self.db.save_component_state(self.component_name, self.last_processed_block, 'ACTIVE')
                await asyncio.sleep(5)

            except Exception as e:
                logging.error(f"Event processor error: {e}")
                await self.db.save_component_state(self.component_name, self.last_processed_block, 'ERROR')
                await asyncio.sleep(30)

    async def _log_heartbeat(self):
        current_block = self.w3.eth.block_number
        blocks_behind = current_block - self.last_processed_block
        logging.info(f"💓 PROCESSOR HEARTBEAT: Current block: {current_block}, "
                     f"Last processed: {self.last_processed_block}, "
                     f"Behind: {blocks_behind}, "
                     f"Total processed: {self.blocks_processed_count}")

    async def _initialize_state(self):
        logging.info("Initializing processor state...")
        state = await self.db.get_component_state(self.component_name)
        current_block = self.w3.eth.block_number

        logging.info(f"🔍 Current blockchain block: {current_block}")

        if state is None:
            start_block = max(1, current_block - 200)
            await self.db.save_component_state(self.component_name, start_block, 'ACTIVE')
            self.last_processed_block = start_block
            logging.info(f"🆕 First run: starting from block {start_block}")
            if current_block > start_block:
                logging.warning(f"⚠️ Processing {current_block - start_block} missed blocks from first run")
                await self._process_missed_blocks(start_block + 1, current_block)
        else:
            saved_block = state['last_processed_block']
            saved_status = state.get('status', 'UNKNOWN')

            logging.info(f"📋 Loaded state: block={saved_block}, status={saved_status}")

            if saved_status == 'RECOVERY':
                logging.warning(f"🔄 RECOVERY MODE DETECTED: Forcing reprocessing from block {saved_block} to {current_block}")
                self.last_processed_block = saved_block
                if current_block > saved_block:
                    await self._process_missed_blocks(saved_block + 1, current_block)
                await self.db.save_component_state(self.component_name, current_block, 'ACTIVE')
                logging.info(f"✅ Recovery completed: updated to block {current_block}")
            elif saved_status == 'RESET':
                logging.warning(f"🔄 RESET MODE DETECTED: Forcing reprocessing from block {saved_block} to {current_block}")
                self.last_processed_block = saved_block
                if current_block > saved_block:
                    await self._process_missed_blocks(saved_block + 1, current_block)
                await self.db.save_component_state(self.component_name, current_block, 'ACTIVE')
                logging.info(f"✅ Reset completed: updated to block {current_block}")
            else:
                if saved_block > current_block:
                    logging.warning(f"⚠️ Saved block {saved_block} > current block {current_block}. Resetting to current block.")
                    await self.db.save_component_state(self.component_name, current_block, 'ACTIVE')
                    self.last_processed_block = current_block
                else:
                    self.last_processed_block = saved_block
                    missed_blocks = current_block - self.last_processed_block
                    if missed_blocks > 0:
                        logging.warning(f"⚠️ Processing {missed_blocks} missed blocks ({self.last_processed_block + 1} to {current_block})")
                        await self._process_missed_blocks(self.last_processed_block + 1, current_block)
                    else:
                        logging.info(f"✅ No missed blocks, resuming from block {self.last_processed_block}")

            logging.info(f"🔄 Resumed monitoring from block {self.last_processed_block}")

    async def _process_missed_blocks(self, from_block: int, to_block: int):
        total_blocks = to_block - from_block + 1
        processed = 0
        logging.info(f"🔄 Starting recovery of {total_blocks} blocks (from {from_block} to {to_block})...")

        for start_block in range(from_block, to_block + 1, self.batch_size):
            end_block = min(start_block + self.batch_size - 1, to_block)

            try:
                await self._process_block_range_parallel(start_block, end_block)

                processed += (end_block - start_block + 1)
                progress = (processed / total_blocks) * 100
                logging.info(f"📈 Recovery progress: {progress:.1f}% ({processed}/{total_blocks}) - blocks {start_block}-{end_block}")

                self.last_processed_block = end_block
                await self.db.save_component_state(self.component_name, end_block, 'RECOVERY')

                await asyncio.sleep(0.1)

            except Exception as e:
                logging.error(f"❌ Error processing blocks {start_block}-{end_block}: {e}")
                raise

        self.last_processed_block = to_block
        logging.info(f"✅ Block recovery completed - processed {total_blocks} blocks")

    async def _process_new_blocks(self):
        current_block = self.w3.eth.block_number
        logging.debug(f"🔍 Checking blocks: current={current_block}, last_processed={self.last_processed_block}")

        if current_block > self.last_processed_block:
            blocks_to_process = current_block - self.last_processed_block
            logging.info(f"📦 Processing {blocks_to_process} new blocks: {self.last_processed_block + 1} to {current_block}")

            if current_block - self.last_processed_block > 10:
                await self._process_block_range_parallel(self.last_processed_block + 1, current_block)
            else:
                await self._process_block_range_sequential(self.last_processed_block + 1, current_block)

            self.last_processed_block = current_block
            self.blocks_processed_count += blocks_to_process
            logging.info(f"✅ Completed processing blocks up to {current_block}")
        else:
            logging.debug(f"⏸️  No new blocks to process (current: {current_block})")

    async def _process_block_range_parallel(self, from_block: int, to_block: int):
        logging.debug(f"🔀 Processing blocks {from_block}-{to_block} in parallel...")
        block_numbers = list(range(from_block, to_block + 1))

        async with self.db.transaction() as tx:
            tasks = [self._process_single_block(block_num) for block_num in block_numbers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_events = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logging.error(f"❌ Error processing block {block_numbers[i]}: {result}")
                    raise result
                if result:
                    all_events.extend(result)

            if all_events:
                sorted_events = sorted(all_events, key=lambda x: (x['blockNumber'], x['logIndex']))
                logging.info(f"📋 Processing {len(all_events)} events from blocks {from_block}-{to_block}")

                for event in sorted_events:
                    await self._process_single_event(event, tx)
            else:
                logging.debug(f"📭 No events found in blocks {from_block}-{to_block}")

    async def _process_block_range_sequential(self, from_block: int, to_block: int):
        logging.debug(f"➡️  Processing blocks {from_block}-{to_block} sequentially...")
        async with self.db.transaction() as tx:
            events_batch = await self._get_all_events(from_block, to_block)
            if events_batch:
                sorted_events = sorted(events_batch, key=lambda x: (x['blockNumber'], x['logIndex']))
                logging.info(f"📋 Processing {len(events_batch)} events from blocks {from_block}-{to_block}")

                for event in sorted_events:
                    await self._process_single_event(event, tx)
            else:
                logging.debug(f"📭 No events found in blocks {from_block}-{to_block}")

    async def _process_single_block(self, block_number: int) -> List[Dict]:
        try:
            return await self._get_all_events(block_number, block_number)
        except BlockNotFound:
            logging.warning(f"⚠️  Block {block_number} not found")
            return []
        except Exception as e:
            logging.error(f"❌ Error processing block {block_number}: {e}")
            raise

    async def _get_all_events(self, from_block: int, to_block: int) -> List[Dict]:
        all_events = []
        logging.debug(f"🔍 Scanning blocks {from_block}-{to_block} for events...")

        event_types = [
            ('OrderCreated', 'CREATED'),
            ('OrderExecuted', 'EXECUTED'),
            ('OrderCancelled', 'CANCELLED'),
            ('OrderModified', 'MODIFIED')
        ]

        for event_name, event_type in event_types:
            try:
                events = await asyncio.to_thread(
                    getattr(self.trading_contract.events, event_name).get_logs,
                    fromBlock=from_block,
                    toBlock=to_block
                )
                if events:
                    logging.info(f"🎯 Found {len(events)} {event_name} events in blocks {from_block}-{to_block}")
                for event in events:
                    all_events.append({**dict(event), 'event_type': event_type})
            except Exception as e:
                logging.error(f"❌ Error getting {event_name} events for blocks {from_block}-{to_block}: {e}")

        if not all_events:
            logging.debug(f"📭 No events found in blocks {from_block}-{to_block}")
        else:
            logging.info(f"📊 Total events found: {len(all_events)} in blocks {from_block}-{to_block}")

        return all_events

    async def _process_single_event(self, event: Dict, tx):
        try:
            tx_hash = event['transactionHash'].hex()
            log_index = event['logIndex']
            event_type = event['event_type']

            if await self.db.check_event_processed(tx_hash, log_index, tx):
                logging.debug(f"⏭️  Event {event_type} already processed: {tx_hash}:{log_index}")
                return

            try:
                if event_type == 'CREATED':
                    await self._handle_order_created(event, tx)
                elif event_type == 'EXECUTED':
                    await self._handle_order_executed(event, tx)
                elif event_type == 'CANCELLED':
                    await self._handle_order_cancelled(event, tx)
                elif event_type == 'MODIFIED':
                    await self._handle_order_modified(event, tx)

                await self.db.mark_event_processed(tx_hash, log_index, event_type, tx)
                logging.debug(f"✅ Processed {event_type} event: {tx_hash}:{log_index}")

            except Exception as decode_error:
                logging.error(f"❌ Error processing event type {event_type}: {decode_error}")
                await self.db.mark_event_processed(tx_hash, log_index, event_type, tx)

        except TransactionNotFound:
            logging.debug(f"⚠️  Transaction {event['transactionHash'].hex()} not found, skipping")
            return
        except Exception as e:
            logging.error(f"❌ Error processing event {event['transactionHash'].hex()}: {e}")
            raise

    async def _handle_order_created(self, event, tx):
        order_id = event['args']['orderId']
        user = event['args']['user']
        token_in = event['args']['tokenIn']
        token_out = event['args']['tokenOut']
        amount_in = event['args']['amountIn']

        try:
            logging.debug(f"🔍 Getting order data for order {order_id}...")
            order_data = await self._get_order_data_cached(order_id)

            order_record = {
                'id': order_id,
                'user_address': user,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': self._wei_to_decimal(amount_in),
                'target_price': self._wei_to_decimal(order_data[5]),
                'min_amount_out': self._wei_to_decimal(order_data[6]),
                'order_type': self._get_order_type(order_data[7]),
                'is_long': order_data[8],
                'status': 'PENDING',
                'self_executable': order_data[11],
                'created_at': datetime.fromtimestamp(order_data[10]),
                'tx_hash': event['transactionHash'].hex(),
                'block_number': event['blockNumber']
            }

            await self.db.insert_order(order_record, tx)
            await self.db.insert_order_event(order_id, 'CREATED', None, 'PENDING', event, tx)
            logging.info(f"✅ Order {order_id} created by {user}")

        except Exception as e:
            logging.error(f"❌ Error handling order created {order_id}: {e}")
            raise

    async def _handle_order_executed(self, event, tx):
        order_id = event['args']['orderId']
        executor = event['args']['executor']
        amount_out = event['args']['amountOut']

        update_data = {
            'status': 'EXECUTED',
            'executed_at': datetime.now(),
            'executor_address': executor,
            'amount_out': self._wei_to_decimal(amount_out),
            'execution_tx_hash': event['transactionHash'].hex()
        }

        await self.db.update_order(order_id, update_data, tx)
        await self.db.insert_order_event(order_id, 'EXECUTED', 'PENDING', 'EXECUTED', event, tx)
        logging.info(f"✅ Order {order_id} executed by {executor}")

    async def _handle_order_cancelled(self, event, tx):
        order_id = event['args']['orderId']

        update_data = {
            'status': 'CANCELLED',
            'updated_at': datetime.now()
        }

        await self.db.update_order(order_id, update_data, tx)
        await self.db.insert_order_event(order_id, 'CANCELLED', 'PENDING', 'CANCELLED', event, tx)
        logging.info(f"✅ Order {order_id} cancelled")

    async def _handle_order_modified(self, event, tx):
        order_id = event['args']['orderId']
        new_target_price = event['args']['newTargetPrice']
        new_min_amount_out = event['args']['newMinAmountOut']

        update_data = {
            'target_price': self._wei_to_decimal(new_target_price),
            'min_amount_out': self._wei_to_decimal(new_min_amount_out),
            'updated_at': datetime.now()
        }

        await self.db.update_order(order_id, update_data, tx)
        await self.db.insert_order_event(order_id, 'MODIFIED', 'PENDING', 'PENDING', event, tx)
        logging.info(f"✅ Order {order_id} modified")

    async def _get_order_data_cached(self, order_id: int):
        cache_key = f"order_{order_id}"

        if cache_key in self.contract_cache:
            logging.debug(f"📋 Using cached order data for {order_id}")
            return self.contract_cache[cache_key]

        try:
            logging.debug(f"🔍 Fetching order data from contract for {order_id}")
            order_data = await asyncio.to_thread(
                self.trading_contract.functions.getOrder(order_id).call
            )
            self.contract_cache[cache_key] = order_data
            return order_data
        except Exception as e:
            logging.error(f"❌ Error getting order data for {order_id}: {e}")
            raise

    async def _get_token_info_cached(self, token_address: str) -> Tuple[str, int]:
        cache_key = token_address.lower()

        if cache_key in self.token_cache:
            return self.token_cache[cache_key]

        symbol = "UNKNOWN"
        decimals = 18

        try:
            checksum_address = Web3.to_checksum_address(token_address)
            erc20_abi = [
                {"constant": True, "inputs": [], "name": "decimals",
                 "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "symbol",
                 "outputs": [{"name": "", "type": "string"}], "type": "function"}
            ]

            contract = self.w3.eth.contract(address=checksum_address, abi=erc20_abi)

            try:
                symbol = await asyncio.to_thread(contract.functions.symbol().call)
            except Exception as e:
                logging.debug(f"Failed to get token symbol for {token_address}: {e}")

            try:
                decimals = await asyncio.to_thread(contract.functions.decimals().call)
            except Exception as e:
                logging.debug(f"Failed to get token decimals for {token_address}: {e}")

            self.token_cache[cache_key] = (symbol, decimals)
            return symbol, decimals

        except Exception as e:
            logging.warning(f"Error getting token info for {token_address}: {e}")
            self.token_cache[cache_key] = (symbol, decimals)
            return symbol, decimals

    def _wei_to_decimal(self, wei_value: int) -> Decimal:
        return Decimal(wei_value) / Decimal(10 ** 18)

    def _get_order_type(self, type_enum: int) -> str:
        types = {0: 'LIMIT', 1: 'STOP_LOSS', 2: 'MARKET', 3: 'CONDITIONAL'}
        return types.get(type_enum, 'UNKNOWN')

    def clear_cache(self):
        cache_size = len(self.token_cache) + len(self.contract_cache)
        self.token_cache.clear()
        self.contract_cache.clear()
        logging.info(f"🧹 Cache cleared - removed {cache_size} entries")