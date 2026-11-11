"""Slow work: fitting, diagnostics, batch, export."""
from __future__ import annotations

import os


from ...core.diagnostics import diagnose
from ...core.fit import fit as run_fit
from ...logs import log
from ..dialogs import BatchDialog, ExportDialog
from ..i18n import tr
from ..workers import submit


class JobsMixin:
    def fit_current(self, n_starts: int = 3):
        if self.key is None:
            return
        if self.model is None:
            self.model = self.project.new_model(self.key)
        else:
            self._store()
        key, model = self.key, self.model.copy()
        self._set_busy(True)

        def job():
            return self.project.fit(key, model, n_starts=n_starts, save=False)

        def done(out):
            self._set_busy(False)
            m, r = out
            self._mark_write()
            self.project.set_model(key, m, r)
            if self.key == key:
                self.model = m
                self._show(r, keep_view=True)
                self.refresh_tree_status()
            self.say(f"{key}: RMS {r.rms_pct:.2f} %  " + "  ".join(f"{k} {v:.1f}%" for k, v in r.fractions.items()))
        submit(job, on_done=done, on_fail=self.fail)

    def fit_all(self):
        if self.project is None:
            return
        keys = self.project.keys(narrow_only=True)
        n = self.panel.starts.value()
        self._set_busy(True)
        self._mark_write()

        def job():
            out = []
            for k in keys:
                try:
                    m, r = self.project.fit(k, n_starts=n)
                    out.append((k, r.rms_pct, None))
                except Exception as e:     # noqa: BLE001 — one failed fit must not stop the batch
                    log.warning("fit %s failed", k, exc_info=True)
                    out.append((k, None, str(e)))
            return out

        def done(out):
            self._set_busy(False)
            self._mark_write()
            for k, rms, err in out:
                self.say(f"{k}: " + (f"RMS {rms:.2f} %" if err is None else "ERROR " + err))
            self.refresh_tree(select=self.key)
        submit(job, on_done=done, on_fail=self.fail)

    def diagnose_current(self):
        if self.key is None or self.model is None:
            return
        key, model = self.key, self.model.copy()
        self._set_busy(True)
        self.tabs.setCurrentWidget(self.diag_txt)
        self.diag_txt.setPlainText(tr("fitting"))

        def job():
            prep = self.project.prepared(key, model)
            r = run_fit(model, prep, n_starts=1)
            return diagnose(model, prep, r, deep=True)

        def done(d):
            self._set_busy(False)
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
        submit(job, on_done=done, on_fail=self.fail)

    def batch(self):
        if self.key is None or self.model is None:
            return
        self._store()
        dlg = BatchDialog(self.project, self.key, self)
        if not dlg.exec():
            return
        v = dlg.values()
        src = self.key
        self._set_busy(True)

        def done(rows):
            self._set_busy(False)
            self._mark_write()
            for r in rows:
                self.say(f"{r['key']}: RMS {r['rms_pct']:.2f} %  " +
                         "  ".join(f"{k} {x:.1f}%" for k, x in r["fractions"].items()))
            self.refresh_tree(select=src)
        self._mark_write()
        submit(self.project.batch_apply, src, v["targets"], v["fix"], v["n_starts"], on_done=done, on_fail=self.fail)

    def export(self):
        if self.project is None:
            return
        dlg = ExportDialog(self.project, self)
        if not dlg.exec():
            return
        v = dlg.values()
        from ...export.exporter import export_all
        self._set_busy(True)

        def done(r):
            self._set_busy(False)
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
        submit(export_all, self.project, None, v["out_dir"], v["theme"], v["formats"], v["dpi"],
               on_done=done, on_fail=self.fail)
