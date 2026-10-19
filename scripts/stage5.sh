#!/bin/sh
# Демонстрация изменения VFS только в оперативной памяти.
set -eu
cd "$(dirname "$0")/.."
sh ./run.sh run --vfs data/vfs_deep --startup startup/stage5.txt
