"""Тесты движка: разбор строки, команды и стартовые скрипты."""

import os
import tempfile
import unittest
from pathlib import Path

from emulator import (
    ECHO,
    ERROR,
    OUTPUT,
    CommandError,
    execute_line,
    expand_vars,
    format_stub,
    has_invalid_args,
    parse_line,
    run_script,
)
from vfs import empty_vfs, load_vfs


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

    def test_vfs_info_rejects_arguments(self) -> None:
        """Команда vfs-info с аргументом не проходит проверку."""
        self.assertTrue(has_invalid_args("vfs-info", ["лишний"]))

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


class EmulatorTestCase(unittest.TestCase):
    """Готовит VFS из временной директории."""

    def prepare_vfs(self):
        """Создаёт источник VFS и загружает его в память."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name) / "demo"
        (source / "home").mkdir(parents=True)
        (source / "root.txt").write_text("корень\n", encoding="utf-8")
        return load_vfs(source)


class TestExecuteLine(EmulatorTestCase):
    """Проверяет выполнение отдельной команды."""

    def test_stub_returns_output(self) -> None:
        """Заглушка возвращает имя и аргументы."""
        result = execute_line(self.prepare_vfs(), "ls -l")
        self.assertEqual(result.output, "ls -l")

    def test_exit_requests_shutdown(self) -> None:
        """Команда exit запрашивает завершение работы."""
        self.assertTrue(execute_line(empty_vfs(), "exit").should_exit)

    def test_empty_line_does_nothing(self) -> None:
        """Пустая строка не вызывает ошибки."""
        self.assertEqual(execute_line(empty_vfs(), "   ").output, "")

    def test_unknown_command(self) -> None:
        """Неизвестная команда сообщает об ошибке."""
        with self.assertRaises(CommandError):
            execute_line(empty_vfs(), "pwd")

    def test_unclosed_quote(self) -> None:
        """Незакрытая кавычка сообщает об ошибке разбора."""
        with self.assertRaises(CommandError):
            execute_line(empty_vfs(), 'cd "unclosed')

    def test_too_many_arguments(self) -> None:
        """Лишние аргументы сообщают об ошибке."""
        with self.assertRaises(CommandError):
            execute_line(empty_vfs(), "cd /home /tmp")


class TestVfsInfo(EmulatorTestCase):
    """Проверяет служебную команду vfs-info."""

    def test_output_contains_name(self) -> None:
        """Ответ содержит имя загруженной VFS."""
        output = execute_line(self.prepare_vfs(), "vfs-info").output
        self.assertIn("demo", output)

    def test_output_contains_hash(self) -> None:
        """Ответ содержит хеш SHA-256."""
        output = execute_line(self.prepare_vfs(), "vfs-info").output
        self.assertIn("SHA-256", output)

    def test_output_contains_source(self) -> None:
        """Ответ содержит путь к источнику VFS."""
        vfs = self.prepare_vfs()
        output = execute_line(vfs, "vfs-info").output
        self.assertIn(str(vfs.source), output)

    def test_rejects_arguments(self) -> None:
        """Команда не принимает аргументов."""
        with self.assertRaises(CommandError):
            execute_line(empty_vfs(), "vfs-info лишний")

    def test_hash_is_stable_between_calls(self) -> None:
        """Повторный вызов даёт тот же хеш: VFS не изменяется."""
        vfs = self.prepare_vfs()
        first = execute_line(vfs, "vfs-info").output
        second = execute_line(vfs, "vfs-info").output
        self.assertEqual(first, second)


class TestScript(EmulatorTestCase):
    """Проверяет выполнение стартового скрипта."""

    def write_script(self, text: str) -> Path:
        """Записывает временный стартовый скрипт."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "startup.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def test_input_is_echoed(self) -> None:
        """Протокол содержит введённую строку."""
        result = run_script(empty_vfs(), self.write_script("ls\n"))
        self.assertIn(ECHO, [kind for kind, _ in result.events])

    def test_output_is_recorded(self) -> None:
        """Протокол содержит вывод команды."""
        result = run_script(empty_vfs(), self.write_script("ls -l\n"))
        self.assertEqual(result.events[-1], (OUTPUT, "ls -l"))

    def test_comments_and_blanks_skipped(self) -> None:
        """Комментарии и пустые строки пропускаются."""
        result = run_script(empty_vfs(), self.write_script("# текст\n\n"))
        self.assertEqual(result.events, [])

    def test_bad_line_is_skipped(self) -> None:
        """Ошибочная строка не останавливает выполнение."""
        script = self.write_script("pwd\nls конец\n")
        result = run_script(empty_vfs(), script)
        self.assertIn(ERROR, [kind for kind, _ in result.events])
        self.assertEqual(result.events[-1], (OUTPUT, "ls конец"))

    def test_error_mentions_line_number(self) -> None:
        """Сообщение об ошибке содержит номер строки."""
        result = run_script(empty_vfs(), self.write_script("ls\npwd\n"))
        errors = [text for kind, text in result.events if kind == ERROR]
        self.assertIn("2", errors[0])

    def test_exit_stops_script(self) -> None:
        """Команда exit прекращает выполнение скрипта."""
        result = run_script(empty_vfs(), self.write_script("exit\nls\n"))
        self.assertTrue(result.should_exit)
        self.assertNotIn(OUTPUT, [kind for kind, _ in result.events])

    def test_vfs_info_works_in_script(self) -> None:
        """Служебная команда доступна из стартового скрипта."""
        script = self.write_script("vfs-info\n")
        result = run_script(self.prepare_vfs(), script)
        self.assertIn("SHA-256", result.events[-1][1])

    def test_missing_script_reports_error(self) -> None:
        """Отсутствующий скрипт даёт сообщение об ошибке."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        result = run_script(empty_vfs(), Path(temp.name) / "нет.txt")
        self.assertEqual(result.events[0][0], ERROR)


if __name__ == "__main__":
    unittest.main()
