"""Движок эмулятора: разбор строки, команды и стартовые скрипты.

Этапы 1–5 варианта №14. Модуль не зависит от графического
интерфейса, поэтому полностью покрывается тестами.

Начиная с Этапа 3 у команд появляется состояние, поэтому execute_line
и run_script принимают загруженную VFS первым аргументом.

Константа MAX_ARGS задаёт максимальное число аргументов для команд,
которые его ограничивают. Константа VAR_PATTERN описывает переменные
окружения в двух формах: $VAR и ${VAR}. Константы ECHO, OUTPUT и ERROR
помечают вид записи в протоколе выполнения скрипта.
"""

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from commands import change_directory, list_directory, word_count
from mutations import chown, touch
from vfs import Vfs, VfsError, describe_source, vfs_hash

PROMPT = "$ "
COMMENT_PREFIX = "#"

EXIT_COMMAND = "exit"
CD_COMMAND = "cd"
LS_COMMAND = "ls"
VFS_INFO_COMMAND = "vfs-info"
CLEAR_COMMAND = "clear"
COMMANDS = {LS_COMMAND: list_directory, CD_COMMAND: change_directory,
            "wc": word_count, "touch": touch, "chown": chown}

MAX_ARGS = {CD_COMMAND: 1, EXIT_COMMAND: 0, VFS_INFO_COMMAND: 0,
            CLEAR_COMMAND: 0}

VAR_PATTERN = re.compile(r"\$(\w+)|\$\{(\w+)\}")

QUOTE_ERROR = "незакрытая кавычка"
ARGS_ERROR = "неверные аргументы команды {name}"
UNKNOWN_ERROR = "неизвестная команда: {name}"
SCRIPT_ERROR = "ошибка в строке {number}: {reason}"
READ_ERROR = "не удалось прочитать стартовый скрипт: {reason}"

VFS_INFO_NAME = "имя VFS: {name}"
VFS_INFO_SOURCE = "источник: {source}"
VFS_INFO_HASH = "SHA-256: {digest}"

ECHO = "echo"
OUTPUT = "output"
ERROR = "error"
CLEAR = "clear"


class CommandError(Exception):
    """Ошибка разбора или выполнения команды эмулятора."""


@dataclass
class CommandResult:
    """Результат выполнения одной команды."""

    output: str = ""
    should_exit: bool = False
    should_clear: bool = False


@dataclass
class ScriptResult:
    """Протокол выполнения стартового скрипта."""

    events: list[tuple[str, str]] = field(default_factory=list)
    should_exit: bool = False


def expand_vars(token: str) -> str:
    """Раскрывает $VAR и ${VAR} значениями переменных окружения ОС.

    Неизвестная переменная раскрывается в пустую строку, как в bash.
    """

    def replace(match: re.Match) -> str:
        """Возвращает значение переменной из найденного совпадения."""
        name = match.group(1) or match.group(2)
        return os.environ.get(name, "")

    return VAR_PATTERN.sub(replace, token)


def parse_line(line: str) -> list[str]:
    """Разбирает строку на команду и аргументы с раскрытием переменных.

    Раскрытие выполняется после разбиения на токены, поэтому значение
    с пробелами остаётся одним аргументом. Вызывает ValueError, если
    кавычка не закрыта.
    """
    return [expand_vars(token) for token in shlex.split(line)]


def has_invalid_args(name: str, args: list[str]) -> bool:
    """Проверяет, превышено ли допустимое число аргументов команды."""
    return len(args) > MAX_ARGS.get(name, len(args))


def format_stub(name: str, args: list[str]) -> str:
    """Формирует вывод команды-заглушки: имя и её аргументы."""
    return " ".join([name, *args])


def format_vfs_info(vfs: Vfs) -> str:
    """Формирует ответ служебной команды vfs-info."""
    return "\n".join(
        [
            VFS_INFO_NAME.format(name=vfs.name),
            VFS_INFO_SOURCE.format(source=describe_source(vfs)),
            VFS_INFO_HASH.format(digest=vfs_hash(vfs)),
        ]
    )


def execute_line(vfs: Vfs, line: str) -> CommandResult:
    """Выполняет одну строку эмулятора.

    Вызывает CommandError при ошибке разбора или выполнения.
    """
    try:
        parts = parse_line(line)
    except ValueError as error:
        raise CommandError(QUOTE_ERROR) from error

    if not parts:
        return CommandResult()

    name = parts[0]
    args = parts[1:]

    if has_invalid_args(name, args):
        raise CommandError(ARGS_ERROR.format(name=name))

    if name == EXIT_COMMAND:
        return CommandResult(should_exit=True)
    if name == VFS_INFO_COMMAND:
        return CommandResult(output=format_vfs_info(vfs))
    if name == CLEAR_COMMAND:
        return CommandResult(should_clear=True)
    if name in COMMANDS:
        return run_handler(vfs, name, args)
    raise CommandError(UNKNOWN_ERROR.format(name=name))


def run_handler(vfs: Vfs, name: str, args: list[str]) -> CommandResult:
    """Переводит ошибки файловых команд в общий формат движка."""
    try:
        return CommandResult(output=COMMANDS[name](vfs, args))
    except VfsError as error:
        raise CommandError(f"{name}: {error}") from error


def run_script(vfs: Vfs, path: Path) -> ScriptResult:
    """Выполняет стартовый скрипт, имитируя диалог с пользователем.

    В протокол попадает и ввод, и вывод. Ошибочные строки пропускаются:
    сообщение с номером строки добавляется в протокол, выполнение
    продолжается со следующей команды.
    """
    result = ScriptResult()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        result.events.append((ERROR, READ_ERROR.format(reason=error)))
        return result

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            continue
        result.events.append((ECHO, PROMPT + line))
        if run_script_line(vfs, line, number, result):
            result.should_exit = True
            return result
    return result


def run_script_line(
    vfs: Vfs,
    line: str,
    number: int,
    result: ScriptResult,
) -> bool:
    """Выполняет одну строку скрипта и дописывает протокол.

    Возвращает True, если запрошено завершение работы эмулятора.
    """
    try:
        command = execute_line(vfs, line)
    except CommandError as error:
        reason = SCRIPT_ERROR.format(number=number, reason=error)
        result.events.append((ERROR, reason))
        return False

    if command.should_clear:
        result.events.append((CLEAR, ""))
    if command.output:
        result.events.append((OUTPUT, command.output))
    return command.should_exit
