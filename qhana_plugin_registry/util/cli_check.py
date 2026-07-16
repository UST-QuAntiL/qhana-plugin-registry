from inspect import stack


def is_cli() -> bool:
    """Heuristically determine whether the app was called from a CLI entry point.

    This function checks the call stack to determine whether the current context
    is part of a CLI tool call.

    Returns:
        bool: True if the context matches CLI calls
    """
    current_stack = stack()

    to_find = [
        ("invoke", "/click/core.py"),
        ("resolve_command", "/click/core.py"),
        ("get_command", "/flask/cli.py"),
        ("load_app", "/flask/cli.py"),
        ("locate_app", "/flask/cli.py"),
        ("find_best_app", "/flask/cli.py"),
    ]

    for frame in current_stack:
        if not to_find:
            break
        if frame.function == to_find[-1][0] and frame.filename.endswith(to_find[-1][1]):
            to_find.pop()

    return not bool(to_find)
