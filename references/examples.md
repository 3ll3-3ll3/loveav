# Natural-language examples

These examples show response shape, not mandatory wording.

## Manual MissAV + Twitter

User:

```text
使用 LoveAV 处理我上传的三个 Telegram HTML。
MissAV 来源提取番号，推特来源提取博主；排除永久历史，返回番号、番号链接、博主名和主页链接。
```

Skill behavior:

1. Preview all files and show recognized sources/counts.
2. Ask only about an unbound or ambiguous source.
3. Process the selected sources with the current rule version.
4. Return four separate copy-ready lists and counts for new, historical, duplicate, invalid, and errors.

## Rule administration

```text
把这个 Miss_AV.html 导入为新的参考女优 Tag 库，并把两层黑名单分别预览。
```

Preview extracted tags, duplicates, removed boundary tags, and blacklist effects. Commit only after the user confirms; create a new immutable rule version and refresh the editable TXT mirrors.

## Data lookup

```text
查找所有包含 ABF 的 MissAV 结果，只返回番号，一行一个。
```

Call a filtered result query, exclude deleted rows, and return a plain-text block with no bullets or commentary inside the block.

## Same containers, adaptive review

```text
用 LoveAV 处理这个 CSV，运行 MissAV、Twitter、Bad.news 和海角；不要把不确定的格式直接丢掉，列出可疑项并说明证据。
```

Run all four selected tools over the same input container. Return accepted, clearly excluded, `review`, and error counts separately. For a new candidate shape, show the smallest confirmation question and create a rule suggestion only; do not silently activate a learned rule.

## Legacy opt-in

```text
使用已经配置好的个人 Telegram 适配器，读取“番号群”今天 09:00 之后的新消息，但先只生成预览，不要标记已读。
```

Check adapter capability and secure-store status, preview the source/time range, and stop before any read-marking or other remote side effect. If the adapter is absent, explain that manual export upload is the available path.

## Whos.tv increment

```text
接着上次记录抓到今天最新。
```

Read `whostv-state.json`, generate the incremental console script using `/helps/10250`, prepend it to `whostv_scripts.md`, and report the generated `.js` path and expected JSON name. Do not update the cutoff until the returned JSON passes the deterministic organizer.

## Whos.tv returned JSON

```text
整理 whos_tv_solved_answers_since_2026-08-27.json。
```

Run the organizer. If count, pages, answers, URLs, cutoff, and ordering all pass, write the Asia/Shanghai date-named Markdown, report four category counts and pure-code count, then advance the cutoff to the first entry's pathname.
