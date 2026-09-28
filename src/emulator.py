"""Движок эмулятора: разбор строки, команды и стартовые скрипты.

Этапы 1 и 2 варианта №14. Модуль не зависит от графического интерфейса,
поэтому полностью покрывается тестами.

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

PROMPT = "$ "
COMMENT_PREFIX = "#"

EXIT_COMMAND = "exit"
CD_COMMAND = "cd"
LS_COMMAND = "ls"
STUB_COMMANDS = (LS_COMMAND, CD_COMMAND)

MAX_ARGS = {CD_COMMAND: 1, EXIT_COMMAND: 0}

VAR_PATTERN = re.compile(r"\$(\w+)|\$\{(\w+)\}")

QUOTE_ERROR = "незакрытая кавычка"
ARGS_ERROR = "неверные аргументы команды {name}"
UNKNOWN_ERROR = "неизвестная команда: {name}"
SCRIPT_ERROR = "ошибка в строке {number}: {reason}"
READ_ERROR = "не удалось прочитать стартовый скрипт: {reason}"

ECHO = "echo"
OUTPUT = "output"
ERROR = "error"


class CommandError(Exception):
    """Ошибка разбора или выполнения команды эмулятора."""


@dataclass
class CommandResult:
    """Результат выполнения одной команды."""

    output: str = ""
    should_exit: bool = False


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


def execute_line(line: str) -> CommandResult:
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
    if name in STUB_COMMANDS:
        return CommandResult(output=format_stub(name, args))
    raise CommandError(UNKNOWN_ERROR.format(name=name))


def run_script(path: Path) -> ScriptResult:
    """Выполняет стартовый скрипт, имитируя диалог с пользователем.

    В протокол попадает и ввод, и вывод. Ошибочные строки пропускаются:
    сообщение с номером строки добавляется в протокол, выполнение
    продолжается со следующей команды.
    """
    result = ScriptResult()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        result.events.append((ERROR, READ_ERROR.format(reason=error)))
        return result

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            continue
        result.events.append((ECHO, PROMPT + line))
        if run_script_line(line, number, result):
            result.should_exit = True
            return result
    return result


def run_script_line(line: str, number: int, result: ScriptResult) -> bool:
    """Выполняет одну строку скрипта и дописывает протокол.

    Возвращает True, если запрошено завершение работы эмулятора.
    """
    try:
        command = execute_line(line)
    except CommandError as error:
        reason = SCRIPT_ERROR.format(number=number, reason=error)
        result.events.append((ERROR, reason))
        return False

    if command.output:
        result.events.append((OUTPUT, command.output))
    return command.should_exit
