"""Run slow work (fits, diagnostics, exports) off the UI thread."""
from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class Task(QRunnable):
    def __init__(self, fn, *args, **kw):
        super().__init__()
        self.fn, self.args, self.kw = fn, args, kw
        self.signals = _Signals()

    def run(self):
        try:
            r = self.fn(*self.args, **self.kw)
        except Exception as e:      # noqa: BLE001
            self.signals.failed.emit(f"{e}\n{traceback.format_exc(limit=3)}")
            return
        self.signals.done.emit(r)


_alive: set = set()      # keep Python references until the task has reported back


def submit(fn, *args, on_done=None, on_fail=None, **kw) -> Task:
    t = Task(fn, *args, **kw)
    t.setAutoDelete(False)
    _alive.add(t)
    t.signals.done.connect(lambda _r: _alive.discard(t))
    t.signals.failed.connect(lambda _m: _alive.discard(t))
    if on_done:
        t.signals.done.connect(on_done)
    if on_fail:
        t.signals.failed.connect(on_fail)
    QThreadPool.globalInstance().start(t)
    return t
