# -*- coding: utf-8 -*-
"""从 exe 里取出 Windows 实际会渲染的那个图标，存成 PNG 用来看。

纯 ctypes，不依赖 pywin32：
  ExtractIconExW 拿 HICON -> DrawIconEx 画到 32bpp DIB -> 读像素
"""
import ctypes
import sys
from ctypes import byref, c_void_p, sizeof
from ctypes import wintypes as w

from PIL import Image

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG),
        ("biPlanes", w.WORD), ("biBitCount", w.WORD), ("biCompression", w.DWORD),
        ("biSizeImage", w.DWORD), ("biXPelsPerMeter", w.LONG),
        ("biYPelsPerMeter", w.LONG), ("biClrUsed", w.DWORD), ("biClrImportant", w.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", w.DWORD * 3)]


def grab(exe, size=64, out="hicon.png"):
    large = (w.HICON * 1)()
    small = (w.HICON * 1)()
    got = shell32.ExtractIconExW(exe, 0, large, small, 1)
    if got <= 0 or not large[0]:
        raise RuntimeError("ExtractIconExW 没取到图标 (return=%r)" % got)

    bi = BITMAPINFO()
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = size
    bi.bmiHeader.biHeight = -size          # 负数 = 自上而下，省得翻转
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    bi.bmiHeader.biCompression = 0         # BI_RGB

    bits = c_void_p()
    hbm = gdi32.CreateDIBSection(None, byref(bi), 0, byref(bits), None, 0)
    if not hbm:
        raise RuntimeError("CreateDIBSection 失败")

    # 先铺一层中灰，透明处才看得见（图标四角是抠掉的）
    mdc = gdi32.CreateCompatibleDC(None)
    gdi32.SelectObject(mdc, hbm)
    brush = gdi32.CreateSolidBrush(0x00C8C8C8)   # BGR
    rect = w.RECT(0, 0, size, size)
    user32.FillRect(mdc, byref(rect), brush)

    user32.DrawIconEx(mdc, 0, 0, large[0], size, size, 0, None, 0x0003)  # DI_NORMAL

    buf = ctypes.string_at(bits, size * size * 4)
    img = Image.frombuffer("RGBA", (size, size), buf, "raw", "BGRA", 0, 1)
    out_img = Image.new("RGB", img.size, (200, 200, 200))
    out_img.paste(img, (0, 0), img)
    out_img.save(out)

    gdi32.DeleteObject(brush)
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(mdc)
    user32.DestroyIcon(large[0])
    return out


if __name__ == "__main__":
    exe = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "hicon.png"
    print("已写出:", grab(exe, 64, out))
