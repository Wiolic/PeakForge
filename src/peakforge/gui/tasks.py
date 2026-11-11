"""Background tasks for the GUI: run_task (QThread + progress + cancel).

Thread rules are in peakforge/tasks.py: the task function never touches widgets or the Project; inputs are
prepared in the UI thread before run_task and the result is written back in on_done (UI thread).
Cancelling takes effect at progress() / check() calls (between steps and at every residual evaluation).

Lifecycle (all in the UI thread):
  worker done / failed / cancelled -> _Relay (queued connection) -> finish(): leave _ACTIVE, refresh the status
  bar, th.quit(), re-enable the button.
  thread finished -> _Relay.cleanup (queued): th.wait(), then leave _RUNNING (the last reference to the QThread).
  Never connect `finished` to a lambda: it would run in the worker thread and the QThread could be destroyed
  inside its own finished signal -> crash.
"""
from __future__ import annotations

import atexit
import time
import traceback

import shiboken6
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from ..logs import log
from ..tasks import Cancelled, TaskHandle
from .i18n import tr

ERRORS: list[str] = []       # messages of failed tasks (the tests read this)
QUIET = {"v": False}         # tests: do not show dialogs


class _Worker(QObject):
    done = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progress = Signal(float, str)

    def __init__(self, fn, handle, with_progress):
        super().__init__()
        self.fn, self.handle, self.wp = fn, handle, with_progress

    def run(self):
        try:
            r = self.fn(self.handle) if self.wp else self.fn()
            # boxed in a tuple: a bare None must not travel through a cross-thread Signal(object)
            # (CPython 3.11 crashed with "none_dealloc" on Ubuntu CI in XAFSmith)
            self.done.emit((r,))
        except Cancelled:
            self.cancelled.emit()
        except Exception as ex:          # noqa: BLE001 — reported to the UI thread
            log.warning("background task failed", exc_info=True)
            self.failed.emit(f"{type(ex).__name__}: {ex}\n\n{traceback.format_exc()}")


class _Relay(QObject):
    """Receives the worker's signals in the UI thread (callbacks build widgets)."""

    def __init__(self, ok, bad, prog, cancelled, cleanup):
        super().__init__()
        self._ok, self._bad, self._prog, self._cancelled, self._cleanup = ok, bad, prog, cancelled, cleanup

    @Slot(object)
    def ok(self, boxed):
        self._ok(boxed[0])

    @Slot(str)
    def bad(self, m):
        self._bad(m)

    @Slot(float, str)
    def prog(self, f, n):
        self._prog(f, n)

    @Slot()
    def cancelled(self):
        self._cancelled()

    @Slot()
    def cleanup(self):
        self._cleanup()


_RUNNING: list = []     # (thread, worker, relay, handle): removed only after the thread has really ended
_ACTIVE: list = []      # jobs in the UI thread that have not reported yet
_BUTTONS: dict = {}     # id(button) -> number of running tasks that disabled it


def active() -> bool:
    """True while a background task has not reported back yet."""
    return bool(_ACTIVE)


def _alive(obj) -> bool:
    return obj is not None and shiboken6.isValid(obj)


def _show_status(status) -> None:
    """Status bar for all active jobs: none -> hidden; one -> progress + cancel; several -> a count."""
    if status is None:
        return
    if not _ACTIVE:
        status(False)
        return
    if len(_ACTIVE) == 1:
        j = _ACTIVE[0]
        if j["handle"].cancelled:
            status(True, tr("task_cancelling"), None, None)
            return
        status(True, j["text"] + (f" {j['ptext']}" if j["ptext"] else ""), j["frac"],
               j["cancel"] if j["cancellable"] else None)
        return
    live = [j for j in _ACTIVE if j["cancellable"] and not j["handle"].cancelled]

    def cancel_all():
        for j in live:
            j["handle"].cancel()
        _show_status(status)
    status(True, tr("tasks_running", n=len(_ACTIVE)), None, cancel_all if live else None)


