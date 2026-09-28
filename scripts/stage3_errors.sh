#!/bin/sh
# Этап 3: ошибки загрузки VFS и неизменность данных на диске.
set -u
cd "$(dirname "$0")/.."

echo "=== источника VFS не существует ==="
./run.sh run --vfs data/нет_такой --startup startup/stage3.txt

echo "=== источник VFS не каталог, а файл ==="
./run.sh run --vfs data/vfs_minimal/hello.txt --startup startup/stage3.txt

echo "=== VFS не задана, используется пустая ==="
./run.sh run --startup startup/stage3.txt

echo "=== проверка, что диск не изменился ==="
BEFORE=$(find data -type f -exec shasum -a 256 {} \; | sort | shasum -a 256)
./run.sh run --vfs data/vfs_deep --startup startup/stage3.txt >/dev/null
AFTER=$(find data -type f -exec shasum -a 256 {} \; | sort | shasum -a 256)

if [ "$BEFORE" = "$AFTER" ]; then
    echo "OK: данные VFS на диске не изменились"
else
    echo "ОШИБКА: данные VFS на диске были изменены" >&2
    exit 1
fi
