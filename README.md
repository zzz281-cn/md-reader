# Markdown Reader

A small, fast Markdown viewer / editor for Windows. Native window, multi-tab, preview & edit modes,
find, export to HTML — no Electron, no browser tab, ~2 MB of memory overhead instead of 200 MB.

**[⬇ Download the latest release](https://github.com/zzz281-cn/md-reader/releases/latest)** — one `.exe`, no installer, no Python required.

> 中文说明在下方 [简体中文](#简体中文)。

---

## Requirements

| | |
|---|---|
| OS | Windows 10 (1809+) or Windows 11, **64-bit** |
| Runtime | Microsoft Edge **WebView2** — preinstalled on Windows 11 and on most up-to-date Windows 10 |
| Disk | ~30 MB |
| Install | None. It's a single portable `.exe`. |

macOS and Linux are **not** supported. This is a Windows-only build.

## If it doesn't start

Please read this before opening an issue — 90% of "it just doesn't open" is one of these five.

### 1. Double-click does nothing, or the window is blank / all white

**WebView2 Runtime is missing.** The app renders its UI with the same engine Edge uses; if that
runtime isn't installed there is nothing to draw the window.

The app now detects this and shows a dialog with a download button. If you dismissed it, get it here:

- Official download: <https://developer.microsoft.com/microsoft-edge/webview2/>
  → *Evergreen Standalone Installer* → **x64** (~2 MB)

Install, then run `MdReader.exe` again. No reboot needed.

To check what you have, open `regedit` and look for:

```
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}
```

The `pv` value is the installed version. Missing key = not installed.

### 2. "Windows protected your PC" (blue SmartScreen box)

Expected. The `.exe` is not code-signed — a certificate costs a few hundred dollars a year, which a
free tool doesn't have. SmartScreen treats *any* unsigned exe downloaded from the internet this way.

Click **More info** → **Run anyway**.

If you'd rather verify before running: the build is reproducible — see
[Build from source](#build-from-source), or check the SHA-256 published with each release.

### 3. Antivirus deletes the file or quarantines it

PyInstaller-built executables get flagged by heuristic scanners fairly often, especially in China
(360, Huorong). This is a false positive caused by the self-extracting stub, not by anything the app does.

- Add the folder to your AV exclusions, then re-download.
- Or use the **portable (folder) build** from the release — a plain directory with `MdReader.exe` and
  a `_internal` folder. It unpacks nothing to `%TEMP%` at runtime, so it's flagged far less often.
- UPX compression is disabled in the official builds specifically to reduce false positives.

### 4. Windows on ARM (Snapdragon laptops)

Works through x64 emulation. First launch is slower; everything else is normal.

### 5. It opens but a `.md` file I dragged in can't be saved back

Known WebView2 limitation: files dropped onto the window don't expose a real filesystem path, so
saving asks you where to put it. Open the file via **Ctrl+O** or by passing it on the command line and
saving writes straight back to the original.

## Usage

| Key | Action |
|---|---|
| `Ctrl + O` | Open file(s) |
| `Ctrl + S` | Save (`Ctrl + Shift + S` = save as) |
| `Ctrl + E` | Toggle preview / edit |
| `Ctrl + F` | Find — `Enter` / `Shift+Enter` to jump |
| `Ctrl + W` | Close tab |
| `Esc` | Close the find bar |

- Drag files onto the window to open them.
- Pass files on the command line: `MdReader.exe notes.md todo.md`
- Saves preserve the original line endings (a CRLF file stays CRLF).
- Reads UTF-8 (with or without BOM) and falls back to GBK.

### Make it the default `.md` handler

Run `register-md.bat` (lives next to the exe — it locates the exe relative to itself, so the folder can
be anywhere). Then right-click any `.md` → **Open with** → **Choose another app** → **Markdown Document**
→ tick *Always use this app*.

It only writes `HKCU`, so no admin rights. To undo:
`reg delete "HKCU\Software\Classes\MarkdownReader.md" /f`

## Build from source

```
python -m pip install pywebview pillow pyinstaller
python app.py                                    # run from source
python -m PyInstaller MdReaderOne.spec --noconfirm --distpath dist-onefile
```

`MdReaderOne.spec` → single-file exe. `MdReader.spec` → portable folder build.

Regenerating the icon (any square PNG/JPG works):

```
python make_icon.py new-icon.png icon.ico
```

It punches the white corners out to transparent, crops to the artwork's real bounds with a 4% margin,
and emits 16/24/32/48/64/128/256 px. Look at the 256 px PNG it drops next to the `.ico`, and at how the
small sizes read on a light desktop — if the letterform isn't legible at 16 px, the source artwork is
too detailed.

## Known limitations

- Editing is plain Markdown source, not WYSIWYG.
- One window, multi-tab — no "open a second instance".
- The **AI polish** button is a placeholder; it isn't wired to a model.

## License

MIT — see [LICENSE](LICENSE).

---

## 简体中文

一个 Windows 上的 Markdown 阅读 / 编辑小工具。原生窗口、多标签、预览与源码双模式、查找、导出 HTML。
不用 Electron，内存占用比同类的网页套壳工具小一个数量级。

**[⬇ 下载最新版](https://github.com/zzz281-cn/md-reader/releases/latest)** ｜ 一个 `.exe`，免安装，不用装 Python。

### 系统要求

- Windows 10（1809 及以上）或 Windows 11，**64 位**
- **Microsoft Edge WebView2 运行时** —— Win11 自带，较新的 Win10 一般也有
- 约 30 MB 磁盘，不需要安装

**不支持 macOS 和 Linux**，这是 Windows 专用构建。

### 打不开？先看这五条

**① 双击没反应 / 窗口一片白**
缺 WebView2 运行时，界面就是用这个引擎画的。程序会自己弹框提示并给下载链接，也可以手动装：
<https://developer.microsoft.com/microsoft-edge/webview2/> → Evergreen Standalone Installer → **x64**（约 2 MB）。
装完直接重开，不用重启电脑。

**② 蓝色「Windows 已保护你的电脑」**
正常现象。exe 没有代码签名（证书一年几百美元），SmartScreen 对所有联网下载的未签名程序都这么弹。
点**更多信息** → **仍要运行**。

**③ 杀毒软件把文件删了 / 报毒**
PyInstaller 打包的程序被启发式引擎误报很常见（360、火绒尤其）。是自解压外壳触发的，不是程序行为。
把文件夹加白名单后重新下载；或者用 Release 里的**便携版（文件夹版）**——运行时不往 `%TEMP%` 解压，
误报率低得多。官方构建已经关掉 UPX 压缩，就是为了压误报。

**④ Windows ARM（骁龙本）**
走 x64 模拟，能用，首次启动慢一点。

**⑤ 拖进去的文件保存不回去**
WebView2 的限制：拖放进来的文件拿不到真实路径，所以保存时会让你选位置。用 `Ctrl+O` 打开或命令行传入的文件，保存是直接写回原文件的。

### 快捷键

`Ctrl+O` 打开 ｜ `Ctrl+S` 保存（`Ctrl+Shift+S` 另存为）｜ `Ctrl+E` 切换预览/编辑 ｜ `Ctrl+F` 查找 ｜ `Ctrl+W` 关标签 ｜ `Esc` 关查找条

### 设为 `.md` 默认打开方式

跑同目录下的 `register-md.bat`（它按自己所在位置找 exe，文件夹放哪都行），
然后右键任意 `.md` → 打开方式 → 选择其他应用 → **Markdown Document** → 勾选「始终使用」。

只写 `HKCU`，不需要管理员。撤销：`reg delete "HKCU\Software\Classes\MarkdownReader.md" /f`

### 已知限制

- 编辑是纯 Markdown 源码，不是所见即所得
- 单窗口多标签，没有做多实例
- 「AI 润色」按钮是占位，没接模型

### 许可

MIT
