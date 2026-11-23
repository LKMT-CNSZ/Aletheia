# 构建 Aletheia 3.2.0

使用 Windows x64 和 Python 3.11+。build/compat-dependencies.json 记录官方便携运行时及各 wheel 的版本、下载地址和 SHA256。构建工具会校验 build/wheels 中的下载文件。安装编译器可用 tools/fetch_installer.ps1 准备。

    python tools/fetch_compat.py --locked --proxy ""
    python THIRD_PARTY/libraw-202611/build_nikon_he.py --support-dir raw_support
    python tools/build_compat.py
    python tools/package_aletheia.py --iscc "C:/Program Files (x86)/Inno Setup 6/ISCC.exe"

用 x64 MSVC 开发者命令行运行 Nikon HE 解码桥的构建步骤。源码和 LGPL 许可保存在 THIRD_PARTY/libraw-202611。

免安装版目录为 dist/3.2.0-compat/Aletheia。打包器按文件清单读取文件，输出至 release。实拍示意图在 tools/installer-assets。

使用随包运行时执行 runtime\python.exe -I -m film_invert_launcher --diagnose 可验证文件、依赖、Qt 主窗口和合成样片。
