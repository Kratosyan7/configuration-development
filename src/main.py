"""Эмулятор командной оболочки ОС. Этап 1: REPL.

Вариант №14. Графический интерфейс, разбор строки с раскрытием
переменных окружения, команды-заглушки ls и cd, команда exit.

Константа MAX_ARGS задаёт максимальное число аргументов для команд,
которые его ограничивают. Константа VAR_PATTERN описывает переменные
окружения в двух формах: $VAR и ${VAR}.
"""

import os
import re
import shlex
import tkinter as tk
from tkinter import scrolledtext

VFS_NAME = "VFS"
WINDOW_SIZE = "600x400"
PROMPT = "$ "

FONT_NAME = "Menlo"
FONT_SIZE = 10
BACKGROUND_COLOR = "black"
FOREGROUND_COLOR = "lime"

EXIT_COMMAND = "exit"
CD_COMMAND = "cd"
LS_COMMAND = "ls"
STUB_COMMANDS = (LS_COMMAND, CD_COMMAND)

MAX_ARGS = {CD_COMMAND: 1, EXIT_COMMAND: 0}

VAR_PATTERN = re.compile(r"\$(\w+)|\$\{(\w+)\}")

QUOTE_ERROR = "Ошибка разбора: незакрытая кавычка"
ARGS_ERROR = "Ошибка: неверные аргументы команды {name}"
UNKNOWN_ERROR = "Неизвестная команда: {name}"


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


class App(tk.Tk):
    """Окно эмулятора с общим текстовым полем ввода и вывода."""

    def __init__(self) -> None:
        """Создаёт окно и настраивает обработчики событий."""
        super().__init__()
        self.title(VFS_NAME)
        self.geometry(WINDOW_SIZE)

        self.output = scrolledtext.ScrolledText(
            self,
            bg=BACKGROUND_COLOR,
            fg=FOREGROUND_COLOR,
            insertbackground=FOREGROUND_COLOR,
            font=(FONT_NAME, FONT_SIZE),
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.bind("<Return>", self.on_enter)
        self._print_prompt()

    def _print_prompt(self) -> None:
        """Выводит приглашение ввода и переносит курсор в конец."""
        self.output.insert(tk.END, PROMPT)
        self.output.mark_set(tk.INSERT, tk.END)
        self.output.see(tk.END)

    def _print_line(self, text: str) -> None:
        """Выводит строку результата."""
        self.output.insert(tk.END, text + "\n")

    def _read_command(self) -> str:
        """Читает команду из текущей строки, отбрасывая приглашение."""
        line = self.output.get("insert linestart", "insert lineend")
        if not line.startswith(PROMPT):
            return ""
        return line[len(PROMPT):].strip()

    def on_enter(self, event: tk.Event) -> str:
        """Обрабатывает нажатие Enter и запускает введённую команду."""
        command = self._read_command()
        self.output.insert(tk.END, "\n")

        if command:
            self._execute(command)

        self._print_prompt()
        return "break"

    def _execute(self, line: str) -> None:
        """Разбирает и выполняет одну команду эмулятора."""
        try:
            parts = parse_line(line)
        except ValueError:
            self._print_line(QUOTE_ERROR)
            return

        if not parts:
            return

        name = parts[0]
        args = parts[1:]

        if has_invalid_args(name, args):
            self._print_line(ARGS_ERROR.format(name=name))
            return

        if name == EXIT_COMMAND:
            self.destroy()
        elif name in STUB_COMMANDS:
            self._print_line(format_stub(name, args))
        else:
            self._print_line(UNKNOWN_ERROR.format(name=name))


def main() -> None:
    """Точка входа приложения."""
    App().mainloop()


if __name__ == "__main__":
    main()
