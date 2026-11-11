"""Slow work: fitting, diagnostics, batch, export — in background tasks (see peakforge/tasks.py).

Pattern for every job: (1) in the UI thread read what is needed from the Project (model copy + Prepared data,
export snapshot) and remember a stamp of what the result will replace; (2) the worker only runs numerical code
on those copies, reporting progress / checking for a cancel; (3) on_done (UI thread) drops the result when the
project or the model changed meanwhile (T3), otherwise writes it back. Cancelling leaves the project unchanged.
"""
from __future__ import annotations

import os

from ...core.diagnostics import diagnose
from ...core.fit import apply_result
from ...core.fit import fit as run_fit
from ...logs import log
from ..dialogs import BatchDialog, ExportDialog
from ..i18n import tr
from ..tasks import run_task


class JobsMixin:
    # ---- helpers ---------------------------------------------------------------------------------
    @staticmethod
    def _stamp(proj, key):
        """The stored model of `key` (JSON dict or None): what a finished fit is about to replace."""
        rec = proj.get_model_record(key)
        return rec["model"] if rec else None

    def _stale(self, proj, key, stamp) -> bool:
        """True when the project was replaced or the stored model of `key` changed since the job started."""
        return self.project is not proj or self._stamp(proj, key) != stamp

    # ---- fitting ---------------------------------------------------------------------------------
    def fit_current(self, n_starts: int = 3):
        if self.key is None:
            return
        if self.model is None:
            self.model = self.project.new_model(self.key)
        else:
            self._store()
        proj, key = self.project, self.key
        try:
            model, prep = proj.fit_inputs(key, self.model.copy())
        except ValueError as e:
            self.fail(f"{key}: {e}")
            return
        stamp = self._stamp(proj, key)

        def job(task):
            r = run_fit(model, prep, n_starts=n_starts, check=task.check)
            apply_result(model, r)
            return model, r

        def done(out):
            m, r = out
            if self._stale(proj, key, stamp):
                self.say(tr("result_discarded", key=key))
                return
            self._mark_write()
            proj.store_fit(key, m, r)
            if self.key == key:
                self.model = m
                self._show(r, keep_view=True)
                self.refresh_tree_status()
            self.say(f"{key}: RMS {r.rms_pct:.2f} %  " + "  ".join(f"{k} {v:.1f}%" for k, v in r.fractions.items()))
        run_task(self, job, done, busy_text=tr("fitting"), button_=self.tool.get("fit"), progress=True)

    def fit_all(self):
        if self.project is None:
            return
        proj = self.project
        n = self.panel.starts.value()
        jobs, errors = [], []
        for k in proj.keys(narrow_only=True):
            try:
                m, prep = proj.fit_inputs(k)
            except Exception as e:     # noqa: BLE001 — one unusable spectrum must not stop the batch
                log.warning("fit %s: no usable input", k, exc_info=True)
                errors.append((k, str(e)))
                continue
            jobs.append((k, m, prep, self._stamp(proj, k)))
        for k, err in errors:
            self.say(f"{k}: ERROR {err}")
        if not jobs:
            return

        def job(task):
            out = []
            for i, (k, m, prep, _stamp) in enumerate(jobs):
                task.progress(i / len(jobs), k)
                try:
                    r = run_fit(m, prep, n_starts=n, check=task.check)
                    apply_result(m, r)
                    out.append((k, m, r, None))
                except Exception as e:     # noqa: BLE001 — one failed fit must not stop the batch
                    log.warning("fit %s failed", k, exc_info=True)
                    out.append((k, None, None, str(e)))
            return out

        def done(out):
            if self.project is not proj:
                self.say(tr("result_discarded", key="*"))
                return
            self._mark_write()
            stamps = {k: s for k, _m, _p, s in jobs}
            for k, m, r, err in out:
                if err is not None:
                    self.say(f"{k}: ERROR " + err)
                elif self._stale(proj, k, stamps[k]):
                    self.say(tr("result_discarded", key=k))
                else:
                    proj.store_fit(k, m, r)
                    self.say(f"{k}: RMS {r.rms_pct:.2f} %")
            self.refresh_tree(select=self.key)
        run_task(self, job, done, busy_text=tr("fitting"), button_=self.tool.get("fit_all"), progress=True)

    def diagnose_current(self):
        if self.key is None or self.model is None:
            return
        proj, key, model = self.project, self.key, self.model.copy()
        try:
            prep = proj.prepared(key, model)
        except Exception as e:     # noqa: BLE001 — shown to the user
            log.warning("diagnose %s: prepare failed", key, exc_info=True)
            self.fail(f"{key}: {e}")
            return
        self.tabs.setCurrentWidget(self.diag_txt)
        self.diag_txt.setPlainText(tr("fitting"))

        def job(task):
            r = run_fit(model, prep, n_starts=1, check=task.check)
            return diagnose(model, prep, r, deep=True, progress=task.progress, check=task.check)

        def done(d):
            if self.project is not proj or self.key != key:
                return
            lines = [f"{tr('rms')}: {d['rms_pct']:.2f} %    χ²ᵣ = {d['chi2_red']:.2f}    BIC = {d['bic']:.1f}", ""]
            if d["warnings"]:
                lines += [tr("warnings") + ":"] + ["  ⚠ " + w for w in d["warnings"]] + [""]
            lines.append("ΔBIC (remove component → refit):")
            for s in d.get("significance", []):
                lines.append(f"  {s['label']:<22} ΔBIC {s['d_bic']:+8.1f}   ΔRMS {s['d_rms']:+.2f} %   {s['verdict']}")
            st = d.get("stability", {})
            if st:
                lines.append("")
                lines.append(f"Multi-start ({st['n_equivalent']}/{st['n_starts']} equivalent solutions):")
                for k, v in st["fractions"].items():
                    lines.append(f"  {k:<22} {v['mean']:.1f} ± {v['std']:.1f} %  [{v['min']:.1f}–{v['max']:.1f}]")
            if d["correlations"]:
                lines.append("")
                lines.append("|corr| ≥ 0.95:")
                for c in d["correlations"]:
                    lines.append(f"  {c['a']} ~ {c['b']}: {c['r']:+.3f}")
            self.diag_txt.setPlainText("\n".join(lines))

        def cancelled():
            self.diag_txt.setPlainText(tr("task_cancelled"))
        run_task(self, job, done, busy_text=tr("diagnose"), button_=self.tool.get("diag"), progress=True,
                 on_cancel=cancelled)

    def batch(self):
        if self.key is None or self.model is None:
            return
        self._store()
        dlg = BatchDialog(self.project, self.key, self)
        if not dlg.exec():
            return
        v = dlg.values()
        proj, src = self.project, self.key
        try:
            inputs = proj.batch_inputs(src, v["targets"], v["fix"])
        except ValueError as e:
            self.fail(str(e))
            return
        if not inputs:
            return
        stamps = {k: self._stamp(proj, k) for k, _m, _p in inputs}

        def job(task):
            out = []
            for i, (k, m, prep) in enumerate(inputs):
                task.progress(i / len(inputs), k)
                r = run_fit(m, prep, n_starts=v["n_starts"], check=task.check)
                apply_result(m, r)
                out.append((k, m, r))
            return out

        def done(out):
            if self.project is not proj:
                self.say(tr("result_discarded", key="*"))
                return
            self._mark_write()
            for k, m, r in out:
                if self._stale(proj, k, stamps[k]):
                    self.say(tr("result_discarded", key=k))
                    continue
                proj.store_fit(k, m, r)
                self.say(f"{k}: RMS {r.rms_pct:.2f} %  " + "  ".join(f"{n} {x:.1f}%" for n, x in r.fractions.items()))
            self.refresh_tree(select=src)
        run_task(self, job, done, busy_text=tr("fitting"), progress=True)

    # ---- export ----------------------------------------------------------------------------------
    def export(self):
        if self.project is None:
            return
        dlg = ExportDialog(self.project, self)
        if not dlg.exec():
            return
        v = dlg.values()
        from ...export.exporter import collect_export, run_export
        try:
            snap = collect_export(self.project, None, v["out_dir"], v["theme"], v["formats"], v["dpi"])
        except (OSError, ValueError) as e:
            self.fail(str(e))
            return

        def job(task):
            return run_export(snap, task.progress)

        def done(r):
            self.say(f"export → {r['out_dir']}  ({r['n']} fits, {len(r['figures'])} figures)")
            o = r.get("origin")
            if o:
                if o["mode"] == "originpro":
                    self.say(f"Origin: {o['opju']}")
                else:
                    self.say(tr("origin_missing") + " " + o["hint"])
            if r.get("xlsx"):
                self.say(f"Excel: {r['xlsx']}")
            os.startfile(r["out_dir"]) if hasattr(os, "startfile") else None
        run_task(self, job, done, busy_text=tr("export_all").rstrip("….") + "…", button_=self.tool.get("export"),
                 progress=True)
