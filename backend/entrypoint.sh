#!/bin/sh
set -e
# Миграции и таблица кэша выполняются при каждом старте (идемпотентно)
python manage.py migrate --noinput
python manage.py createcachetable
exec "$@"
