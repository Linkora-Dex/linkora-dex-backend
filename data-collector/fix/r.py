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

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal, InvalidOperation



def normalize_decimal_value(value_str: str) -> Decimal:
    """Нормализация значений от Binance, включая научную нотацию"""
    try:
        if isinstance(value_str, (int, float)):
            value_str = str(value_str)

        float_val = float(value_str)
        if float_val == 0:
            return Decimal('0')

        return Decimal(str(round(float_val, 8)))
    except (ValueError, TypeError, InvalidOperation) as e:
        print(f"Invalid decimal value '{value_str}': {e}")
        return Decimal('0')


d = normalize_decimal_value("0E-8")
print(d)
