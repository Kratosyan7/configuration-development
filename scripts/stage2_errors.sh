#!/bin/sh
# Этап 2: ошибки чтения конфигурации и исполнения стартового скрипта.
set -u
cd "$(dirname "$0")/.."

echo "=== конфигурационного файла не существует ==="
./run.sh run --config config/нет_такого.toml || echo "код возврата: $?"

echo "=== повреждённый TOML ==="
./run.sh run --config config/broken.toml || echo "код возврата: $?"

echo "=== неизвестный ключ в конфиге ==="
./run.sh run --config config/unknown_key.toml || echo "код возврата: $?"

echo "=== стартового скрипта не существует ==="
./run.sh run --startup startup/нет_такого.txt

echo "=== скрипт целиком из ошибочных строк ==="
./run.sh run --startup startup/errors.txt
