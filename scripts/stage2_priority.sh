#!/bin/sh
# Этап 2: командная строка имеет приоритет над конфигурационным файлом.
set -eu
cd "$(dirname "$0")/.."

echo "=== конфиг задаёт data/vfs, строка задаёт data/vfs_cli ==="
echo "Ожидается: путь к VFS = data/vfs_cli [командная строка]"
./run.sh run --config config/default.toml --vfs data/vfs_cli

echo "=== переопределён только стартовый скрипт ==="
echo "Ожидается: VFS из файла, скрипт из командной строки"
./run.sh run --config config/default.toml --startup startup/errors.txt
