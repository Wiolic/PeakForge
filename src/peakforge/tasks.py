"""Cancellable tasks with progress (no Qt: shared by the GUI and the command line).

A task function receives a TaskHandle ``task``.  Call ``task.progress(f, text)`` between steps: it reports
progress and is a cancellation point — once the user has asked to cancel, the next call raises Cancelled and
the task leaves from there.  ``task.check`` is the bare cancellation point to hand to numerical code
(``fit(..., check=task.check)``).

Thread rules (when the GUI runs a task function in a background thread through ``gui.tasks.run_task``):
1. A task function never creates, reads or changes a widget, and never reads or writes the Project;
2. the inputs (model copies, Prepared arrays, export snapshots) are prepared in the UI thread before the task
   starts, and the result is written back in ``on_done`` (UI thread);
3. matplotlib is used through the object-oriented API only (Figure + Agg canvas), never pyplot;
4. a single scipy call cannot be interrupted except at the points where it evaluates the residual: cancelling
   takes effect at the next residual evaluation / progress call.

Cancelled derives from BaseException so that the many ``except Exception`` blocks do not swallow a cancel.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional


class Cancelled(BaseException):
    """The user cancelled the task (deliberately not an Exception)."""


class TaskHandle:
    """Link between a task and its caller: progress and the cancel flag."""

    def __init__(self, on_progress: Optional[Callable[[float, str], None]] = None):
        self._event = threading.Event()
        self._on_progress = on_progress
        self.fraction = 0.0
        self.text = ""

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    def check(self) -> None:
        """Cancellation point: raise Cancelled when a cancel has been requested."""
        if self._event.is_set():
            raise Cancelled()

    def progress(self, f: float = 0.0, text: str = "") -> None:
        """Report progress (f in 0–1) and check for a cancel."""
        self.check()
        self.fraction, self.text = float(f), str(text)
        if self._on_progress is not None:
            self._on_progress(self.fraction, self.text)
