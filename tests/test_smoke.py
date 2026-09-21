"""Тесты разбора команд и проверки аргументов."""

import os
import unittest

from main import expand_vars, format_stub, has_invalid_args, parse_line


class TestParser(unittest.TestCase):
    """Проверяет разбор командной строки."""

    def test_simple_command(self) -> None:
        """Разбирает простую команду."""
        self.assertEqual(parse_line("ls"), ["ls"])

    def test_command_with_argument(self) -> None:
        """Разбирает команду с аргументом."""
        self.assertEqual(parse_line("ls /home"), ["ls", "/home"])

    def test_quoted_argument(self) -> None:
        """Разбирает аргумент в кавычках."""
        self.assertEqual(
            parse_line('cd "my folder"'),
            ["cd", "my folder"],
        )

    def test_empty_line(self) -> None:
        """Пустая строка даёт пустой список токенов."""
        self.assertEqual(parse_line("   "), [])

    def test_unclosed_quote(self) -> None:
        """Выдаёт ошибку при незакрытой кавычке."""
        with self.assertRaises(ValueError):
            parse_line('cd "unclosed')


class TestEnvExpansion(unittest.TestCase):
    """Проверяет раскрытие переменных окружения."""

    def prepare_environment(self) -> None:
        """Готовит тестовые переменные окружения."""
        os.environ["VFS_TEST_VAR"] = "/tmp/vfs"
        os.environ["VFS_TEST_SPACED"] = "/tmp/my vfs"
        os.environ.pop("VFS_TEST_MISSING", None)

    def test_simple_variable(self) -> None:
        """Раскрывает переменную вида $VAR."""
        self.prepare_environment()
        self.assertEqual(
            parse_line("cd $VFS_TEST_VAR"),
            ["cd", "/tmp/vfs"],
        )

    def test_braced_variable(self) -> None:
        """Раскрывает переменную вида ${VAR}."""
        self.prepare_environment()
        self.assertEqual(
            parse_line("cd ${VFS_TEST_VAR}"),
            ["cd", "/tmp/vfs"],
        )

    def test_value_with_spaces_stays_one_argument(self) -> None:
        """Значение с пробелами остаётся одним аргументом."""
        self.prepare_environment()
        self.assertEqual(
            parse_line("cd $VFS_TEST_SPACED"),
            ["cd", "/tmp/my vfs"],
        )

    def test_variable_inside_path(self) -> None:
        """Раскрывает переменную внутри пути."""
        self.prepare_environment()
        self.assertEqual(
            expand_vars("${VFS_TEST_VAR}/docs"),
            "/tmp/vfs/docs",
        )

    def test_missing_variable_becomes_empty(self) -> None:
        """Неизвестная переменная раскрывается в пустую строку."""
        self.prepare_environment()
        self.assertEqual(expand_vars("$VFS_TEST_MISSING"), "")

    def test_text_without_variables_unchanged(self) -> None:
        """Текст без переменных не меняется."""
        self.prepare_environment()
        self.assertEqual(expand_vars("/home/user"), "/home/user")


class TestArgumentValidation(unittest.TestCase):
    """Проверяет контроль числа аргументов команд."""

    def test_cd_accepts_one_argument(self) -> None:
        """Команда cd допускает один аргумент."""
        self.assertFalse(has_invalid_args("cd", ["/home"]))

    def test_cd_rejects_two_arguments(self) -> None:
        """Команда cd отвергает два аргумента."""
        self.assertTrue(has_invalid_args("cd", ["/home", "/tmp"]))

    def test_exit_accepts_no_arguments(self) -> None:
        """Команда exit без аргументов проходит проверку."""
        self.assertFalse(has_invalid_args("exit", []))

    def test_exit_rejects_arguments(self) -> None:
        """Команда exit с аргументом не проходит проверку."""
        self.assertTrue(has_invalid_args("exit", ["now"]))

    def test_ls_accepts_any_arguments(self) -> None:
        """Команда ls не ограничена по числу аргументов."""
        self.assertFalse(has_invalid_args("ls", ["-l", "-a", "/tmp"]))


class TestStubOutput(unittest.TestCase):
    """Проверяет вывод команд-заглушек."""

    def test_name_without_arguments(self) -> None:
        """Заглушка без аргументов выводит только своё имя."""
        self.assertEqual(format_stub("cd", []), "cd")

    def test_name_with_arguments(self) -> None:
        """Заглушка выводит имя и аргументы через пробел."""
        self.assertEqual(
            format_stub("ls", ["-l", "/home"]),
            "ls -l /home",
        )


if __name__ == "__main__":
    unittest.main()
