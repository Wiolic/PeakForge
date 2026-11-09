"""PeakForge 锻峰 — Windows installer (double-click this file).

Creates a private virtual environment, installs PeakForge from this folder, and adds
desktop / Start-menu shortcuts, a .xpsproj file association and an uninstaller.
Requires Python 3.10+ (3.11/3.12 recommended) and an internet connection for pip.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

SRC = os.path.dirname(os.path.abspath(__file__))
APP = "PeakForge"
DEFAULT_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", APP)
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _ps(cmd: str):
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], creationflags=NO_WINDOW, check=False)


def shortcut(lnk: str, target: str, args: str, icon: str, workdir: str):
    os.makedirs(os.path.dirname(lnk), exist_ok=True)
    _ps(f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        f"$s.TargetPath='{target}';$s.Arguments='{args}';$s.IconLocation='{icon}';"
        f"$s.WorkingDirectory='{workdir}';$s.Save()")


def associate(pythonw: str, icon: str):
    """Per-user file association for .xpsproj (no admin rights needed)."""
    import winreg
    base = r"Software\Classes"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\.xpsproj") as k:
        winreg.SetValue(k, "", winreg.REG_SZ, "PeakForge.Project")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\PeakForge.Project") as k:
        winreg.SetValue(k, "", winreg.REG_SZ, "PeakForge project")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\PeakForge.Project\DefaultIcon") as k:
        winreg.SetValue(k, "", winreg.REG_SZ, icon)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\PeakForge.Project\shell\open\command") as k:
        winreg.SetValue(k, "", winreg.REG_SZ, f'"{pythonw}" -m peakforge gui "%1"')


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PeakForge 锻峰 — 安装 / Setup")
        self.geometry("640x460")
        f = ttk.Frame(self, padding=14)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="PeakForge 锻峰  XPS 分析软件 / XPS analysis", font=("Microsoft YaHei", 14, "bold")).pack(anchor="w")
        ttk.Label(f, text=f"Python {sys.version.split()[0]}  ·  需要联网，约 600 MB，3–10 分钟 / needs internet, ~600 MB").pack(anchor="w", pady=(2, 10))
        row = ttk.Frame(f); row.pack(fill="x")
        ttk.Label(row, text="安装目录 / Folder:").pack(side="left")
        self.dir = tk.StringVar(value=DEFAULT_DIR)
        ttk.Entry(row, textvariable=self.dir).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="…", width=3, command=self._browse).pack(side="left")
        self.desk = tk.BooleanVar(value=True)
        self.assoc = tk.BooleanVar(value=True)
        self.origin = tk.BooleanVar(value=self._has_origin())
        ttk.Checkbutton(f, text="桌面快捷方式 / Desktop shortcut", variable=self.desk).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(f, text="关联 .xpsproj 工程文件 / Associate .xpsproj files", variable=self.assoc).pack(anchor="w")
        ttk.Checkbutton(f, text="安装 originpro（本机有 Origin 2021+ 时可直接生成 .opju）/ install originpro",
                        variable=self.origin).pack(anchor="w")
        self.log = tk.Text(f, height=12, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=8)
        self.bar = ttk.Progressbar(f, mode="indeterminate")
        self.bar.pack(fill="x")
        self.btn = ttk.Button(f, text="安装 / Install", command=self.start)
        self.btn.pack(anchor="e", pady=(8, 0))
        if sys.version_info < (3, 10):
            messagebox.showerror(APP, "需要 Python 3.10 以上 / Python 3.10+ required")

    def _has_origin(self):
        for base in (r"C:\Program Files\OriginLab", r"C:\Program Files (x86)\OriginLab"):
            if os.path.isdir(base):
                return True
        return False

    def _browse(self):
        d = filedialog.askdirectory(initialdir=os.path.dirname(self.dir.get()))
        if d:
            self.dir.set(os.path.join(d, APP))

    def say(self, s):
        self.log.insert("end", s + "\n")
        self.log.see("end")

    def run(self, args):
        self.say("> " + " ".join(args))
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        for line in p.stdout:
            line = line.rstrip()
            if line:
                self.after(0, self.say, line[:200])
        if p.wait() != 0:
            raise RuntimeError(f"failed: {' '.join(args)}")

    def start(self):
        self.btn.config(state="disabled")
        self.bar.start(12)
        threading.Thread(target=self._install, daemon=True).start()

    def _install(self):
        try:
            d = self.dir.get()
            os.makedirs(d, exist_ok=True)
            venv = os.path.join(d, "venv")
            if not os.path.exists(os.path.join(venv, "Scripts", "python.exe")):
                self.run([sys.executable, "-m", "venv", venv])
            py = os.path.join(venv, "Scripts", "python.exe")
            pyw = os.path.join(venv, "Scripts", "pythonw.exe")
            self.run([py, "-m", "pip", "install", "--upgrade", "pip"])
            spec = SRC + ("[origin]" if self.origin.get() else "")
            self.run([py, "-m", "pip", "install", "--upgrade", spec])
            icon = os.path.join(d, "peakforge.ico")
            shutil.copy(os.path.join(SRC, "src", "peakforge", "assets", "peakforge.ico"), icon)
            start_menu = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs", APP)
            shortcut(os.path.join(start_menu, "PeakForge 锻峰.lnk"), pyw, "-m peakforge gui", icon, d)
            if self.desk.get():
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut(os.path.join(desktop, "PeakForge 锻峰.lnk"), pyw, "-m peakforge gui", icon, d)
            if self.assoc.get():
                associate(pyw, icon)
            unin = os.path.join(d, "uninstall_PeakForge.bat")
            with open(unin, "w", encoding="utf-8") as f:
                f.write("@echo off\r\nchcp 65001 >nul\r\n"
                        f'del "%USERPROFILE%\\Desktop\\PeakForge 锻峰.lnk" 2>nul\r\n'
                        f'rmdir /s /q "{start_menu}" 2>nul\r\n'
                        'reg delete "HKCU\\Software\\Classes\\.xpsproj" /f >nul 2>nul\r\n'
                        'reg delete "HKCU\\Software\\Classes\\PeakForge.Project" /f >nul 2>nul\r\n'
                        f'echo PeakForge removed. Projects and ~\\.peakforge are kept.\r\n'
                        f'start "" /b cmd /c "timeout /t 1 >nul & rmdir /s /q \\"{d}\\""\r\n')
            shortcut(os.path.join(start_menu, "卸载 Uninstall PeakForge.lnk"), unin, "", icon, d)
            self.run([py, "-m", "peakforge", "--version"])
            with open(os.path.join(d, "location.txt"), "w", encoding="utf-8") as f:
                f.write(py)
            self.after(0, self._finish, pyw)
        except Exception as e:      # noqa: BLE001
            self.after(0, self._error, str(e))

    def _finish(self, pyw):
        self.bar.stop()
        self.say("✓ 安装完成 / Done")
        if messagebox.askyesno(APP, "安装完成，现在启动 PeakForge？\nInstalled. Launch PeakForge now?"):
            subprocess.Popen([pyw, "-m", "peakforge", "gui"], creationflags=NO_WINDOW)
        self.destroy()

    def _error(self, msg):
        self.bar.stop()
        self.btn.config(state="normal")
        messagebox.showerror(APP, msg)


if __name__ == "__main__":
    Installer().mainloop()
