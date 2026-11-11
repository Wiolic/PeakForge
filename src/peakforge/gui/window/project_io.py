"""Project lifecycle: new / open / watch / import / validation / diagnostics."""
from __future__ import annotations

import os
import time

from PySide6.QtWidgets import (QFileDialog, QInputDialog, QMessageBox)

from ... import APP_NAME
from ...io import FILE_FILTER
from ...io.registry import TableReader
from ...logs import log
from ...export.themes import theme_id
from ...project import EXT, Project
from ..i18n import tr


class ProjectMixin:
    def new_project(self):
        d = QFileDialog.getExistingDirectory(self, tr("new_project"))
        if not d:
            return
        name, ok = QInputDialog.getText(self, tr("new_project"), "Name", text=os.path.basename(d))
        if not ok:
            return
        p = Project.create(d, name or None)
        self.open_project(p.path)

    def open_project_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("open_project"), "", f"PeakForge (*{EXT})")
        if f:
            self.open_project(f)

    def open_project(self, path: str):
        try:
            self.project = Project.open(path)
        except (OSError, ValueError) as e:      # SchemaError / ReadError are ValueErrors
            self.fail(f"{path}\n{self.err(e)}")
            return
        self._remember(self.project.path)
        self.setWindowTitle(f"{APP_NAME} — {self.project.name}")
        th = theme_id(self.project.settings.get("theme"))
        self.view.theme = th
        self.palette.set_theme(th)
        self.brand_sub.setText(f"·   {self.project.name}")
        self._watch()
        self.refresh_tree()
        self.log.appendPlainText(time.strftime("%H:%M:%S  ") + self.project.path)
        self.statusBar().showMessage(f"{self.project.name}: {len(self.project.spectra)} spectra", 4000)

    def _watch(self):
        for p in self.watcher.files() + self.watcher.directories():
            self.watcher.removePath(p)
        if self.project:
            self.watcher.addPath(self.project.path)
            md = os.path.join(self.project.root, "models")
            os.makedirs(md, exist_ok=True)
            self.watcher.addPath(md)

    def _fs_changed(self, _path):
        if time.time() < self._own_write:
            return
        self._reload_timer.start()

    def _external_reload(self):
        if self.project is None:
            return
        from ..tasks import active
        if active():        # a background job is working on copies: reload after it has written back
            self._reload_pending = True
            self._reload_timer.start()
            return
        if time.time() < self._own_write:
            if self._reload_pending:      # an external change waited for a job: retry after our own write
                self._reload_timer.start()
            return
        self._reload_pending = False
        key = self.key
        try:
            self.project.reload()
        except (OSError, ValueError) as e:      # half-written file from the agent: retry on next change
            log.warning("external reload of %s failed: %s", self.project.path, e)
            return
        self.project.results.clear()
        self._watch()
        self.refresh_tree(select=key)
        self.say(tr("reloaded"))

    def _mark_write(self):
        self._own_write = time.time() + 1.5

    def import_files(self):
        if self.project is None:
            self.new_project()
            if self.project is None:
                return
        files, _ = QFileDialog.getOpenFileNames(self, tr("import"), "", FILE_FILTER)
        if not files:
            return
        self._add_files(files)

    def _add_files(self, files, template: str | None = None):
        self._mark_write()
        failed_tables = []
        for f in files:
            try:
                keys = self.project.add_file(f, template=template)
                self.say(f"+ {os.path.basename(f)}: {len(keys)} spectra")
            except (OSError, ValueError) as e:
                if template is None and os.path.splitext(f)[1].lower() in TableReader.suffixes:
                    failed_tables.append(f)
                self.fail(f"{f}: {self.err(e)}")
        self.refresh_tree()
        if failed_tables:
            self.import_mapped(failed_tables)

    def import_mapped(self, files=None):
        """Import tables through a saved column template or a new one made in the wizard."""
        if self.project is None:
            self.new_project()
            if self.project is None:
                return
        if not files:
            files, _ = QFileDialog.getOpenFileNames(self, tr("import_mapped"), "",
                                                    f"{tr('tables_filter')} (*.csv *.txt *.dat *.xy *.xlsx *.xls *.xlsm);;All files (*)")
            if not files:
                return
        new = tr("wiz_title") + "…"
        names = list(self.project.formats)
        name = new
        if names:
            name, ok = QInputDialog.getItem(self, tr("template"), tr("template"), [new] + names, 0, False)
            if not ok:
                return
        if name == new:
            from .colwizard import ColumnWizard
            try:
                dlg = ColumnWizard(files[0], self.project.formats, self)
            except (OSError, ValueError) as e:
                self.fail(f"{files[0]}: {self.err(e)}")
                return
            if not dlg.exec():
                return
            try:
                self._mark_write()
                self.project.add_template(dlg.template_name, dlg.template)
            except ValueError as e:
                self.fail(self.err(e))
                return
            name = dlg.template_name
        self._add_files(files, template=name)

    def validate_project(self):
        if self.project is None:
            self.fail(tr("no_project"))
            return
        from ... import schema
        rep = schema.validate_project(self.project.path)
        if not rep.items:
            QMessageBox.information(self, APP_NAME, tr("validate_ok"))
            return
        self.say(rep.text())
        box = QMessageBox(QMessageBox.Icon.Warning if rep.n_err else QMessageBox.Icon.Information, APP_NAME,
                          tr("validate_title", e=rep.n_err, w=rep.n_warn), parent=self)
        box.setDetailedText(rep.text())
        box.exec()

    def export_diagnostics(self):
        from ... import logs
        try:
            path = logs.diagnostics_zip(project=self.project)
        except OSError as e:
            self.fail(str(e))
            return
        self.say(f"{tr('diag_done')} {path}")
        QMessageBox.information(self, APP_NAME, f"{tr('diag_done')}\n{path}")
        self.open_log_folder()

    def open_log_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from ... import logs
        logs.LOG_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs.LOG_DIR)))
