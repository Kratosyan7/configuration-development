"""Виртуальная файловая система в памяти.

Этап 3 варианта №14. Источником VFS является директория на диске
пользователя. Данные читаются один раз при запуске и целиком
помещаются в память, на диске эмулятор ничего не изменяет.

Константа DEFAULT_VFS_NAME используется, когда источник не задан
и эмулятор работает с пустой VFS. Константа SEPARATOR разделяет
сегменты пути внутри VFS.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_VFS_NAME = "vfs"

ROOT_PATH = "/"
SEPARATOR = "/"

NO_SOURCE = "не задан"

MISSING_ERROR = "источник VFS не найден: {path}"
NOT_DIR_ERROR = "источник VFS не является каталогом: {path}"
READ_ERROR = "не удалось прочитать VFS: {reason}"


class VfsError(Exception):
    """Ошибка загрузки виртуальной файловой системы."""


@dataclass
class VfsNode:
    """Узел VFS: файл или каталог."""

    name: str
    is_dir: bool
    data: bytes = b""
    children: dict[str, "VfsNode"] = field(default_factory=dict)


@dataclass
class Vfs:
    """Загруженная виртуальная файловая система."""

    name: str
    root: VfsNode
    source: Path | None = None


def empty_vfs(name: str = DEFAULT_VFS_NAME) -> Vfs:
    """Создаёт пустую VFS для запуска без источника данных."""
    return Vfs(name=name, root=VfsNode(name=ROOT_PATH, is_dir=True))


def load_vfs(path: Path) -> Vfs:
    """Загружает директорию с диска в память.

    Вызывает VfsError, если путь не существует, не является каталогом
    или недоступен для чтения.
    """
    if not path.exists():
        raise VfsError(MISSING_ERROR.format(path=path))
    if not path.is_dir():
        raise VfsError(NOT_DIR_ERROR.format(path=path))

    try:
        root = read_directory(path)
    except OSError as error:
        raise VfsError(READ_ERROR.format(reason=error)) from error
    return Vfs(name=path.name or DEFAULT_VFS_NAME, root=root, source=path)


def read_directory(path: Path) -> VfsNode:
    """Рекурсивно читает каталог с диска в узел VFS."""
    node = VfsNode(name=path.name or ROOT_PATH, is_dir=True)
    for entry in sorted(path.iterdir(), key=lambda item: item.name):
        if entry.is_dir():
            node.children[entry.name] = read_directory(entry)
        elif entry.is_file():
            node.children[entry.name] = VfsNode(
                name=entry.name,
                is_dir=False,
                data=entry.read_bytes(),
            )
    return node


def format_path(segments: list[str]) -> str:
    """Собирает текстовый путь из списка сегментов."""
    if not segments:
        return ROOT_PATH
    return ROOT_PATH + SEPARATOR.join(segments)


def walk(node: VfsNode, prefix: list[str] | None = None):
    """Обходит дерево VFS в устойчивом порядке.

    Порядок обхода задан сортировкой имён, поэтому он не зависит
    от файловой системы и одинаков между запусками.
    """
    segments = prefix or []
    yield format_path(segments), node
    for name in sorted(node.children):
        yield from walk(node.children[name], segments + [name])


def vfs_hash(vfs: Vfs) -> str:
    """Считает SHA-256 по именам и содержимому всех узлов VFS."""
    digest = hashlib.sha256()
    for path, node in walk(vfs.root):
        digest.update(path.encode("utf-8"))
        digest.update(b"\x00")
        if not node.is_dir:
            digest.update(node.data)
        digest.update(b"\x00")
    return digest.hexdigest()


def describe_source(vfs: Vfs) -> str:
    """Представляет источник VFS для служебного вывода."""
    return str(vfs.source) if vfs.source is not None else NO_SOURCE