def run_task(parent, fn, on_done, busy_text=None, button_=None, progress=False, on_error=None,
             cancellable=True, on_cancel=None) -> TaskHandle:
    """Run fn in a background thread; call on_done(result) in the UI thread when it finishes.
    progress=True: fn receives the TaskHandle (task.progress(f, text) / task.check are the cancel points); the
    status bar then offers Cancel; a cancelled task calls on_cancel() (if any) and never on_done.
    Errors go to on_error(msg) or to the window's fail()."""
    win = parent.window() if hasattr(parent, "window") else parent
    status = getattr(win, "busy", None)
    th = QThread()
    wk = None
    handle = TaskHandle(lambda f, n: wk.progress.emit(float(f), str(n)))
    job = dict(handle=handle, text=busy_text or tr("running"), frac=None, ptext="",
               cancellable=bool(cancellable and progress))
    job["cancel"] = lambda: (handle.cancel(), _show_status(status))
    wk = _Worker(fn, handle, progress)
    wk.moveToThread(th)
    if button_ is not None:          # several tasks may share a button: re-enable after the last one
        _BUTTONS[id(button_)] = _BUTTONS.get(id(button_), 0) + 1
        button_.setEnabled(False)
    _ACTIVE.append(job)
    _show_status(status)
    QApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)
    state = {"finished": False}

    def finish():
        if state["finished"]:
            return
        state["finished"] = True
        if job in _ACTIVE:
            _ACTIVE.remove(job)
        _show_status(status)
        th.quit()
        QApplication.restoreOverrideCursor()
        if button_ is not None:
            left = _BUTTONS.get(id(button_), 1) - 1
            if left > 0:
                _BUTTONS[id(button_)] = left
            else:
                _BUTTONS.pop(id(button_), None)
                if _alive(button_):
                    button_.setEnabled(True)

    def call(cb, *a):
        """A callback that meets a widget deleted while the task ran is only logged."""
        try:
            cb(*a)
        except RuntimeError as ex:
            if "already deleted" not in str(ex):
                raise
            log.warning("window rebuilt while a task ran, stale widget in callback: %s", ex)

    def cancelled():
        finish()
        if _alive(win) and hasattr(win, "say"):
            win.say(tr("task_cancelled"))
        if on_cancel:
            call(on_cancel)

    def ok(r):
        if handle.cancelled:             # cancel requested but the task just finished: discard, as for a cancel
            cancelled()
            return
        finish()
        call(on_done, r)

    def bad(msg):
        finish()
        ERRORS.append(msg)
        if on_error:
            call(on_error, msg)
        elif not QUIET["v"] and _alive(win) and hasattr(win, "fail"):
            win.fail(msg)

    def prog(f, n):
        job["frac"], job["ptext"] = f, n
        _show_status(status)

    def cleanup():
        th.wait()
        if entry in _RUNNING:
            _RUNNING.remove(entry)
        relay.deleteLater()

    relay = _Relay(ok, bad, prog, cancelled, cleanup)    # created in the UI thread -> queued connections
    Q = Qt.ConnectionType.QueuedConnection
    wk.done.connect(relay.ok, Q)
    wk.failed.connect(relay.bad, Q)
    wk.progress.connect(relay.prog, Q)
    wk.cancelled.connect(relay.cancelled, Q)
    th.started.connect(wk.run)
    th.finished.connect(relay.cleanup, Q)
    entry = (th, wk, relay, handle)
    _RUNNING.append(entry)
    th.start()
    return handle


def wait_tasks(app=None, timeout: float = 60.0) -> bool:
    """Process events until every task has finished (tests). Returns False on timeout."""
    app = app or QApplication.instance()
    end = time.monotonic() + timeout
    while (_RUNNING or _ACTIVE) and time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)
    for _ in range(5):
        app.processEvents()
    return not (_RUNNING or _ACTIVE)


def shutdown_tasks(timeout_ms: int = 10000) -> None:
    """On exit: cancel every task and wait for the threads within the total time limit.
    A thread that is still running keeps its reference: destroying a running QThread aborts the process."""
    entries = list(_RUNNING)
    for _th, _wk, _relay, handle in entries:
        handle.cancel()
    deadline = time.monotonic() + timeout_ms / 1000
    for entry in entries:
        th = entry[0]
        try:
            th.quit()
            if th.wait(max(0, int((deadline - time.monotonic()) * 1000))) and entry in _RUNNING:
                _RUNNING.remove(entry)
        except RuntimeError:          # C++ object already deleted
            log.debug("shutdown_tasks: thread object already deleted", exc_info=True)
            if entry in _RUNNING:
                _RUNNING.remove(entry)
    if _RUNNING:
        log.warning("%d background thread(s) still running at exit", len(_RUNNING))


atexit.register(shutdown_tasks)
