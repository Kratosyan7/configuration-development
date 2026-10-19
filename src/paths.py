"""Разрешение UNIX-путей исключительно внутри дерева VFS."""

from vfs import Vfs, VfsError, VfsNode


def node_at(vfs: Vfs, segments: list[str]) -> VfsNode:
    """Возвращает узел по уже проверенным сегментам пути."""
    node = vfs.root
    for name in segments:
        node = node.children[name]
    return node


def require_directory(node: VfsNode) -> None:
    """Отклоняет файл там, где требуется каталог."""
    if not node.is_dir:
        raise VfsError(f"не каталог: {node.name}")


def step(vfs: Vfs, segments: list[str], part: str) -> list[str]:
    """Обрабатывает один компонент, проверяя промежуточный каталог."""
    node = node_at(vfs, segments)
    require_directory(node)
    if part == "..":
        return segments[:-1]
    if part in ("", "."):
        return segments
    if part not in node.children:
        raise VfsError(f"путь не найден: {part}")
    return segments + [part]


def resolve(vfs: Vfs, path: str) -> tuple[list[str], VfsNode]:
    """Разрешает абсолютный или относительный путь, включая . и .. ."""
    if not path:
        raise VfsError("пустой путь")
    segments = [] if path.startswith("/") else list(vfs.cwd)
    for part in path.split("/"):
        segments = step(vfs, segments, part)
    node = node_at(vfs, segments)
    if path.endswith("/"):
        require_directory(node)
    return segments, node
