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
import asyncpg
import sys
import os
from datetime import datetime
from typing import Dict, List, Any


class DatabaseDiagnostics:
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'crypto_user'),
            'password': os.getenv('DB_PASSWORD', 'crypto_pass'),
            'database': os.getenv('DB_NAME', 'crypto_data')
        }
        self.conn = None

    async def connect(self):
        try:
            dsn = f"postgresql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            self.conn = await asyncpg.connect(dsn)
            print(f"✅ Подключение к базе {self.config['database']} на {self.config['host']} успешно")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к базе: {e}")
            print(f"📋 Параметры подключения: host={self.config['host']}, port={self.config['port']}, user={self.config['user']}, db={self.config['database']}")
            return False

    async def check_tables_exist(self):
        print("\n📋 Проверка существования таблиц:")
        tables = ['orders', 'order_events', 'system_state', 'processed_events']
        for table in tables:
            try:
                result = await self.conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                status = "✅ существует" if result else "❌ отсутствует"
                print(f"  {table}: {status}")
            except Exception as e:
                print(f"  {table}: ❌ ошибка проверки - {e}")

    async def count_records(self):
        print("\n📊 Количество записей в таблицах:")
        tables = ['orders', 'order_events', 'system_state', 'processed_events']
        for table in tables:
            try:
                count = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"  {table}: {count} записей")
            except Exception as e:
                print(f"  {table}: ❌ ошибка подсчета - {e}")

    async def show_orders_data(self):
        print("\n🔍 Данные таблицы orders:")
        try:
            rows = await self.conn.fetch("SELECT * FROM orders ORDER BY created_at DESC LIMIT 10")
            if not rows:
                print("  📭 Таблица orders пуста")
                return
            print(f"  📦 Найдено {len(rows)} записей (показаны последние 10):")
            for row in rows:
                print(f"    ID: {row['id']}, Status: {row['status']}, User: {row['user_address'][:10]}..., Created: {row['created_at']}")
        except Exception as e:
            print(f"  ❌ Ошибка чтения orders: {e}")

    async def show_order_events_data(self):
        print("\n📝 Данные таблицы order_events:")
        try:
            rows = await self.conn.fetch("SELECT * FROM order_events ORDER BY timestamp DESC LIMIT 10")
            if not rows:
                print("  📭 Таблица order_events пуста")
                return
            print(f"  📦 Найдено {len(rows)} записей (показаны последние 10):")
            for row in rows:
                print(
                    f"    Order ID: {row['order_id']}, Event: {row['event_type']}, Status: {row['old_status']} -> {row['new_status']}, Time: {row['timestamp']}")
        except Exception as e:
            print(f"  ❌ Ошибка чтения order_events: {e}")

    async def show_system_state(self):
        print("\n⚙️ Состояние системных компонентов:")
        try:
            rows = await self.conn.fetch("SELECT * FROM system_state ORDER BY updated_at DESC")
            if not rows:
                print("  📭 Таблица system_state пуста")
                return
            for row in rows:
                print(f"  🔧 {row['component_name']}: блок {row['last_processed_block']}, статус {row['status']}, обновлен {row['updated_at']}")
        except Exception as e:
            print(f"  ❌ Ошибка чтения system_state: {e}")

    async def show_processed_events(self):
        print("\n🎯 Обработанные события:")
        try:
            count = await self.conn.fetchval("SELECT COUNT(*) FROM processed_events")
            print(f"  📊 Всего обработано событий: {count}")
            if count > 0:
                latest = await self.conn.fetch("SELECT * FROM processed_events ORDER BY processed_at DESC LIMIT 5")
                print("  🕐 Последние 5 событий:")
                for row in latest:
                    print(f"    TX: {row['tx_hash'][:10]}..., Event: {row['event_type']}, Время: {row['processed_at']}")
        except Exception as e:
            print(f"  ❌ Ошибка чтения processed_events: {e}")

    async def test_api_queries(self):
        print("\n🔍 Тестирование запросов API:")
        try:
            pending_query = "SELECT * FROM orders WHERE status = 'PENDING' ORDER BY created_at ASC"
            pending_orders = await self.conn.fetch(pending_query)
            print(f"  📋 PENDING orders (как в API): {len(pending_orders)} записей")
            for order in pending_orders:
                print(f"    ID: {order['id']}, Status: {order['status']}, User: {order['user_address'][:10]}...")

            stats_query = """SELECT status, \
                                    COUNT(*) as count,
                            SUM(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 ELSE 0 END) as last_24h
                             FROM orders \
                             GROUP BY status"""
            stats = await self.conn.fetch(stats_query)
            print(f"  📊 Статистика (как в API):")
            for stat in stats:
                print(f"    {stat['status']}: всего {stat['count']}, за 24ч {stat['last_24h']}")
        except Exception as e:
            print(f"  ❌ Ошибка тестирования API запросов: {e}")

    async def check_statistics_query(self):
        print("\n📈 Проверка запроса статистики:")
        try:
            query = """SELECT status, \
                              COUNT(*) as count,
                      SUM(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 ELSE 0 END) as last_24h
                       FROM orders \
                       GROUP BY status"""
            rows = await self.conn.fetch(query)
            if not rows:
                print("  📭 Нет данных для статистики")
                return
            print("  📊 Статистика по статусам:")
            for row in rows:
                print(f"    {row['status']}: всего {row['count']}, за 24ч {row['last_24h']}")
        except Exception as e:
            print(f"  ❌ Ошибка запроса статистики: {e}")

    async def check_database_connection_info(self):
        print("\n🔗 Информация о подключении:")
        try:
            db_name = await self.conn.fetchval("SELECT current_database()")
            user_name = await self.conn.fetchval("SELECT current_user")
            version = await self.conn.fetchval("SELECT version()")
            print(f"  🗄️ База данных: {db_name}")
            print(f"  👤 Пользователь: {user_name}")
            print(f"  🏷️ Версия PostgreSQL: {version.split(',')[0]}")
        except Exception as e:
            print(f"  ❌ Ошибка получения информации: {e}")

    async def run_diagnostics(self):
        print("🔍 ДИАГНОСТИКА БАЗЫ ДАННЫХ ORDER SYSTEM")
        print("=" * 50)
        if not await self.connect():
            return
        await self.check_database_connection_info()
        await self.check_tables_exist()
        await self.count_records()
        await self.show_system_state()
        await self.show_orders_data()
        await self.show_order_events_data()
        await self.show_processed_events()
        await self.check_statistics_query()
        await self.test_api_queries()
        print("\n" + "=" * 50)
        print(f"✅ Диагностика завершена в {datetime.now().strftime('%H:%M:%S')}")

    async def close(self):
        if self.conn:
            await self.conn.close()


async def main():
    diagnostics = DatabaseDiagnostics()
    try:
        await diagnostics.run_diagnostics()
    except KeyboardInterrupt:
        print("\n🛑 Диагностика прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        await diagnostics.close()


if __name__ == "__main__":
    asyncio.run(main())