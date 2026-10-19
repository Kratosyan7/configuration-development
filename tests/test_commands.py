"""Поведенческие проверки основных команд варианта 14."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from emulator import CLEAR, ERROR, CommandError, execute_line, run_script
from vfs import VfsNode, empty_vfs, vfs_hash


class CommandTests(unittest.TestCase):
    """Готовит дерево с Unicode, бинарными данными и вложенными папками."""

    def setUp(self):
        """Создаёт независимую VFS для каждой проверки."""
        self.vfs = empty_vfs()
        docs = VfsNode("My Docs", True)
        text = "один два\nтри".encode()
        docs.children["text"] = VfsNode("text", False, text)
        self.vfs.root.children = {
            "My Docs": docs,
            "ascii": VfsNode("ascii", False, b"one two\nthree\n"),
            "empty": VfsNode("empty", False),
            ".hidden": VfsNode(".hidden", False),
            "binary": VfsNode("binary", False, b"\xff\x00\n"),
            "-dash": VfsNode("-dash", False, b"a"),
        }

    def output(self, line):
        """Выполняет команду в подготовленном сеансе."""
        return execute_line(self.vfs, line).output

    def test_ls_default_hidden_and_sorted(self):
        """Показывает только непосредственных видимых детей по порядку."""
        names = self.output("ls").splitlines()
        self.assertEqual(names, sorted(names))
        self.assertIn("My Docs", names)
        self.assertNotIn("text", names)
        self.assertNotIn(".hidden", names)
        self.assertIn(".hidden", self.output("ls -a"))

    def test_ls_long_multiple_and_file(self):
        """Поддерживает длинный вывод, файлы и несколько операндов."""
        self.assertIn("ascii", self.output("ls -l ascii"))
        self.assertIn(".:\n", self.output("ls -al . ascii"))
        self.assertEqual(self.output("ls -- -dash"), "-dash")

    def test_cd_paths_and_default(self):
        """Поддерживает пробелы, абсолютные пути, . и .. и корень."""
        self.output('cd "My Docs"')
        self.assertEqual(self.output("ls"), "text")
        self.output("cd ./.././")
        self.assertEqual(self.vfs.cwd, [])
        self.output('cd "/../../My Docs"')
        self.assertEqual(self.vfs.cwd, ["My Docs"])
        self.output("cd")
        self.assertEqual(self.vfs.cwd, [])

    def test_invalid_paths_leave_cwd_unchanged(self):
        """Не позволяет обходить отсутствующий каталог или файл через .. ."""
        for path in ("ascii", "ascii/..", "missing/..", '""'):
            with self.subTest(path=path), self.assertRaises(CommandError):
                self.output(f"cd {path}")
            self.assertEqual(self.vfs.cwd, [])

    def test_environment_expansion_uses_virtual_paths(self):
        """Значение переменной с пробелом остаётся одним путём VFS."""
        with patch.dict("os.environ", {"VFS_DOCS": "/My Docs"}):
            self.output("cd $VFS_DOCS")
        self.assertEqual(self.output("ls"), "text")

    def test_wc_default_and_flags(self):
        """Считает строки по LF, слова, байты и отдельные режимы."""
        self.assertEqual(self.output("wc ascii"), "2 3 14 ascii")
        self.assertEqual(self.output("wc -l ascii"), "2 ascii")
        self.assertEqual(self.output("wc -w ascii"), "3 ascii")
        self.assertEqual(self.output("wc -c ascii"), "14 ascii")
        self.assertEqual(self.output("wc -m ascii"), "14 ascii")

    def test_wc_unicode_and_unterminated_line(self):
        """Различает символы и байты, не считает незавершённую строку LF."""
        self.output('cd "My Docs"')
        self.assertEqual(self.output("wc -lwmc text"), "1 3 12 22 text")

    def test_wc_empty_totals_and_separator(self):
        """Обрабатывает пустой файл, итоги и имя с дефисом."""
        self.assertEqual(self.output("wc empty"), "0 0 0 empty")
        self.assertTrue(self.output("wc -l ascii empty").endswith("2 итого"))
        self.assertEqual(self.output("wc -c -- -dash"), "1 -dash")

    def test_wc_binary_and_errors(self):
        """Бинарный файл допускает счёт байтов и LF, но не слов UTF-8."""
        self.assertEqual(self.output("wc -lc binary"), "1 3 binary")
        for line in ("wc", "wc -x ascii", "wc missing", 'wc "My Docs"',
                     "wc binary", "ls -x", "ls ascii/", "clear extra"):
            with self.subTest(line=line), self.assertRaises(CommandError):
                self.output(line)

    def test_clear_preserves_vfs_and_directory(self):
        """Очистка экрана не меняет файловые данные и текущую папку."""
        self.output('cd "My Docs"')
        before = vfs_hash(self.vfs)
        result = execute_line(self.vfs, "clear")
        self.assertTrue(result.should_clear)
        self.assertEqual(self.vfs.cwd, ["My Docs"])
        self.assertEqual(vfs_hash(self.vfs), before)

    def test_script_clear_errors_and_state(self):
        """Скрипт сохраняет cwd, регистрирует очистку и продолжает ошибки."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.txt"
            path.write_text('cd "My Docs"\nclear\nwc missing\nwc -l text\n',
                            encoding="utf-8")
            result = run_script(self.vfs, path)
        self.assertIn((CLEAR, ""), result.events)
        self.assertIn(ERROR, [kind for kind, _ in result.events])
        self.assertEqual(result.events[-1][1], "1 text")


if __name__ == "__main__":
    unittest.main()
