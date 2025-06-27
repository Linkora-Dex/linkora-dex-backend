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


echo "=== Проверка структуры таблиц ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "\dt"

echo -e "\n=== Проверяем ордера ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT id, user_address, order_type, status, amount_in, created_at FROM orders ORDER BY id DESC LIMIT 10;"

echo -e "\n=== Проверяем события ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT id, order_id, event_type, old_status, new_status, timestamp FROM order_events ORDER BY id DESC LIMIT 10;"

echo -e "\n=== Статистика по статусам ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT status, COUNT(*) FROM orders GROUP BY status;"

echo -e "\n=== Общая статистика таблиц ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT 'orders' as table_name, COUNT(*) as count FROM orders UNION ALL SELECT 'order_events' as table_name, COUNT(*) as count FROM order_events;"

echo -e "\n=== Проверка PENDING ордеров ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT id, user_address, order_type, status FROM orders WHERE status = 'PENDING';"


