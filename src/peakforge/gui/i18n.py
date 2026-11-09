"""Tiny dictionary-based translation (zh / en). Language is stored in ~/.peakforge/settings.json."""
from __future__ import annotations

import json
import os

_SETTINGS = os.path.join(os.path.expanduser("~"), ".peakforge", "settings.json")

T = {
    # menus
    "menu_file": ("文件", "&File"), "menu_analysis": ("分析", "&Analysis"), "menu_export": ("导出", "&Export"),
    "menu_view": ("视图", "&View"), "menu_agent": ("Agent", "&Agent"), "menu_help": ("帮助", "&Help"),
    "new_project": ("新建工程…", "New project…"), "open_project": ("打开工程…", "Open project…"),
    "import": ("导入数据…", "Import data…"), "recent": ("最近的工程", "Recent projects"),
    "quit": ("退出", "Quit"), "auto_charge": ("自动荷电校准 (C 1s)", "Auto charge correction (C 1s)"),
    "set_shift": ("手动设置荷电位移…", "Set charge shift…"), "fit": ("拟合", "Fit"),
    "fit_all": ("拟合全部", "Fit all"), "batch": ("批量应用当前模型…", "Apply model to others…"),
    "diagnose": ("拟合诊断", "Diagnostics"), "quant": ("元素定量", "Quantification"),
    "export_all": ("导出…", "Export…"), "language": ("语言", "Language"), "theme": ("图形主题", "Figure theme"),
    "agent_connect": ("连接 AI Agent（MCP）…", "Connect AI agent (MCP)…"),
    "agent_md": ("写入 AGENTS.md", "Write AGENTS.md"), "about": ("关于", "About"),
    "save_preset": ("保存为预设…", "Save as preset…"), "undo": ("撤销", "Undo"), "redo": ("重做", "Redo"),
    "remove_sample": ("移除样品", "Remove sample"), "rename_sample": ("重命名样品…", "Rename sample…"),
    # docks / panels
    "spectra": ("谱图", "Spectra"), "model": ("分峰模型", "Peak model"), "results": ("结果", "Results"),
    "log": ("日志", "Log"), "preset": ("预设", "Preset"), "apply": ("应用", "Apply"),
    "background": ("背景", "Background"), "bg_kind": ("类型", "Type"), "bg_lo": ("低端 (eV)", "Low end (eV)"),
    "bg_hi": ("高端 (eV)", "High end (eV)"), "fit_range": ("拟合范围", "Fit range"),
    "components": ("组分", "Components"), "add": ("添加", "Add"), "remove": ("删除", "Remove"),
    "parameters": ("参数", "Parameters"), "starts": ("起点数", "Starts"),
    "weighting": ("加权", "Weighting"), "deep": ("深度诊断", "Deep diagnostics"),
    "col_name": ("名称", "Name"), "col_label": ("图例", "Label"), "col_shape": ("线形", "Shape"),
    "col_doublet": ("双峰", "Doublet"), "col_total": ("计入占比", "In total"),
    "col_param": ("参数", "Param"), "col_value": ("值", "Value"), "col_min": ("下限", "Min"),
    "col_max": ("上限", "Max"), "col_vary": ("可变", "Vary"), "col_expr": ("联动表达式", "Link expr"),
    "col_err": ("±1σ", "±1σ"), "col_center": ("峰位 (eV)", "Center (eV)"), "col_fwhm": ("FWHM (eV)", "FWHM (eV)"),
    "col_area": ("面积", "Area"), "col_frac": ("占比 (%)", "Fraction (%)"),
    "no_project": ("没有打开的工程。请新建或打开一个工程。", "No project open. Create or open one."),
    "no_model": ("尚无模型：选择预设后点“应用”，或在谱图上右键添加峰。",
                 "No model: pick a preset and Apply, or right-click the plot to add a peak."),
    "hint_canvas": ("右键：在此添加峰 · 拖动峰顶：移动峰 · 拖动虚线：背景端点 · 滚轮：缩放",
                    "Right-click: add peak · drag peak top: move · drag dashed lines: background ends · wheel: zoom"),
    "shift": ("荷电位移", "Charge shift"), "fitting": ("拟合中…", "Fitting…"), "done": ("完成", "Done"),
    "rms": ("残差 RMS", "Residual RMS"), "warnings": ("警告", "Warnings"),
    "export_title": ("导出", "Export"), "formats": ("格式", "Formats"), "out_dir": ("输出目录", "Output folder"),
    "choose": ("选择…", "Choose…"), "ok": ("确定", "OK"), "cancel": ("取消", "Cancel"),
    "batch_title": ("批量应用模型", "Apply model to other spectra"), "fix_params": ("固定参数", "Fix parameters"),
    "targets": ("目标谱图", "Targets"), "restart_lang": ("语言已切换。", "Language switched."),
    "origin_missing": ("未检测到 originpro / Origin：已生成数据和脚本，在 Origin 中运行：",
                       "originpro / Origin not available: data + script written. In Origin run:"),
    "reloaded": ("工程已被外部修改（Agent），已重新载入。", "Project changed externally (agent) — reloaded."),
    "sample": ("样品", "Sample"), "region": ("区域", "Region"), "label_sample": ("样品显示名", "Sample label"),
    "copy": ("复制", "Copy"), "residual": ("残差", "Residual"),
    "add_peak_here": ("在 {x:.2f} eV 添加峰", "Add peak at {x:.2f} eV"),
    "set_bg_lo": ("背景低端设为 {x:.2f} eV", "Set background low end to {x:.2f} eV"),
    "set_bg_hi": ("背景高端设为 {x:.2f} eV", "Set background high end to {x:.2f} eV"),
    "remove_comp": ("删除组分 {n}", "Remove component {n}"),
    "palette": ("配色", "Palette"), "palette_new": ("＋ 新建自定义配色…", "+ New custom palette…"),
    "fill_alpha": ("填充不透明度", "Fill opacity"), "inspector": ("分峰模型", "Peak model"),
    "samples": ("样品与谱区", "Samples & regions"), "view_reset": ("复位视图", "Reset view"),
    "view_pan": ("平移", "Pan"), "view_zoom": ("框选放大", "Zoom to box"), "view_save": ("保存图片", "Save image"),
    "empty_title": ("开始一个分析", "Start an analysis"),
    "empty_body": ("新建或打开一个工程，然后导入 .spe / .vms / .csv / .xlsx 数据。",
                   "Create or open a project, then import .spe / .vms / .csv / .xlsx data."),
    "agent": ("Agent", "Agent"), "show_residual": ("残差", "Residual"),
    "rsf": ("灵敏度因子 RSF", "RSF"), "at_pct": ("原子 %", "Atomic %"),
    "agent_text": ("在 Claude Code 等 Agent 中注册 PeakForge MCP 服务器后，可以用自然语言让它分析当前工程；"
                   "GUI 会自动显示 Agent 的修改。", "Register the PeakForge MCP server in your agent "
                   "(Claude Code, Codex, Cursor…) and ask it to analyse this project in plain language; "
                   "the GUI shows its changes live."),
}

_lang = None


def _load() -> dict:
    try:
        with open(_SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def settings() -> dict:
    return _load()


def save_setting(key: str, value):
    d = _load()
    d[key] = value
    os.makedirs(os.path.dirname(_SETTINGS), exist_ok=True)
    with open(_SETTINGS, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def lang() -> str:
    global _lang
    if _lang is None:
        _lang = _load().get("lang", "zh")
    return _lang


def set_lang(code: str):
    global _lang
    _lang = code
    save_setting("lang", code)


def tr(key: str, **kw) -> str:
    v = T.get(key)
    if v is None:
        return key
    s = v[0] if lang() == "zh" else v[1]
    return s.format(**kw) if kw else s
