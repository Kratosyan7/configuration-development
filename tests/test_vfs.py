"""Тесты виртуальной файловой системы."""

import tempfile
import unittest
from pathlib import Path

from vfs import (
    VfsError,
    describe_source,
    empty_vfs,
    format_path,
    load_vfs,
    vfs_hash,
    walk,
)

HASH_LENGTH = 64
HEX_DIGITS = "0123456789abcdef"


class VfsTestCase(unittest.TestCase):
    """Создаёт временную директорию-источник VFS."""

    def prepare_vfs(self):
        """Готовит директорию с тремя уровнями вложенности."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name) / "vfs_demo"

        docs = source / "home" / "user" / "docs"
        docs.mkdir(parents=True)
        (docs / "report.txt").write_text("одна\nдве\n", encoding="utf-8")
        (source / "root.txt").write_text("корень\n", encoding="utf-8")
        (source / "empty").mkdir()
        return source, load_vfs(source)

    def find_node(self, vfs, path: str):
        """Находит узел VFS по текстовому пути через обход дерева."""
        for current, node in walk(vfs.root):
            if current == path:
                return node
        return None


class TestLoading(VfsTestCase):
    """Проверяет загрузку директории в память."""

    def test_name_from_directory(self) -> None:
        """Имя VFS берётся из имени директории."""
        _, vfs = self.prepare_vfs()
        self.assertEqual(vfs.name, "vfs_demo")

    def test_source_is_remembered(self) -> None:
        """Путь к источнику сохраняется в VFS."""
        source, vfs = self.prepare_vfs()
        self.assertEqual(vfs.source, source)

    def test_file_content_is_loaded(self) -> None:
        """Содержимое файла попадает в память целиком."""
        _, vfs = self.prepare_vfs()
        node = self.find_node(vfs, "/home/user/docs/report.txt")
        self.assertFalse(node.is_dir)
        self.assertEqual(node.data, "одна\nдве\n".encode("utf-8"))

    def test_nested_directories_are_loaded(self) -> None:
        """Дерево каталогов загружается на всю глубину."""
        _, vfs = self.prepare_vfs()
        self.assertIsNotNone(self.find_node(vfs, "/home/user/docs"))

    def test_empty_directory_loaded(self) -> None:
        """Пустой каталог тоже попадает в VFS."""
        _, vfs = self.prepare_vfs()
        node = self.find_node(vfs, "/empty")
        self.assertTrue(node.is_dir)
        self.assertEqual(node.children, {})

    def test_missing_source(self) -> None:
        """Сообщает об ошибке, если источника не существует."""
        source, _ = self.prepare_vfs()
        with self.assertRaises(VfsError):
            load_vfs(source / "нет_такого")

    def test_source_is_file(self) -> None:
        """Сообщает об ошибке, если источник не каталог."""
        source, _ = self.prepare_vfs()
        with self.assertRaises(VfsError):
            load_vfs(source / "root.txt")


class TestEmptyVfs(unittest.TestCase):
    """Проверяет пустую VFS для запуска без источника."""

    def test_has_default_name(self) -> None:
        """Пустая VFS получает имя по умолчанию."""
        self.assertEqual(empty_vfs().name, "vfs")

    def test_has_no_source(self) -> None:
        """У пустой VFS источник не задан."""
        self.assertIsNone(empty_vfs().source)

    def test_source_description(self) -> None:
        """Отсутствующий источник описывается словами."""
        self.assertEqual(describe_source(empty_vfs()), "не задан")

    def test_root_is_empty_directory(self) -> None:
        """Корень пустой VFS не содержит узлов."""
        self.assertEqual(empty_vfs().root.children, {})


class TestPaths(unittest.TestCase):
    """Проверяет сборку путей внутри VFS."""

    def test_root_path(self) -> None:
        """Пустой список сегментов даёт корневой путь."""
        self.assertEqual(format_path([]), "/")

    def test_nested_path(self) -> None:
        """Сегменты собираются через разделитель."""
        self.assertEqual(format_path(["home", "user"]), "/home/user")


class TestHash(VfsTestCase):
    """Проверяет подсчёт SHA-256 по данным VFS."""

    def test_hash_is_stable(self) -> None:
        """Повторная загрузка того же источника даёт тот же хеш."""
        source, vfs = self.prepare_vfs()
        self.assertEqual(vfs_hash(vfs), vfs_hash(load_vfs(source)))

    def test_hash_length(self) -> None:
        """Хеш записан 64 шестнадцатеричными цифрами."""
        _, vfs = self.prepare_vfs()
        digest = vfs_hash(vfs)
        self.assertEqual(len(digest), HASH_LENGTH)
        self.assertTrue(all(char in HEX_DIGITS for char in digest))

    def test_hash_changes_with_content(self) -> None:
        """Изменение содержимого файла меняет хеш."""
        _, vfs = self.prepare_vfs()
        before = vfs_hash(vfs)
        self.find_node(vfs, "/root.txt").data = b"other"
        self.assertNotEqual(before, vfs_hash(vfs))

    def test_different_sources_differ(self) -> None:
        """Разные VFS дают разные хеши."""
        _, vfs = self.prepare_vfs()
        self.assertNotEqual(vfs_hash(vfs), vfs_hash(empty_vfs()))

    def test_empty_vfs_has_hash(self) -> None:
        """Пустая VFS тоже имеет хеш."""
        self.assertEqual(len(vfs_hash(empty_vfs())), HASH_LENGTH)


if __name__ == "__main__":
    unittest.main()
