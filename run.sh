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

docker-compose up --build





# Запуск сервисов
# docker-compose up

# Запуск в фоновом режиме
# docker-compose up -d

# Запуск с пересборкой образов
# docker-compose up --build

# Остановка и удаление контейнеров
# docker-compose down

# Остановка контейнеров без удаления
# docker-compose stop

# Запуск остановленных контейнеров
# docker-compose start

# Перезапуск контейнеров
# docker-compose restart

# Сборка всех образов
# docker-compose build

# Сборка конкретного сервиса
# docker-compose build [service]

# Сборка без использования кеша
# docker-compose build --no-cache

# Список запущенных контейнеров
# docker-compose ps

# Просмотр логов всех сервисов
# docker-compose logs

# Логи конкретного сервиса
# docker-compose logs [service]

# Следить за логами в реальном времени
# docker-compose logs -f

# Выполнение команды в запущенном контейнере
# docker-compose exec [service] [command]

# Запуск нового контейнера для выполнения команды
# docker-compose run [service] [command]

# Загрузка актуальных образов
# docker-compose pull

# Удаление контейнеров и томов
# docker-compose down -v

# Проверка конфигурации файла
# docker-compose config