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

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class OrderBookLevel(BaseModel):
    price: str
    quantity: str

class OrderBookResponse(BaseModel):
    symbol: str
    timestamp: int
    last_update_id: int
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]

class CandleResponse(BaseModel):
    timestamp: int
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    trades: int
    taker_buy_volume: Decimal
    taker_buy_quote_volume: Decimal

class CandlesRequest(BaseModel):
    symbol: str
    timeframe: str = "1"
    start_date: Optional[datetime] = None
    limit: int = 500

class OrderBookRequest(BaseModel):
    symbol: str
    levels: Optional[int] = 20

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str

class ErrorResponse(BaseModel):
    error: str
    message: str