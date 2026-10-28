"""从一个 git 标签打两个发布用的 zip（放在仓库的上一级目录）：

    python3 tools/build_release.py v0.2.1

  kepu-studio.zip         整个仓库（插件市场 + 插件 + 文档 + 例子）：解压后 claude plugin marketplace add ./kepu-studio
  kepu-studio-plugin.zip  只有插件本体：Claude 桌面版 / Cowork 的 Upload plugin 用

用 Python 的 zipfile 而不是 git archive：中文文件名（系列设定.md）带 UTF-8 标记，命令行 unzip 不会乱码；
可执行位按 git 里的记录写进去（双击解压仍可能丢掉，所以 kepu init 会再补一次）。
"""
from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def files_at(tag: str) -> list[tuple[str, bytes, int]]:
    tar = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", tag], capture_output=True, check=True).stdout
    out = []
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        for m in t.getmembers():
            if m.isfile():
                out.append((m.name, t.extractfile(m).read(), m.mode))
    return sorted(out)


def write_zip(path: Path, items, strip: str = "") -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data, mode in items:
            if strip and not name.startswith(strip):
                continue
            zi = zipfile.ZipInfo("kepu-studio/" + name[len(strip):], date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3                                  # unix: keep the permission bits
            zi.external_attr = ((0o755 if mode & 0o111 else 0o644) | 0o100000) << 16
            z.writestr(zi, data)
    print(f"{path}  {path.stat().st_size / 1e6:.2f} MB")


def main(tag: str) -> int:
    items = files_at(tag)
    write_zip(REPO.parent / "kepu-studio.zip", items)
    write_zip(REPO.parent / "kepu-studio-plugin.zip", items, strip="kepu-studio/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "HEAD"))
