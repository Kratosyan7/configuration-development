#!/bin/sh
# Демонстрация основных команд варианта 14.
set -eu
cd "$(dirname "$0")/.."
sh ./run.sh run --vfs data/vfs_deep --startup startup/stage4.txt
