版本 {{VERSION}} —— 单文件绿色版，免安装，不用装 Python。

## 下载哪个

| 文件 | 说明 |
|---|---|
| **MdReader-{{VERSION}}-win-x64.zip** | 单文件 exe（约 16 MB），解压到任意位置双击 `MdReader.exe` |
| **MdReader-{{VERSION}}-win-x64-portable.zip** | 文件夹版。杀软拦单文件版时用这个，它运行时不往 `%TEMP%` 解压 |

仅支持 Windows 10 / 11，64 位。

## 打不开先看这里

1. **窗口一片白，或双击没反应** —— 缺 Microsoft Edge **WebView2** 运行时。Win11 和较新的 Win10 自带；
   缺失时程序会弹框并给下载按钮。手动装：<https://developer.microsoft.com/microsoft-edge/webview2/>
   → **Evergreen Standalone Installer** → **x64**（约 2 MB），装完不用重启。
2. **「Windows 已保护你的电脑」** —— 正常。exe 没有代码签名。点**更多信息** → **仍要运行**。
3. **杀软报毒或直接删文件** —— PyInstaller 打包的常见误报。把文件夹加白名单，或改用便携版。

## 校验和（SHA-256）

```
{{SHA_SINGLE}}  MdReader-{{VERSION}}-win-x64.zip
{{SHA_PORTABLE}}  MdReader-{{VERSION}}-win-x64-portable.zip
```

## 已知限制

- 编辑是纯 Markdown 源码，不是所见即所得
- 拖进窗口的文件保存不回去（WebView2 限制），改用 `Ctrl+O` 打开
- 「AI 润色」按钮是占位，没接模型

完整说明见 [README](https://github.com/zzz281-cn/md-reader#readme)。
