# -*- coding: utf-8 -*-
"""把 tag 版本号写进 exe 的版本资源。

否则每个 Release 的 exe 右键属性里都写着 1.0.0.0，用户在设置里排查版本时没法区分。
只改 version_info.txt 里的四处（filevers / prodvers / FileVersion / ProductVersion），
CI 里跑，改完就打进 exe，不提交回仓库。

用法：
    python stamp_version.py v1.2.3
    python stamp_version.py 1.2.3.4
    python stamp_version.py dev-abc1234      # 不认识就原样跳过
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "version_info.txt")

SEMVER = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def main(argv):
    raw = argv[1].strip() if len(argv) > 1 else ""
    match = SEMVER.match(raw)
    if not match:
        # 输出一律走 ASCII：GitHub Actions 的 Windows runner 控制台是 cp1252，
        # print 中文会直接抛 UnicodeEncodeError 把构建打挂。
        print("skip: %r is not a x.y[.z[.w]] version, version_info.txt left untouched" % raw)
        return 0

    parts = [int(g) if g else 0 for g in match.groups()]
    quad = "(%d, %d, %d, %d)" % tuple(parts)
    dotted = "%d.%d.%d.%d" % tuple(parts)

    with open(TARGET, encoding="utf-8") as fh:
        src = fh.read()

    before = src
    src = re.sub(r"filevers=\([^)]*\)", "filevers=" + quad, src)
    src = re.sub(r"prodvers=\([^)]*\)", "prodvers=" + quad, src)
    src = re.sub(r"(StringStruct\(u'FileVersion',\s*u')[^']*(')",
                 r"\g<1>" + dotted + r"\g<2>", src)
    src = re.sub(r"(StringStruct\(u'ProductVersion',\s*u')[^']*(')",
                 r"\g<1>" + dotted + r"\g<2>", src)

    if src == before:
        print("ERROR: no version fields matched in version_info.txt, check its format")
        return 1

    with open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    print("version resource set to %s %s" % (dotted, quad))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
