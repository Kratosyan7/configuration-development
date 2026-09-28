#!/bin/sh
# Этап 2: параметры задаются только конфигурационным файлом TOML.
set -eu
cd "$(dirname "$0")/.."

echo "=== конфиг задаёт и VFS, и стартовый скрипт ==="
./run.sh run --config config/default.toml

echo "=== конфиг задаёт только VFS ==="
./run.sh run --config config/vfs_only.toml --startup startup/errors.txt
