# LoveAV

这是面向桌面 Codex 及其他兼容 AI 工具的本地优先可复用 Skill。Skill 是产品主体；本目录默认不保存 Telegram 原文、数据库、Token、Session 或浏览器资料。

## 使用

1. 将整个 `loveav` 文件夹作为 Skill 安装或上传。
2. 在对话中使用 `$loveav`，上传 Telegram Desktop 的 HTML/JSON、TXT/CSV/MD/LOG，或直接粘贴文本。
3. 说明要运行的工具、时间范围、是否排除精选库已有记录和需要的输出。默认只做本地/对话内解析，不连接 Telegram。
4. 预览完成后，只勾选你要长期保留的结果入库；未选择的候选不会进入历史查重库。

如需从 v0.5.13 旧库初始化，可运行 `scripts/migrate_v0513_library.py`。它只读打开旧 SQLite，生成 `seen-index.csv`、精选候选、待复核候选、女优 Tag 候选和旧 Raindrop 元数据；默认不会生成正式精选库。只有你明确确认后，才使用 `--activate-ok` 激活 `status=ok` 的候选。

## 包含的 5.13 能力

- MissAV、Twitter、Bad.news、海角四个确定性过滤器。
- MissAV 番号规范化、详情链接、浏览器脚本、参考女优 Tag、两层黑名单和三目录 Raindrop 导出。
- Telegram Desktop HTML/JSON、多文件、粘贴文本、时间筛选、选择、查重和历史语义。
- 精选结果库、查重索引、规则包，TXT/CSV/JSON 输出，以及 v0.5.13 业务数据迁移契约。
- Whos.tv 已解决答案：控制台抓取脚本、增量截止点、JSON 校验、四类 Markdown 和脚本归档。
- 123AV 的番号解析、页面证据和导出规则；收藏/关注等账号操作不启用。
- Telegram Desktop 文件解析、消息规范化和时间筛选；个人 API、Bot、历史回拉、检查点和标记已读不启用。

详细规则位于 `references/`。精选资料库契约见 `references/curated-library.md`。Skill 只决定流程、规则和输出；本版本不包含 Telegram、Work/cloud 或远程账号执行器。

## 版本与边界

规则基线：Windows `missav-manager` v0.5.13（稳定提交 `4e2aad0`）。123AV 和 Telegram 的联网部分仅作为兼容参考，不属于当前启用范围；当前默认不联网、不自动标记已读、不直写 Raindrop。

当前五个主功能是：MissAV、Twitter、Bad.news、海角、Whos.tv 已解决答案。
