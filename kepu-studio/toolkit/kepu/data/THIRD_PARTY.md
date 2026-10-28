# 第三方数据

- `words.tsv.gz`：由 `toolkit/tools/build_data.py` 生成。
  - 词与词频来自 jieba 的 `dict.txt`（https://github.com/fxsjy/jieba，MIT License）。
  - 词的读音来自 pypinyin 的词组拼音库（https://github.com/mozillazg/python-pypinyin，MIT License，词组数据源自 phrase-pinyin-data，MIT License）。
- `char_readings.tsv`：单字读音，来自 pypinyin（MIT License）。

这些数据只用来**发现**读音风险（分词陷阱、非默认读音），不直接决定读音：pypinyin 在不少理工科词上是错的（方差 chà、相变 xiāng、似然 shì、切线 qiè、背包 bēi、用处 chǔ），决定以 `lexicon.tsv` 和规则为准。
