# v0.5.13 功能对照

本表用于防止迁移时漏掉旧版能力。当前项目只启用离线手动输入、精选库和确定性输出；联网账号操作列为历史兼容参考，不属于当前范围。

| v0.5.13 能力 | Skill 中的位置 | 是否需要宿主适配器 |
| --- | --- | --- |
| MissAV 番号、详情链接、规范化 | `tool-rules.md` | 否；规则可直接运行 |
| MissAV 浏览器脚本生成 | `tool-rules.md`、`input-output.md` | 生成否；执行脚本需要浏览器宿主 |
| 参考女优 Tag HTML 提取 | `tool-rules.md`、`data-contract.md` | 解析否；保存新版本需要数据写入 |
| 第一层参考 Tag 黑名单 | `tool-rules.md` | 否 |
| 第二层 Raindrop 导出黑名单 | `tool-rules.md` | 否 |
| 三个 Raindrop 输出文件夹 | `tool-rules.md`、`input-output.md` | 文件生成否；远端写入不包含在 Skill |
| Twitter 博主名与主页链接 | `tool-rules.md` | 否 |
| Bad.news 直达帖链接 | `tool-rules.md` | 否 |
| 海角直达帖链接 | `tool-rules.md` | 否 |
| Telegram HTML/JSON/TXT/粘贴输入 | `input-output.md` | 文件上传由宿主提供 |
| 多文件、时间范围、消息多选 | `input-output.md` | UI/文件选择由宿主提供 |
| 永久历史查重与编辑/删除语义 | `data-contract.md` | 需要持久化适配器才能跨会话保存 |
| 任务、结果、规则、历史包 | `input-output.md`、`data-contract.md` | 下载/导入由宿主提供 |
| 精选库增删改、备份、恢复 | `curated-library.md`、`data-contract.md` | 需要本地文件/小型库适配器 |
| v0.5.13 业务库迁移 | `data-contract.md` | 需要一次性的本地迁移适配器 |
| 个人 Telegram API 登录、历史、增量 | `legacy-parity.md` | 必须使用安全 MTProto 适配器 |
| Bot 更新、offset、来源分发 | `legacy-parity.md` | 必须使用 Bot 适配器 |
| 编辑/删除传播、检查点、手动标已读 | `legacy-parity.md` | 必须使用 Telegram 适配器 |
| 123AV 精确查询 | `legacy-parity.md`、`tool-rules.md` | 需要网站/浏览器适配器 |
| 123AV 收藏/关注三种方式 | `tool-rules.md` | 需要 Chrome 或串行执行器 |

不属于 Skill 的内容：正式数据库、原始 Telegram 消息归档、认证信息、浏览器登录态、自动后台服务和任何未确认的远程写操作。
