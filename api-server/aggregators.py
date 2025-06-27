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

import logging
from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime
import config
from utils import normalize_decimal_for_api

logger = logging.getLogger(__name__)

class CandleAggregator:
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.timeframe_minutes = config.TIMEFRAMES.get(timeframe, 1)
        self.current_candle = None
        self.current_period_start = None

    def get_period_start(self, timestamp: int) -> int:
        dt = datetime.fromtimestamp(timestamp / 1000)

        if self.timeframe_minutes == 1:
            period_start = dt.replace(second=0, microsecond=0)
        elif self.timeframe_minutes == 5:
            period_start = dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
        elif self.timeframe_minutes == 15:
            period_start = dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)
        elif self.timeframe_minutes == 30:
            period_start = dt.replace(minute=(dt.minute // 30) * 30, second=0, microsecond=0)
        elif self.timeframe_minutes == 60:
            period_start = dt.replace(minute=0, second=0, microsecond=0)
        elif self.timeframe_minutes == 240:
            period_start = dt.replace(hour=(dt.hour // 4) * 4, minute=0, second=0, microsecond=0)
        elif self.timeframe_minutes == 480:
            period_start = dt.replace(hour=(dt.hour // 8) * 8, minute=0, second=0, microsecond=0)
        elif self.timeframe_minutes == 720:
            period_start = dt.replace(hour=(dt.hour // 12) * 12, minute=0, second=0, microsecond=0)
        elif self.timeframe_minutes == 1440:
            period_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            minutes_offset = (dt.minute // self.timeframe_minutes) * self.timeframe_minutes
            period_start = dt.replace(minute=minutes_offset, second=0, microsecond=0)

        return int(period_start.timestamp() * 1000)

    def add_minute_candle(self, candle_data: dict) -> Optional[dict]:
        try:
            timestamp = int(candle_data["timestamp"])
            period_start = self.get_period_start(timestamp)

            if self.timeframe_minutes == 1:
                return self._format_candle(candle_data, period_start)

            if self.current_period_start is None or period_start != self.current_period_start:
                completed_candle = None
                if self.current_candle is not None:
                    completed_candle = self._format_candle(self.current_candle, self.current_period_start)

                self._start_new_period(candle_data, period_start)
                return completed_candle
            else:
                self._update_current_period(candle_data)
                return None

        except Exception as e:
            logger.error(f"Error in candle aggregation for {self.symbol}:{self.timeframe}: {e}")
            return None

    def get_current_candle(self) -> Optional[dict]:
        if self.current_candle is not None and self.current_period_start is not None:
            return self._format_candle(self.current_candle, self.current_period_start)
        return None

    def _start_new_period(self, candle_data: dict, period_start: int):
        self.current_period_start = period_start
        self.current_candle = {
            "timestamp": period_start,
            "open": Decimal(str(candle_data["open"])),
            "high": Decimal(str(candle_data["high"])),
            "low": Decimal(str(candle_data["low"])),
            "close": Decimal(str(candle_data["close"])),
            "volume": Decimal(str(candle_data["volume"])),
            "quote_volume": Decimal(str(candle_data["quote_volume"])),
            "trades": int(candle_data["trades"])
        }

    def _update_current_period(self, candle_data: dict):
        self.current_candle["high"] = max(self.current_candle["high"], Decimal(str(candle_data["high"])))
        self.current_candle["low"] = min(self.current_candle["low"], Decimal(str(candle_data["low"])))
        self.current_candle["close"] = Decimal(str(candle_data["close"]))
        self.current_candle["volume"] += Decimal(str(candle_data["volume"]))
        self.current_candle["quote_volume"] += Decimal(str(candle_data["quote_volume"]))
        self.current_candle["trades"] += int(candle_data["trades"])

    def _format_candle(self, candle_data: dict, timestamp: int) -> dict:
        if isinstance(candle_data, dict) and "timestamp" in candle_data and isinstance(candle_data.get("open"), str):
            return {
                "symbol": self.symbol,
                "timestamp": timestamp,
                "open": candle_data["open"],
                "high": candle_data["high"],
                "low": candle_data["low"],
                "close": candle_data["close"],
                "volume": candle_data["volume"],
                "quote_volume": candle_data["quote_volume"],
                "trades": candle_data["trades"]
            }

        return {
            "symbol": self.symbol,
            "timestamp": timestamp,
            "open": normalize_decimal_for_api(candle_data["open"]),
            "high": normalize_decimal_for_api(candle_data["high"]),
            "low": normalize_decimal_for_api(candle_data["low"]),
            "close": normalize_decimal_for_api(candle_data["close"]),
            "volume": normalize_decimal_for_api(candle_data["volume"]),
            "quote_volume": normalize_decimal_for_api(candle_data["quote_volume"]),
            "trades": candle_data["trades"]
        }

    def force_complete_current(self) -> Optional[dict]:
        if self.current_candle is not None and self.current_period_start is not None:
            completed = self._format_candle(self.current_candle, self.current_period_start)
            self.current_candle = None
            self.current_period_start = None
            return completed
        return None
