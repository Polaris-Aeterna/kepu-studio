# AGENTS.md：在《{{NAME}}》项目里干活的规矩

给所有在这里工作的 agent：主 session、子 agent、并行的 worker。先读这一页。
- 流程和命令：插件技能 `kepu-studio:studio`。
- 为什么这么定：`LESSONS.md`，以及插件里的 `references/lessons.md`。
- 作者用中文交流，回复也用中文。

## 不可违反
1. **API key 不打印、不复制、不写进日志。** key 只在 `.env` 里，代码运行时自己读。
2. **花钱的操作先问。** ElevenLabs 合成、AI 视频都算。
   - 先 `./kepu voice <稿子> --dry`，说清字符数和余额，作者同意后再合成。
   - 作者在消息里明确要求的，算已批准。
3. **不替作者发布。** B 站、抖音、网盘都由作者上传；agent 只把发布文件夹准备好。
4. **旁白一个字都不能和稿子不同。** 改画面时不许顺手改旁白；要改台词，先改稿子，再重新配音。
5. **多音字不交给模型猜。**
   - `./kepu lint` 必须是 0 处拦下才能合成。
   - 读音以作者为准。作者定过的读音写进 `pron/lexicon.tsv` 或稿子里的 `字〔读音〕`，不靠记忆。
6. **并行时**：
   - 每个 worker 只写自己那一期的文件夹。
   - 共享的引擎、词典、样式只由一个人改，而且必须向后兼容。
   - 渲染两集两集地跑。
7. **没有 git 的项目**，大改之前先打包备份。

## 每期的关卡（必须过）
```bash
./kepu gate script/episodes/epNN.md            # script / voice / picture / release 四个阶段一张表；有 ✗ 就不往下走
./kepu gate script/episodes/epNN.md --final    # 发布前
```

## 作者报“X 读错了 / 字被挡住了”
先确认是哪一处：集、时间、整句、哪一个字、应该念什么。确认后按技能 `kepu-studio:fix` 的流程改，改完给作者一段新旧对照的试听或截图。
