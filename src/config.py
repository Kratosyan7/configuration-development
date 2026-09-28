"""Конфигурация эмулятора: параметры командной строки и файл TOML.

Этап 2 варианта №14. Значения из командной строки имеют приоритет над
значениями из конфигурационного файла.

Константа KNOWN_KEYS перечисляет ключи, допустимые в файле TOML.
Константы SOURCE_* используются в отладочном выводе, чтобы показать,
откуда взято каждое значение.
"""

import argparse
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DESCRIPTION = "Эмулятор командной оболочки ОС"

VFS_KEY = "vfs_path"
STARTUP_KEY = "startup_path"
KNOWN_KEYS = (VFS_KEY, STARTUP_KEY)

SOURCE_CLI = "командная строка"
SOURCE_FILE = "конфигурационный файл"
SOURCE_NONE = "не задан"

NOT_SET = "не задан"


class ConfigError(Exception):
    """Ошибка чтения или разбора конфигурационного файла."""


@dataclass
class Config:
    """Параметры запуска эмулятора и источник каждого значения."""

    vfs_path: Path | None = None
    startup_path: Path | None = None
    config_path: Path | None = None
    sources: dict[str, str] = field(default_factory=dict)


def build_parser() -> argparse.ArgumentParser:
    """Описывает поддерживаемые параметры командной строки."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--vfs",
        type=Path,
        help="путь к физическому расположению VFS",
    )
    parser.add_argument(
        "--startup",
        type=Path,
        help="путь к стартовому скрипту эмулятора",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="путь к конфигурационному файлу TOML",
    )
    return parser


def read_config_file(path: Path) -> dict[str, str]:
    """Читает конфигурационный файл TOML.

    Вызывает ConfigError, если файл недоступен, повреждён или содержит
    неизвестные ключи.
    """
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as error:
        raise ConfigError(f"не удалось прочитать {path}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"ошибка разбора {path}: {error}") from error

    unknown = sorted(set(data) - set(KNOWN_KEYS))
    if unknown:
        keys = ", ".join(unknown)
        raise ConfigError(f"неизвестные ключи в {path}: {keys}")
    return data


def pick_value(
    cli_value: Path | None,
    file_value: str | None,
) -> tuple[Path | None, str]:
    """Выбирает значение параметра: командная строка важнее файла."""
    if cli_value is not None:
        return Path(cli_value), SOURCE_CLI
    if file_value is not None:
        return Path(file_value), SOURCE_FILE
    return None, SOURCE_NONE


def load_config(argv: list[str] | None = None) -> Config:
    """Собирает конфигурацию из командной строки и файла TOML."""
    args = build_parser().parse_args(argv)
    data = read_config_file(args.config) if args.config else {}

    vfs_path, vfs_source = pick_value(args.vfs, data.get(VFS_KEY))
    startup_path, startup_source = pick_value(
        args.startup,
        data.get(STARTUP_KEY),
    )
    return Config(
        vfs_path=vfs_path,
        startup_path=startup_path,
        config_path=args.config,
        sources={VFS_KEY: vfs_source, STARTUP_KEY: startup_source},
    )


def show_path(value: Path | None) -> str:
    """Представляет необязательный путь для отладочного вывода."""
    return str(value) if value is not None else NOT_SET


def describe(config: Config) -> list[str]:
    """Формирует отладочный вывод всех заданных параметров."""
    vfs_source = config.sources.get(VFS_KEY, SOURCE_NONE)
    startup_source = config.sources.get(STARTUP_KEY, SOURCE_NONE)
    return [
        "Параметры запуска:",
        f"  конфигурационный файл: {show_path(config.config_path)}",
        f"  путь к VFS: {show_path(config.vfs_path)}"
        f" [{vfs_source}]",
        f"  стартовый скрипт: {show_path(config.startup_path)}"
        f" [{startup_source}]",
    ]
