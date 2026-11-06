#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown 阅读器 —— 原生窗口（WebView2）+ 多标签 + 编辑/保存。

用法：
    python app.py                 # 打开空白窗口
    python app.py a.md b.md       # 直接打开若干文件
    python app.py --dir <目录>     # 打开目录里的第一个 md（给文件关联用）

依赖：pywebview（已装）、Windows 自带 WebView2。
"""
import io
import json
import os
import sys
import time

import logging

import webview

HERE = os.path.dirname(os.path.abspath(__file__))

BOOT_T0 = time.perf_counter()      # 进程最早的可用时基，用来量启动到上屏
LOG_PATH = os.path.join(os.environ.get("TEMP") or HERE, "mdreader.log")

# 窗口不要挂在 Api 实例上：pywebview 的 get_functions() 会遍历 js_api 的每个属性，
# 遇到对象就递归下去，Window -> native(WinForms 控件) 会无限递归直到 RecursionError，
# 结果是 _createApi 注入失败、pywebviewready 不派发（窗口起来了但界面一片空）。
_WINDOW = None


def resource_path(*parts):
    """开发时取脚本目录；PyInstaller 打包后取 _MEIPASS（onedir 下是 _internal）。"""
    base = getattr(sys, "_MEIPASS", HERE)
    return os.path.join(base, *parts)


UI = resource_path("ui", "index.html")

MD_EXT = (".md", ".markdown", ".mdown", ".txt")
FILE_TYPES = ("Markdown (*.md;*.markdown;*.txt)", "所有文件 (*.*)")


def read_text(path):
    """md 文件绝大多数是 UTF-8；少数 Windows 老文件是 GBK，兜一下。"""
    with io.open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def detect_eol(path):
    """原文件用 CRLF 还是 LF。textarea 赋值时浏览器会把 CRLF 规范化成 LF，
    不记下来，保存一次整个文件的换行就都变了。"""
    try:
        with io.open(path, "rb") as fh:
            return "\r\n" if b"\r\n" in fh.read() else "\n"
    except OSError:
        return "\n"


def file_payload(path):
    st = os.stat(path)
    return {
        "path": path,
        "name": os.path.basename(path),
        # 统一成 LF 交给前端；保存时再按原文件的换行风格还原
        "content": read_text(path).replace("\r\n", "\n").replace("\r", "\n"),
        "eol": detect_eol(path),
        "mtime": st.st_mtime,
        "size": st.st_size,
        "dir": os.path.dirname(path),
    }


class Api:
    """暴露给 JS 的接口，全部返回 dict / list，避免 JS 侧类型歧义。"""

    def __init__(self):
        # 这里只能放方法和简单数据；放对象会把上面的递归坑引爆
        self.pending = []      # 命令行传进来的文件，等前端就绪后来取

    def log(self, msg):
        """windowed 进程没有控制台，前端只能写文件回报状态。"""
        try:
            with io.open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write("%s +%6.0fms  %s\n" % (
                    time.strftime("%H:%M:%S"),
                    (time.perf_counter() - BOOT_T0) * 1000, msg))
        except OSError:
            pass
        return {"ok": True}

    # ---------------------------------------------------------------- 启动
    def take_startup(self):
        """前端 pywebviewready 之后主动调用。

        不用 window.events.loaded + evaluate_js：那个时机和 app.js 的执行顺序
        没有保证，实测在打包后的 exe 里会静默失效（窗口起来了但文件没加载）。
        """
        paths, self.pending = self.pending, []
        out, errors = [], []
        for p in paths:
            try:
                out.append(file_payload(p))
            except OSError as exc:
                errors.append("%s：%s" % (os.path.basename(p), exc))
        return {"files": out, "error": "；".join(errors)}

    # ---------------------------------------------------------------- 打开
    def open_dialog(self):
        result = _WINDOW.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True, file_types=FILE_TYPES)
        if not result:
            return {"ok": False, "files": []}
        out = []
        for p in result:
            try:
                out.append(file_payload(p))
            except OSError as exc:
                return {"ok": False, "error": "打不开 %s：%s" % (p, exc), "files": out}
        return {"ok": True, "files": out}

    def open_paths(self, paths):
        """拖放或外部传参用：JS 拿到路径后回传这里读。"""
        out, errors = [], []
        for p in paths or []:
            try:
                out.append(file_payload(p))
            except OSError as exc:
                errors.append("%s：%s" % (p, exc))
        return {"ok": not errors, "files": out, "error": "；".join(errors)}

    # ---------------------------------------------------------------- 保存
    def save(self, path, content):
        try:
            # 前端传来的永远是 LF；按原文件的换行风格写回，避免整篇 diff
            data = content.replace("\r\n", "\n").replace("\r", "\n")
            if detect_eol(path) == "\r\n":
                data = data.replace("\n", "\r\n")
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(data)
            return {"ok": True, "mtime": os.stat(path).st_mtime}
        except OSError as exc:
            return {"ok": False, "error": "保存失败：%s" % exc}

    def save_as(self, content, suggested="未命名.md"):
        target = _WINDOW.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=suggested, file_types=FILE_TYPES)
        if not target:
            return {"ok": False, "cancelled": True}
        path = target if isinstance(target, str) else target[0]
        if not os.path.splitext(path)[1]:
            path += ".md"
        res = self.save(path, content)
        if res.get("ok"):
            res["path"] = path
            res["name"] = os.path.basename(path)
        return res

    # ---------------------------------------------------------------- 杂项
    def set_title(self, name):
        if _WINDOW:
            _WINDOW.title = ("%s — Markdown 阅读器" % name) if name else "Markdown 阅读器"
        return {"ok": True}

    def reveal(self, path):
        """在资源管理器里定位文件——报告写完直接找到它很方便。"""
        try:
            import subprocess
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            return {"ok": True}
        except Exception as exc:                      # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def recent_dirs(self):
        """交付目录里通常一堆 md，返回上次打开文件所在目录的 md 列表。"""
        return {"ok": True, "files": []}


def collect_startup_paths(argv):
    paths = []
    for token in argv[1:]:
        if token in ("--dir", "-d"):
            continue
        p = os.path.abspath(token.strip('"'))
        if os.path.isdir(p):
            cand = [os.path.join(p, f) for f in sorted(os.listdir(p))
                    if f.lower().endswith(MD_EXT)]
            if cand:
                paths.append(cand[0])
        elif os.path.isfile(p):
            paths.append(p)
    return paths


def install_crash_logger():
    """--windowed 打包后没有控制台，未捕获的异常要靠这个留下痕迹。"""
    import traceback

    def hook(exc_type, exc_value, exc_tb):
        try:
            with io.open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write("%s  FATAL\n%s\n" % (
                    time.strftime("%H:%M:%S"),
                    "".join(traceback.format_exception(exc_type, exc_value, exc_tb))))
        except OSError:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


# ---------------------------------------------------------------- WebView2

WEBVIEW2_CLIENT = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def webview2_version():
    """从注册表读 WebView2 运行时版本，没装返回 None。

    Evergreen Runtime 会按「机器/用户」和「32/64 位」分别登记，三个位置都要看：
    64 位机器级在 WOW6432Node 下，32 位机器级在 Software 下，用户级在 HKCU。
    """
    try:
        import winreg
    except ImportError:          # 非 Windows 平台，交给 pywebview 自己报错
        return None

    targets = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_CLIENT),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_CLIENT),
        (winreg.HKEY_CURRENT_USER,
         r"Software\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_CLIENT),
    ]
    for hive, sub in targets:
        try:
            with winreg.OpenKey(hive, sub) as key:
                pv = winreg.QueryValueEx(key, "pv")[0]
        except OSError:
            continue
        if pv and str(pv) not in ("", "0.0.0.0"):
            return str(pv)
    return None


def require_webview2():
    """缺运行时的时候 pywebview 通常白窗或静默失败，这里提前拦下来给人话。

    别人的电脑上这几乎是「双击没反应」的唯一原因，值得专门弹个框。
    """
    version = webview2_version()
    if version:
        try:
            api_log("WebView2 runtime = %s" % version)
        except Exception:                                    # noqa: BLE001
            pass
        return True

    text = (
        "Markdown 阅读器需要「Microsoft Edge WebView2 运行时」，"
        "这台电脑上没有找到。\n\n"
        "Windows 11 和较新的 Windows 10 一般自带；如果确实缺失，"
        "点「是」打开微软官方下载页，装那个 2 MB 左右的 Evergreen Runtime，"
        "装完重新打开本程序即可。\n\n"
        "（也可以手动搜 “WebView2 Runtime download” 到微软官网下载）"
    )
    try:
        import ctypes
        MB_YESNO = 0x04
        MB_ICONWARNING = 0x30
        reply = ctypes.windll.user32.MessageBoxW(
            None, text, "缺少 WebView2 运行时 - Markdown 阅读器",
            MB_YESNO | MB_ICONWARNING)
        if reply == 6:                                       # IDYES
            import webbrowser
            webbrowser.open(WEBVIEW2_URL)
    except Exception:                                        # noqa: BLE001
        pass
    return False


def api_log(text):
    """不依赖 Api 实例的粗日志，只用来记启动期信息。"""
    try:
        with io.open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%H:%M:%S"), text))
    except OSError:
        pass


def main():
    install_crash_logger()
    if not require_webview2():
        return 1

    api = Api()
    window = webview.create_window(
        "Markdown 阅读器",
        UI,
        js_api=api,
        width=1220,
        height=840,
        min_size=(720, 480),
        background_color="#ffffff",
        text_select=True,
    )
    global _WINDOW
    _WINDOW = window
    api.pending = collect_startup_paths(sys.argv)
    try:
        io.open(LOG_PATH, "w", encoding="utf-8").close()
    except OSError:
        pass
    api.log("argv=%r" % (sys.argv,))
    api.log("pending=%r" % (api.pending,))
    api.log("UI=%r exists=%s" % (UI, os.path.exists(UI)))
    api.log("MEIPASS=%r" % (getattr(sys, "_MEIPASS", None),))

    def _evt(name):
        def cb(*args):
            api.log("event: %s" % name)
        return cb

    for evt in ("shown", "loaded", "closing", "closed"):
        try:
            getattr(window.events, evt).__iadd__(_evt(evt))
        except Exception as exc:                        # noqa: BLE001
            api.log("event hook %s failed: %r" % (evt, exc))

    webview.start(gui="edgechromium")


if __name__ == "__main__":
    sys.exit(main())
