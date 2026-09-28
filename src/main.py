"""Эмулятор командной оболочки ОС: графический интерфейс.

Этап 3 варианта №14. Точка входа читает конфигурацию, загружает VFS
из директории на диске, печатает отладочный вывод всех заданных
параметров, выполняет стартовый скрипт и переходит в интерактивный
режим.

Константа ERROR_COLOR выделяет сообщения об ошибках, ECHO_COLOR
выделяет строки, которые скрипт подставляет вместо ввода пользователя.
"""

import sys
import tkinter as tk
from tkinter import scrolledtext

from config import Config, ConfigError, describe, load_config
from emulator import (
    ECHO,
    ERROR,
    PROMPT,
    CommandError,
    execute_line,
    run_script,
)
from vfs import Vfs, VfsError, empty_vfs, load_vfs

WINDOW_SIZE = "700x450"
TITLE_TEMPLATE = "Эмулятор: {name}"

FONT_NAME = "Menlo"
FONT_SIZE = 11
BACKGROUND_COLOR = "black"
FOREGROUND_COLOR = "lime"
ERROR_COLOR = "orange red"
ECHO_COLOR = "deep sky blue"

ERROR_TAG = "error"
ECHO_TAG = "echo"

ERROR_PREFIX = "Ошибка: "
CONFIG_ERROR = "Ошибка конфигурации: {reason}"
VFS_ERROR = "Ошибка загрузки VFS: {reason}"
VFS_LOADED = "VFS «{name}» загружена в память."
VFS_ABSENT = "VFS не задана, используется пустая."

EXIT_FAILURE = 1
EXIT_SUCCESS = 0


class App(tk.Tk):
    """Окно эмулятора с общим текстовым полем ввода и вывода."""

    def __init__(self, vfs: Vfs, report: list[str]) -> None:
        """Создаёт окно и печатает отладочный вывод параметров."""
        super().__init__()
        self.vfs = vfs
        self.title(TITLE_TEMPLATE.format(name=vfs.name))
        self.geometry(WINDOW_SIZE)

        self.output = scrolledtext.ScrolledText(
            self,
            bg=BACKGROUND_COLOR,
            fg=FOREGROUND_COLOR,
            insertbackground=FOREGROUND_COLOR,
            font=(FONT_NAME, FONT_SIZE),
        )
        self.output.tag_config(ERROR_TAG, foreground=ERROR_COLOR)
        self.output.tag_config(ECHO_TAG, foreground=ECHO_COLOR)
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.bind("<Return>", self.on_enter)

        for line in report:
            self.print_line(line)
        self.print_line("")

    def print_line(self, text: str, tag: str | None = None) -> None:
        """Выводит строку, при необходимости выделяя её цветом."""
        tags = (tag,) if tag else ()
        self.output.insert(tk.END, text + "\n", tags)

    def print_prompt(self) -> None:
        """Выводит приглашение ввода и переносит курсор в конец."""
        self.output.insert(tk.END, PROMPT)
        self.output.mark_set(tk.INSERT, tk.END)
        self.output.see(tk.END)

    def read_command(self) -> str:
        """Читает команду из текущей строки, отбрасывая приглашение."""
        line = self.output.get("insert linestart", "insert lineend")
        if not line.startswith(PROMPT):
            return ""
        return line[len(PROMPT):].strip()

    def on_enter(self, event: tk.Event) -> str:
        """Обрабатывает нажатие Enter и запускает введённую команду."""
        command = self.read_command()
        self.output.insert(tk.END, "\n")

        if command and self.run_command(command):
            return "break"

        self.print_prompt()
        return "break"

    def run_command(self, line: str) -> bool:
        """Выполняет команду. Возвращает True при завершении работы."""
        try:
            result = execute_line(self.vfs, line)
        except CommandError as error:
            self.print_line(ERROR_PREFIX + str(error), ERROR_TAG)
            return False

        if result.output:
            self.print_line(result.output)
        if result.should_exit:
            self.destroy()
        return result.should_exit

    def replay(self, events: list[tuple[str, str]]) -> None:
        """Отображает протокол выполнения стартового скрипта."""
        for kind, text in events:
            if kind == ECHO:
                self.print_line(text, ECHO_TAG)
            elif kind == ERROR:
                self.print_line(ERROR_PREFIX + text, ERROR_TAG)
            else:
                self.print_line(text)


def prepare_vfs(config: Config, report: list[str]) -> Vfs:
    """Загружает VFS, дописывая сообщения в отладочный вывод."""
    if config.vfs_path is None:
        report.append(VFS_ABSENT)
        return empty_vfs()

    try:
        vfs = load_vfs(config.vfs_path)
    except VfsError as error:
        report.append(VFS_ERROR.format(reason=error))
        return empty_vfs()

    report.append(VFS_LOADED.format(name=vfs.name))
    return vfs


def mirror(events: list[tuple[str, str]]) -> None:
    """Дублирует протокол скрипта в стандартный вывод."""
    for kind, text in events:
        prefix = ERROR_PREFIX if kind == ERROR else ""
        print(prefix + text)


def main(argv: list[str] | None = None) -> int:
    """Точка входа приложения."""
    try:
        config = load_config(argv)
    except ConfigError as error:
        print(CONFIG_ERROR.format(reason=error), file=sys.stderr)
        return EXIT_FAILURE

    report = describe(config)
    vfs = prepare_vfs(config, report)
    print("\n".join(report))

    app = App(vfs, report)
    if config.startup_path is not None:
        result = run_script(vfs, config.startup_path)
        mirror(result.events)
        app.replay(result.events)
        if result.should_exit:
            app.destroy()
            return EXIT_SUCCESS

    app.print_prompt()
    app.mainloop()
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
