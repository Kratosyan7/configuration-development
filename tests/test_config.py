"""Тесты конфигурации: параметры командной строки и файл TOML."""

import tempfile
import unittest
from pathlib import Path

from config import (
    SOURCE_CLI,
    SOURCE_FILE,
    SOURCE_NONE,
    STARTUP_KEY,
    VFS_KEY,
    ConfigError,
    describe,
    load_config,
    read_config_file,
)


class ConfigTestCase(unittest.TestCase):
    """Общая подготовка временного каталога для конфигураций."""

    def prepare_directory(self) -> Path:
        """Создаёт временный каталог на время одного теста."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def write_config(self, name: str, text: str) -> Path:
        """Записывает временный конфигурационный файл."""
        path = self.prepare_directory() / name
        path.write_text(text, encoding="utf-8")
        return path


class TestCommandLine(ConfigTestCase):
    """Проверяет разбор параметров командной строки."""

    def test_no_arguments(self) -> None:
        """Без параметров все пути остаются незаданными."""
        config = load_config([])
        self.assertIsNone(config.vfs_path)
        self.assertIsNone(config.startup_path)
        self.assertIsNone(config.config_path)

    def test_source_is_none_without_arguments(self) -> None:
        """Источник значения без параметров помечен как незаданный."""
        config = load_config([])
        self.assertEqual(config.sources[VFS_KEY], SOURCE_NONE)

    def test_all_three_arguments(self) -> None:
        """Читает все три параметра командной строки."""
        path = self.write_config("empty.toml", "")
        config = load_config(
            ["--vfs", "/a", "--startup", "/b", "--config", str(path)]
        )
        self.assertEqual(config.vfs_path, Path("/a"))
        self.assertEqual(config.startup_path, Path("/b"))
        self.assertEqual(config.config_path, path)

    def test_source_is_command_line(self) -> None:
        """Источник значения из строки помечен правильно."""
        config = load_config(["--vfs", "/a"])
        self.assertEqual(config.sources[VFS_KEY], SOURCE_CLI)


class TestConfigFile(ConfigTestCase):
    """Проверяет чтение конфигурационного файла TOML."""

    def test_values_from_file(self) -> None:
        """Берёт значения из файла, если в строке их нет."""
        path = self.write_config(
            "ok.toml",
            'vfs_path = "/from/file"\nstartup_path = "/script"\n',
        )
        config = load_config(["--config", str(path)])
        self.assertEqual(config.vfs_path, Path("/from/file"))
        self.assertEqual(config.startup_path, Path("/script"))

    def test_source_is_config_file(self) -> None:
        """Источник значения из файла помечен правильно."""
        path = self.write_config("ok.toml", 'vfs_path = "/from/file"\n')
        config = load_config(["--config", str(path)])
        self.assertEqual(config.sources[VFS_KEY], SOURCE_FILE)

    def test_missing_file(self) -> None:
        """Сообщает об ошибке, если файла не существует."""
        path = self.prepare_directory() / "нет.toml"
        with self.assertRaises(ConfigError):
            read_config_file(path)

    def test_broken_toml(self) -> None:
        """Сообщает об ошибке разбора повреждённого файла."""
        path = self.write_config("broken.toml", 'vfs_path = "/незакрыт\n')
        with self.assertRaises(ConfigError):
            read_config_file(path)

    def test_unknown_key(self) -> None:
        """Сообщает о неизвестном ключе в конфигурации."""
        path = self.write_config("bad.toml", 'colour = "green"\n')
        with self.assertRaises(ConfigError):
            read_config_file(path)

    def test_empty_file_is_valid(self) -> None:
        """Пустой конфигурационный файл считается корректным."""
        path = self.write_config("empty.toml", "")
        self.assertEqual(read_config_file(path), {})


class TestPriority(ConfigTestCase):
    """Проверяет приоритет командной строки над файлом."""

    def test_command_line_wins(self) -> None:
        """Значение из командной строки важнее значения из файла."""
        path = self.write_config("both.toml", 'vfs_path = "/from/file"\n')
        config = load_config(["--config", str(path), "--vfs", "/from/cli"])
        self.assertEqual(config.vfs_path, Path("/from/cli"))
        self.assertEqual(config.sources[VFS_KEY], SOURCE_CLI)

    def test_file_used_when_argument_absent(self) -> None:
        """Файл используется, если параметра в строке нет."""
        path = self.write_config(
            "both.toml",
            'vfs_path = "/from/file"\nstartup_path = "/from/file"\n',
        )
        config = load_config(["--config", str(path), "--vfs", "/from/cli"])
        self.assertEqual(config.startup_path, Path("/from/file"))
        self.assertEqual(config.sources[STARTUP_KEY], SOURCE_FILE)


class TestDescribe(ConfigTestCase):
    """Проверяет отладочный вывод заданных параметров."""

    def test_report_mentions_every_parameter(self) -> None:
        """Отладочный вывод содержит все три параметра."""
        report = "\n".join(describe(load_config([])))
        self.assertIn("конфигурационный файл", report)
        self.assertIn("путь к VFS", report)
        self.assertIn("стартовый скрипт", report)

    def test_report_shows_source(self) -> None:
        """Отладочный вывод показывает источник значения."""
        report = "\n".join(describe(load_config(["--vfs", "/a"])))
        self.assertIn(SOURCE_CLI, report)


if __name__ == "__main__":
    unittest.main()
