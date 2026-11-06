# -*- coding: utf-8 -*-
"""把一张方形 PNG/JPG 转成 Windows 多尺寸 .ico（四角白底自动抠透明）。

用法：
    python make_icon.py <源图> [输出.ico]

要点：
1. 源图四角是白色 paper，Windows 桌面若是白底不透明，图标会变成一个白方块，
   所以从四个角 floodfill 把连通的白抠成透明。容差压小，避免渗进书页的白。
2. ico 内含 16/24/32/48/64/128/256 七档，256 走 PNG 压缩（Vista 以后支持）。
3. 缩放用 LANCZOS，小尺寸（16/24）额外做一点锐化，否则 M 字糊成一团。
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SIZES = [16, 24, 32, 48, 64, 128, 256]
CORNER_TOL = 24          # floodfill 容差：JPEG 白区有噪点，但别大到吃掉书页
PADDING = 0.04           # 裁切后四周留白（满幅的圆角卡片在桌面上会显得比邻居大一圈）


def cut_corners(im):
    """从四角把连通的白抠透明，返回 RGBA。"""
    im = im.convert("RGBA")
    w, h = im.size
    for xy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(im, xy, (0, 0, 0, 0), thresh=CORNER_TOL)
    return im


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "icon.ico")

    im = Image.open(src)
    print("源图: %s  %s  %s" % (src, im.size, im.mode))
    im = cut_corners(im)

    alpha = im.getchannel("A")
    nz = alpha.getbbox()
    if not nz:
        print("!! 抠完什么都不剩了，检查源图")
        return 2
    hit = sum(1 for p in alpha.get_flattened_data() if p == 0) if hasattr(
        alpha, "get_flattened_data") else sum(1 for p in alpha.getdata() if p == 0)
    ratio = hit / float(im.size[0] * im.size[1])
    print("抠掉的外围白边: %.2f%% 像素" % (ratio * 100))
    print("内容 bbox: %s" % (nz,))

    # 裁到内容，再居中放进带内边距的正方形画布。
    # 原图的白色外边其实很宽（左右各 57px、上 52 下 68，上下不对称），
    # 直接缩放会让图形偏下且顶到边，这里统一成对称留白。
    im = im.crop(nz)
    cw, ch = im.size
    side = int(max(cw, ch) / (1 - 2 * PADDING))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - cw) // 2, (side - ch) // 2), im)
    im = canvas
    print("裁切居中后: %dx%d，四周留白 %.0f%%" % (side, side, PADDING * 100))

    im.save(dst, format="ICO", sizes=[(s, s) for s in SIZES])
    print("已写出: %s  (%d 档: %s)" % (dst, len(SIZES), "/".join(map(str, SIZES))))

    # 顺手导出 256 PNG，方便预览和给 README 用
    png = os.path.splitext(dst)[0] + "-256.png"
    im.resize((256, 256), Image.LANCZOS).save(png)
    print("预览 PNG: %s" % png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
