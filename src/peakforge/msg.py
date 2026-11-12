"""Translatable messages from the back end (core / project) without a GUI dependency.

A ``Msg`` is a plain ``str`` (the English text used by the CLI, MCP, logs and exports) that also carries a
``code`` and pre-formatted ``args``, so the GUI can show it in the user's language (gui/i18n.tr_msg).
Values in ``args`` may themselves be Msg objects or lists of them (translated recursively).
"""
from __future__ import annotations


class Msg(str):
    code: str
    args: dict

    def __new__(cls, text: str, code: str, **args: object) -> "Msg":
        o = super().__new__(cls, text)
        o.code, o.args = code, args
        return o

    def __reduce__(self):            # keep code/args through copy / pickle
        return (_rebuild, (str(self), self.code, self.args))


def _rebuild(text: str, code: str, args: dict) -> Msg:
    return Msg(text, code, **args)


def exc_msg(e: BaseException) -> str:
    """The message of an exception, keeping a Msg passed as its first argument."""
    return e.args[0] if e.args and isinstance(e.args[0], str) else str(e)
