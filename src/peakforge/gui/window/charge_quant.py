"""Charge correction and quantification."""
from __future__ import annotations


from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QInputDialog, QMessageBox, QTableWidgetItem

from ..i18n import tr, tr_msg


class ChargeQuantMixin:
    def auto_charge(self):
        if self.project is None:
            return
        self._mark_write()
        out = self.project.auto_charge()
        st = self.project.settings
        self.say(f"{st.get('charge_region') or 'C 1s'} → {st.get('charge_ref', 284.8)} eV: " +
                 ", ".join(f"{k} {v:+.2f}" for k, v in out.items()))
        msgs = [f"{tr('charge_failed')} {self.project.sample_label(smp)}: {tr_msg(why)}"
                for smp, why in self.project.charge_failures.items()]
        msgs += [f"{tr('charge_check_failed')} {self.project.sample_label(smp)}: {tr_msg(w)}"
                 for smp, ws in self.project.charge_warnings.items() for w in ws]
        for m in msgs:
            self.say(m)
        if msgs:
            QMessageBox.warning(self, tr("auto_charge"), "\n\n".join(msgs))
        self.refresh_tree()

    def set_charge_reference(self):
        """Project-wide reference line and energy for auto charge correction."""
        if self.project is None:
            return
        st = self.project.settings
        regions = sorted({s.region for s in self.project.spectra.values() if not s.is_survey}) or ["C 1s"]
        cur = st.get("charge_region") or "C 1s"
        if cur not in regions:
            regions.insert(0, cur)
        reg, ok = QInputDialog.getItem(self, tr("charge_reference"), tr("charge_ref_region"), regions,
                                       regions.index(cur), True)
        if not ok or not reg.strip():
            return
        default = st.get("charge_ref", 284.8) if reg == cur else (284.8 if reg == "C 1s" else 0.0)
        be, ok = QInputDialog.getDouble(self, tr("charge_reference"), tr("charge_ref_be"), default, 0, 2000, 2)
        if not ok:
            return
        self._mark_write()
        st["charge_region"], st["charge_ref"] = reg.strip(), float(be)
        self.project.save()
        self.say(f"{tr('charge_reference')} {reg.strip()} → {be:.2f} eV")

    def set_shift(self, sample: str | None = None):
        if self.project is None:
            return
        if sample is None:
            if self.key is None:
                return
            sample = self.project.spectra[self.key].sample
        v, ok = QInputDialog.getDouble(self, tr("set_shift"), f"{sample} (eV)", self.project.shift(sample), -50, 50, 3)
        if ok:
            self._mark_write()
            self.project.set_shift(sample, v)
            self.refresh_tree()

    def show_quant(self):
        if self.project is None:
            return
        q = self.project.quantify()
        t = self.quant_tab
        t.blockSignals(True)
        cols = [tr("sample"), tr("region"), tr("col_area"), "src", tr("rsf"), tr("at_pct")]
        t.setColumnCount(len(cols)); t.setHorizontalHeaderLabels(cols); t.setRowCount(len(q))
        for i, e in enumerate(q):
            vals = [self.project.sample_label(e["sample"]), e["region"], f"{e['area']:.4g}", e["area_source"],
                    "" if e.get("rsf") is None else f"{e['rsf']:.4g}",
                    "" if e.get("at_pct") is None else f"{e['at_pct']:.2f}"]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if j != 4:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    it.setData(Qt.ItemDataRole.UserRole, e["region"])
                t.setItem(i, j, it)
        t.resizeColumnsToContents()
        t.setToolTip(tr("quant_method"))
        t.blockSignals(False)
        self.say(tr("quant_method"))
        self.tabs.setCurrentWidget(t)

    def _rsf_edited(self, it):
        if it.column() != 4:
            return
        try:
            v = float(it.text())
        except ValueError:
            return
        self._mark_write()
        self.project.set_rsf(it.data(Qt.ItemDataRole.UserRole), v)
        QTimer.singleShot(0, self.show_quant)
