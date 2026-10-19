"""Основные команды варианта 14, работающие с VFS в памяти."""

from paths import node_at, require_directory, resolve
from vfs import Vfs, VfsError, VfsNode

SINGLE_OPERAND = 1
WC_ORDER = "lwmc"
WC_DEFAULT = "lwc"


def parse_options(args: list[str], allowed: str):
    """Разбирает короткие ключи, сочетания ключей и разделитель --."""
    flags, operands = set(), []
    stopped = False
    for arg in args:
        if arg == "--" and not stopped:
            stopped = True
        elif arg.startswith("-") and not stopped:
            if arg == "-" or not set(arg[1:]) <= set(allowed):
                raise VfsError(f"неизвестная опция: {arg}")
            flags.update(arg[1:])
        else:
            operands.append(arg)
    return flags, operands


def change_directory(vfs: Vfs, args: list[str]) -> str:
    """Меняет текущий каталог; без аргументов переходит в корень."""
    segments, node = resolve(vfs, args[0] if args else "/")
    require_directory(node)
    vfs.cwd = segments
    return ""


def list_entries(vfs: Vfs, path: str, hidden: bool):
    """Формирует пары имя/узел для одного операнда ls."""
    segments, node = resolve(vfs, path)
    if not node.is_dir:
        return [(path, node)]
    entries = [(name, child) for name, child in sorted(node.children.items())
               if hidden or not name.startswith(".")]
    if hidden:
        entries = [(".", node), ("..", node_at(vfs, segments[:-1]))] + entries
    return entries


def format_entry(name: str, node: VfsNode, long: bool) -> str:
    """Показывает тип, владельца, группу, байты и время изменения."""
    if not long:
        return name
    kind = "d" if node.is_dir else "-"
    return (f"{kind} {node.owner}:{node.group} {len(node.data)} "
            f"{node.modified_ns} {name}")


def list_directory(vfs: Vfs, args: list[str]) -> str:
    """Реализует ls с ключами -a, -l и несколькими путями."""
    flags, paths = parse_options(args, "al")
    output = []
    for path in paths or ["."]:
        entries = list_entries(vfs, path, "a" in flags)
        if len(paths) > SINGLE_OPERAND:
            output.append(f"{path}:")
        output.extend(format_entry(name, node, "l" in flags)
                      for name, node in entries)
    return "\n".join(output)


def count_file(node: VfsNode, flags: set[str]) -> dict[str, int]:
    """Считает LF, слова, символы UTF-8 и байты без изменения файла."""
    if node.is_dir:
        raise VfsError(f"это каталог: {node.name}")
    counts = {"l": node.data.count(b"\n"), "c": len(node.data)}
    if flags & {"w", "m"}:
        try:
            text = node.data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise VfsError(f"не UTF-8 текст: {node.name}") from error
        counts.update(w=len(text.split()), m=len(text))
    return counts


def format_counts(counts: dict[str, int], flags: set[str], name: str):
    """Выводит выбранные счётчики в устойчивом порядке и имя файла."""
    return " ".join([str(counts[key]) for key in WC_ORDER if key in flags]
                    + [name])


def word_count(vfs: Vfs, args: list[str]) -> str:
    """Реализует wc [-lwmc] ФАЙЛ... и итог для нескольких файлов."""
    flags, paths = parse_options(args, WC_ORDER)
    if not paths:
        raise VfsError("wc: укажите файл")
    flags = flags or set(WC_DEFAULT)
    totals = dict.fromkeys(WC_ORDER, 0)
    output = []
    for path in paths:
        _, node = resolve(vfs, path)
        counts = count_file(node, flags)
        output.append(format_counts(counts, flags, path))
        for key in flags:
            totals[key] += counts[key]
    if len(paths) > SINGLE_OPERAND:
        output.append(format_counts(totals, flags, "итого"))
    return "\n".join(output)
