# -*- mode: python ; coding: utf-8 -*-
# 单文件版：一个 exe 拷走就能跑。
# upx=False 是有意的：UPX 压过的 PyInstaller 产物是杀软误报的重灾区，
# 为省几 MB 换来「下载完直接被删」不值。体积 ~25 MB，换双击不报毒。
#
# 产物名用 ASCII 的 MdReader.exe：中文文件名在浏览器下载、邮件附件、
# 某些解压工具里会乱码，GitHub Release 的 zip 里也不该出现。

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[('ui', 'ui')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MdReader',
    icon='icon.ico',
    version='version_info.txt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
