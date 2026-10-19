"""Команды touch и chown: изменение только виртуальных объектов в памяти."""

import re
import time

from commands import parse_options
from paths import require_directory, resolve
from vfs import Vfs, VfsError, VfsNode, walk

CHOWN_MIN_OPERANDS = 2
IDENTITY_PATTERN = re.compile(r"[\w.-]+")


def touch_target(vfs: Vfs, path: str, no_create: bool):
    """Находит узел либо создаёт пустой файл у существующего родителя."""
    if not path:
        raise VfsError("пустой путь")
    parent_path, separator, name = path.rpartition("/")
    if name in ("", ".", ".."):
        return resolve(vfs, path)[1]
    parent_path = (parent_path or "/") if separator else "."
    _, parent = resolve(vfs, parent_path)
    require_directory(parent)
    if name not in parent.children:
        if no_create:
            return None
        parent.children[name] = VfsNode(name, False)
    return parent.children[name]


def touch(vfs: Vfs, args: list[str]) -> str:
    """Создаёт файлы или обновляет время; -a, -m, -c, несколько путей."""
    flags, paths = parse_options(args, "amc")
    if not paths:
        raise VfsError("touch: укажите путь")
    clocks = flags & {"a", "m"} or {"a", "m"}
    timestamp = time.time_ns()
    for path in paths:
        node = touch_target(vfs, path, "c" in flags)
        if node is None:
            continue
        update_times(node, clocks, timestamp)
    return ""


def update_times(node: VfsNode, clocks: set[str], timestamp: int) -> None:
    """Обновляет выбранные временные метки без изменения содержимого."""
    if "a" in clocks:
        node.accessed_ns = timestamp
    if "m" in clocks:
        node.modified_ns = timestamp


def parse_identity(spec: str) -> tuple[str | None, str | None]:
    """Разбирает OWNER, OWNER:GROUP и :GROUP без обращения к учёткам ОС."""
    owner, separator, group = spec.partition(":")
    names = [owner] if not separator else [group]
    if owner and separator:
        names.append(owner)
    if not all(IDENTITY_PATTERN.fullmatch(name) for name in names):
        raise VfsError(f"неверный владелец или группа: {spec}")
    return owner or None, group or None


def set_ownership(node: VfsNode, owner, group) -> None:
    """Назначает только указанные поля виртуального владельца и группы."""
    if owner is not None:
        node.owner = owner
    if group is not None:
        node.group = group


def chown(vfs: Vfs, args: list[str]) -> str:
    """Меняет владельца и/или группу, -R обходит всё поддерево."""
    flags, operands = parse_options(args, "R")
    if len(operands) < CHOWN_MIN_OPERANDS:
        raise VfsError("chown: укажите владельца и путь")
    owner, group = parse_identity(operands[0])
    for path in operands[1:]:
        _, node = resolve(vfs, path)
        targets = walk(node) if "R" in flags else [(path, node)]
        for _, target in targets:
            set_ownership(target, owner, group)
    return ""
