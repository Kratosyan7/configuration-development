#!/bin/sh
# Этап 2: параметры задаются только командной строкой.
set -eu
cd "$(dirname "$0")/.."

echo "=== без параметров вообще ==="
./run.sh run --startup startup/stage2.txt

echo "=== только --vfs ==="
./run.sh run --vfs data/vfs --startup startup/stage2.txt

echo "=== --vfs и --startup вместе ==="
./run.sh run --vfs data/vfs_other --startup startup/errors.txt
