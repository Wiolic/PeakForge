"""Sample / region tree."""
from __future__ import annotations


from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QInputDialog, QMessageBox, QTreeWidgetItem)

from ... import APP_NAME, presets
from ..i18n import tr
from ..style import C
from .common import _dot


class TreeMixin:
    def refresh_tree(self, select: str | None = None):
        p = self.project
        self.tree.blockSignals(True)
        self.tree.clear()
        first = None
        target = None
        for smp in p.samples():
            sh = p.shift(smp)
            it = QTreeWidgetItem([p.sample_label(smp), f"{sh:+.2f} eV"])
            f = it.font(0); f.setBold(True); it.setFont(0, f)
            it.setForeground(1, QColor(C["faint"]))
            it.setToolTip(1, tr("shift"))
            it.setData(0, Qt.ItemDataRole.UserRole, ("sample", smp))
            self.tree.addTopLevelItem(it)
            for k in p.keys(sample=smp):
                s = p.spectra[k]
                rec = p.get_model_record(k)
                ch = QTreeWidgetItem(["", ""])
                ch.setData(0, Qt.ItemDataRole.UserRole, ("spec", k))
                self._decorate(ch, s, rec)
                it.addChild(ch)
                if first is None and not s.is_survey:
                    first = ch
                if k == (select or self.key):
                    target = ch
            it.setExpanded(True)
        self.tree.blockSignals(False)
        (target or first) and self.tree.setCurrentItem(target or first)
        if self.tree.currentItem() is None:
            self.view.clear(tr("no_project") if not p.spectra else "")

    def _decorate(self, item, s, rec):
        """Region row: status dot (grey = no model, amber = not fitted / stale, green = fitted) + RMS."""
        item.setText(0, s.region + (f"  #{s.index}" if s.index else ""))
        if rec and rec.get("result") and not rec.get("result_stale"):
            col, rms = C["ok"], f"{rec['result'].get('rms_pct', 0):.2f} %"
        elif rec:
            col, rms = C["warn"], (f"{rec['result'].get('rms_pct', 0):.2f} %" if rec.get("result") else "—")
        else:
            col, rms = "#C9CDD4", ""
        item.setIcon(0, _dot(col))
        item.setText(1, rms)
        item.setForeground(1, QColor(C["muted"]))

    def _tree_changed(self, cur, _prev):
        if cur is None:
            return
        kind, val = cur.data(0, Qt.ItemDataRole.UserRole)
        if kind == "spec":
            self.select_key(val)

    def _tree_menu(self, pos):
        it = self.tree.itemAt(pos)
        if it is None or self.project is None:
            return
        from PySide6.QtWidgets import QMenu
        kind, val = it.data(0, Qt.ItemDataRole.UserRole)
        smp = val if kind == "sample" else self.project.spectra[val].sample
        m = QMenu(self)
        if kind == "spec":
            m.addAction(tr("set_region"), lambda: self.assign_region(val))
            m.addSeparator()
        m.addAction(tr("set_shift"), lambda: self.set_shift(smp))
        m.addAction(tr("rename_sample"), lambda: self.rename_sample(smp))
        m.addAction(tr("remove_sample"), lambda: self.remove_sample(smp))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def assign_region(self, key):
        """Pick the element / core level for a spectrum (any element Li–U, or a single sub-level)."""
        choices = presets.orbital_choices()
        labels = [d for _k, d in choices]
        cur = self.project.spectra[key].region
        idx = next((i for i, (k, _d) in enumerate(choices) if k == cur), 0)
        txt, ok = QInputDialog.getItem(self, tr("set_region"),
                                       "Fe 2p · Fe 2p3/2 · Ce 3d …", labels, idx, True)
        if not ok or not txt.strip():
            return
        region = next((k for k, d in choices if d == txt), txt.strip())
        self._mark_write()
        new = self.project.set_region(key, region)
        self.say(f"{key} → {new}")
        self.refresh_tree(select=new)

    def rename_sample(self, smp):
        t, ok = QInputDialog.getText(self, tr("rename_sample"), tr("label_sample"), text=self.project.sample_label(smp))
        if ok and t:
            self._mark_write()
            self.project.set_sample_label(smp, t)
            self.refresh_tree()

    def remove_sample(self, smp):
        if QMessageBox.question(self, APP_NAME, f"{tr('remove_sample')}: {smp}?") != QMessageBox.StandardButton.Yes:
            return
        self._mark_write()
        self.project.remove_sample(smp)
        self.key = None
        self.refresh_tree()

    def refresh_tree_status(self):
        it = self.tree.currentItem()
        if it is None or self.key is None:
            return
        rec = self.project.get_model_record(self.key)
        s = self.project.spectra[self.key]
        self._decorate(it, s, rec)
