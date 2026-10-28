"""kepu：动漫 / 动画 / 游戏风中文科普视频的工作流工具（kepu-studio 插件的 Python 部分）。

    python -m kepu --help

只依赖 Python 3.9+ 标准库；音频相关的命令需要 ffmpeg。读音引擎用自带的词表（data/words.tsv.gz，
由 jieba 与 pypinyin 的词典生成，MIT 许可，见 data/THIRD_PARTY.md），不需要安装 jieba / pypinyin。
"""
__version__ = "0.2.0"
