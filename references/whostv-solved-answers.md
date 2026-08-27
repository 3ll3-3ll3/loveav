# Whos.tv 已解决答案

第五个主功能处理 whos.tv 求助社区的“已解决”答案。它与 MissAV、Twitter、Bad.news、海角相互独立，不进入精选番号库，除非用户之后明确选择其中的番号入库。

## 固定目录与状态

- 工作目录：`C:\Users\WJL\Desktop\windows\杂记\secret\beauty\whostv`
- 脚本归档：`whostv_scripts.md`
- 整理器：Skill 内的 `scripts/organize_whos_answers.js`
- 当前状态：`references/whostv-state.json`
- 最终文档：按 `Asia/Shanghai` 当天日期命名，例如 `2026-08-27.md`
- 不生成分类 JSON。

当前截止帖是 `/helps/10250`。`/helps/6270` 仅是旧历史截止点，不得用于新的增量抓取。每次成功校验和整理一批新 JSON 后，将第一条记录 URL 的 pathname 写为新截止点；如果它的帖子编号比现有截止点更旧，则不得倒退状态。

## 抓取流程

用户要求“前 n 页”或“第 1-n 页”时，调用：

```powershell
node scripts/generate_whostv_scraper.js --pages n
```

用户要求“接着上次记录抓到今天最新”时，调用：

```powershell
node scripts/generate_whostv_scraper.js --incremental
```

生成器把独立 `.js` 和完整脚本说明追加到固定目录的 `whostv_scripts.md` 最前面。脚本必须由用户在 whos.tv 已解决列表页面的控制台运行。用户明确要求控制 Chrome 时，可先检查可见账户菜单与“登出”；未确认登录就停止。若安全策略不允许代理运行控制台脚本，交付生成的脚本让用户手动运行，不使用 `javascript:` URL、原始 CDP 或规避手段。

抓取脚本必须：

- 校验 `location.hostname` 是 `whos.tv` 或其子域；
- 通过当前已解决列表 URL修改 `page` 查询参数，不猜测另一个站点路径；
- 使用 `credentials: "include"`、`cache: "no-store"` 和页间延时；
- 首选 `article[data-help-id], article[data-post-href]`；
- 首选 `[data-post-answer-preview] p`，旧“答案：”结构只作回退；
- 保留答案内真正的 http/https 链接；
- 在 0 条、空答案、HTTP 失败、重复 URL 或增量未找到截止帖时抛错且不下载文件；
- 增量结果不包含截止帖；结果按最新到较旧顺序排列。

## JSON 校验与整理

收到 `whos_tv_solved_answers*.json` 后运行：

```powershell
node scripts/organize_whos_answers.js <JSON路径>
```

整理器接受普通数组，或带 `entries` 的对象。对象必须有与 `entries.length` 相等的 `count`。它验证必需字段、连续页码、空答案、重复 URL和增量截止点，并输出总数、页码范围、第一条、最后一条、空答案数和重复数；任一校验失败都不生成最终 Markdown，也不更新状态。

## 四类输出

先从答案中移除 http/https URL，再识别番号。`magnet:` 和 `ed2k:` 不算访问链接。支持 `ABC-123`、`FC2-PPV-123456`、`FC2 PPV 123456`、`030515-821`、`4149-PPV043` 等形式。

分类固定为：

1. 答案只有番号的：有番号，无 http/https URL；
2. 答案只有访问链接的：有 http/https URL，无番号；
3. 答案同时有番号和访问链接的：两者都有；
4. 其他内容：两者都没有。

Markdown 开头是“答案只有番号的”分类中提取出的纯番号列表，大小写不敏感去重且保留首次顺序。随后一级标题顺序固定为：答案只有访问链接的、其他内容、答案同时有番号和访问链接的、答案只有番号的。最后一类不重复展开答案，只说明已收录于开头。其余每条包含二级标题、来源 URL、页码和保留多行的引用块。
