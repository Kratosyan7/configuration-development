#!/bin/sh
# Этап 3: три варианта VFS и служебная команда vfs-info.
set -eu
cd "$(dirname "$0")/.."

echo "=== минимальная VFS: один файл ==="
./run.sh run --vfs data/vfs_minimal --startup startup/stage3.txt

echo "=== несколько файлов в корне ==="
./run.sh run --vfs data/vfs_flat --startup startup/stage3.txt

echo "=== четыре уровня файлов и папок ==="
./run.sh run --vfs data/vfs_deep --startup startup/stage3.txt
