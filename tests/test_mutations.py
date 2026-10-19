"""Проверки touch, chown и неизменности физического источника VFS."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from emulator import ERROR, CommandError, execute_line, run_script
from paths import resolve
from vfs import DEFAULT_GROUP, DEFAULT_OWNER, load_vfs, vfs_hash


class MutationTests(unittest.TestCase):
    """Проверяет изменение только копии файловой системы в памяти."""

    def setUp(self):
        """Создаёт реальный источник и загружает независимую VFS."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name)
        (self.source / "docs" / "nested").mkdir(parents=True)
        (self.source / "docs" / "text").write_bytes(b"one two\n")
        (self.source / "docs" / "nested" / ".hidden").write_bytes(b"secret")
        (self.source / "root.txt").write_bytes(b"root\n")
        self.vfs = load_vfs(self.source)

    def command(self, line):
        """Выполняет команду и возвращает её результат."""
        return execute_line(self.vfs, line)

    def node(self, path):
        """Получает узел по виртуальному пути."""
        return resolve(self.vfs, path)[1]

    def snapshot(self):
        """Сохраняет состав, содержимое и время изменения файлов на диске."""
        return {str(path.relative_to(self.source)):
                (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.source.rglob("*") if path.is_file()}

    def test_touch_creates_empty_files_with_spaces(self):
        """Создаёт несколько пустых файлов и поддерживает кавычки."""
        self.command('touch first "second file"')
        self.assertEqual(self.node("first").data, b"")
        self.assertFalse(self.node("second file").is_dir)
        self.assertEqual(self.node("first").owner, DEFAULT_OWNER)
        self.assertEqual(self.command("wc first").output, "0 0 0 first")

    def test_touch_relative_absolute_and_separator(self):
        """Разрешает пути относительно cwd и абсолютные пути."""
        self.command("cd docs")
        self.command("touch relative /absolute")
        self.command("touch -- -dash")
        self.assertEqual(self.node("/docs/relative").data, b"")
        self.assertEqual(self.node("/absolute").data, b"")
        self.assertEqual(self.node("/docs/-dash").data, b"")

    def test_touch_preserves_content_and_updates_both_times(self):
        """Повторный touch не обнуляет файл, обновляя обе метки."""
        node = self.node("root.txt")
        with patch("mutations.time.time_ns", return_value=12345):
            self.command("touch root.txt")
        self.assertEqual(node.data, b"root\n")
        self.assertEqual(node.accessed_ns, 12345)
        self.assertEqual(node.modified_ns, 12345)

    def test_touch_access_only(self):
        """Ключ -a оставляет время модификации без изменений."""
        node = self.node("root.txt")
        before = node.modified_ns
        with patch("mutations.time.time_ns", return_value=12345):
            self.command("touch -a root.txt")
        self.assertEqual(node.accessed_ns, 12345)
        self.assertEqual(node.modified_ns, before)

    def test_touch_modification_only_and_combined_flags(self):
        """Ключ -m меняет только mtime, -am меняет обе метки."""
        node = self.node("root.txt")
        before = node.accessed_ns
        with patch("mutations.time.time_ns", return_value=12345):
            self.command("touch -m root.txt")
        self.assertEqual(node.accessed_ns, before)
        self.assertEqual(node.modified_ns, 12345)
        with patch("mutations.time.time_ns", return_value=67890):
            self.command("touch -am root.txt")
        self.assertEqual((node.accessed_ns, node.modified_ns), (67890, 67890))

    def test_touch_no_create(self):
        """Ключ -c пропускает новый файл, но обновляет существующий."""
        with patch("mutations.time.time_ns", return_value=12345):
            self.command("touch -c missing root.txt")
        self.assertNotIn("missing", self.vfs.root.children)
        self.assertEqual(self.node("root.txt").modified_ns, 12345)

    def test_touch_directory_and_invalid_paths(self):
        """Обновляет существующую папку и проверяет промежуточные пути."""
        with patch("mutations.time.time_ns", return_value=12345):
            self.command("touch docs/")
        self.assertEqual(self.node("docs").modified_ns, 12345)
        for path in ('""', "missing/child", "root.txt/child", "new/",
                     "root.txt/../new"):
            with self.subTest(path=path), self.assertRaises(CommandError):
                self.command(f"touch {path}")

    def test_touch_rejects_missing_arguments_and_flags(self):
        """Некорректные вызовы дают ошибку без добавления файлов."""
        before = vfs_hash(self.vfs)
        for line in ("touch", "touch --", "touch -x new"):
            with self.subTest(line=line), self.assertRaises(CommandError):
                self.command(line)
        self.assertEqual(vfs_hash(self.vfs), before)

    def test_chown_owner_group_and_both(self):
        """Позволяет менять владельца и группу независимо."""
        self.command("chown alice root.txt")
        self.assertEqual(self.node("root.txt").owner, "alice")
        self.assertEqual(self.node("root.txt").group, DEFAULT_GROUP)
        self.command("chown :staff root.txt")
        self.assertEqual(self.node("root.txt").owner, "alice")
        self.assertEqual(self.node("root.txt").group, "staff")
        self.command("chown bob:editors root.txt docs")
        self.assertEqual(self.node("docs").owner, "bob")
        self.assertEqual(self.node("root.txt").group, "editors")

    def test_chown_recursive_includes_hidden_descendants(self):
        """Рекурсивный режим меняет весь выбранный каталог."""
        self.command("chown -R alice:staff docs")
        for path in ("docs", "docs/text", "docs/nested/.hidden"):
            with self.subTest(path=path):
                self.assertEqual(self.node(path).owner, "alice")
                self.assertEqual(self.node(path).group, "staff")
        self.assertEqual(self.node("root.txt").owner, DEFAULT_OWNER)

    def test_chown_nonrecursive_and_numeric_identity(self):
        """Без -R не меняет детей, числовые идентификаторы допустимы."""
        self.command("chown -- 1000:100 docs")
        self.assertEqual(self.node("docs").owner, "1000")
        self.assertEqual(self.node("docs").group, "100")
        self.assertEqual(self.node("docs/text").owner, DEFAULT_OWNER)

    def test_chown_root_and_relative_paths(self):
        """Обрабатывает корень рекурсивно и пути относительно cwd."""
        self.command("chown -R -- admin:all /")
        self.assertEqual(self.vfs.root.owner, "admin")
        self.assertEqual(self.node("root.txt").owner, "admin")
        self.command("cd docs")
        self.command("chown author text")
        self.assertEqual(self.node("text").owner, "author")

    def test_chown_errors_preserve_node(self):
        """Неверные режимы и операнды не меняют выбранный файл."""
        cases = ("chown", "chown -R", "chown alice", "chown : root.txt",
                 "chown alice: root.txt", "chown a:b:c root.txt",
                 'chown "bad name" root.txt', "chown -z a root.txt",
                 "chown a missing")
        for line in cases:
            with self.subTest(line=line), self.assertRaises(CommandError):
                self.command(line)
        self.assertEqual(self.node("root.txt").owner, DEFAULT_OWNER)

    def test_metadata_visible_in_ls_but_not_content_hash(self):
        """Метаданные видны в ls -l, SHA-256 остаётся хешем данных."""
        before = vfs_hash(self.vfs)
        self.command("chown alice:staff root.txt")
        self.command("touch root.txt")
        self.assertIn("alice:staff", self.command("ls -l root.txt").output)
        self.assertEqual(vfs_hash(self.vfs), before)
        self.command("touch new")
        self.assertNotEqual(vfs_hash(self.vfs), before)

    def test_disk_unchanged_and_reload_discards_mutations(self):
        """Изменения не затрагивают исходник и исчезают при перезагрузке."""
        before = self.snapshot()
        self.command("touch new docs/text")
        self.command("chown -R alice:staff /")
        self.assertEqual(self.snapshot(), before)
        fresh = load_vfs(self.source)
        self.assertNotIn("new", fresh.root.children)
        self.assertEqual(fresh.root.owner, DEFAULT_OWNER)

    def test_script_continues_errors_and_exit_stops_changes(self):
        """Скрипт сохраняет изменения между строками, уважая exit."""
        script = self.source / "script.txt"
        script.write_text("touch one\nchown : one\nchown alice one\n"
                          "exit\ntouch ignored\n", encoding="utf-8")
        result = run_script(self.vfs, script)
        self.assertTrue(result.should_exit)
        self.assertEqual(self.node("one").owner, "alice")
        self.assertNotIn("ignored", self.vfs.root.children)
        self.assertIn(ERROR, [kind for kind, _ in result.events])


if __name__ == "__main__":
    unittest.main()
