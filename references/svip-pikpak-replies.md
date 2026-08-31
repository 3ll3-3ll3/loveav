# Svip 官方 PikPak 资源回复

本工作流是 LoveAV 对本机 `tgctl` 的一个**窄范围、只读、确定性**适配。它不改变 TG Exporter 的 `--sender-role admin` 语义，也不修改 GUI、daemon、Session、普通导出或普通读取路径。

## 启用条件

只有当用户明确提出 Svip 官方 PikPak 资源回复类请求时启用，例如：

- `读取Svip最近1000条官方PikPak回复`
- `提取Svip本月管理员资源链接`
- `复核Svip可疑PikPak回复`

其他 LoveAV 请求仍保持 Manual 默认模式。

## 本地私有配置

Svip 的真实 `chat_id` 只保存在本机私有配置：

`loveav-data/svip-resource-replies.json`

结构：

```json
{
  "bindings": {
    "Svip": {
      "chat_id": "<本机填写非零整数>"
    }
  },
  "tgctl_path": "<可选：tgctl.exe 的本机路径>"
}
```

上面的占位符只是说明，不是可直接运行的配置。真实 `chat_id`、Session、API Hash、手机号、验证码、2FA、代理凭据都不得提交到公开仓库。`loveav-data/` 已被 `.gitignore` 排除。

## 数据来源

首选：

```powershell
python scripts/filter_svip_resource_replies.py --run-tgctl --limit 1000 --pretty
```

脚本只调用只读历史接口，先取得“最近 N 条真实消息”，再在本地做 URL 与身份分类：

```text
tgctl messages history --chat <exact-chat-id> --limit ... --json
```

必要时使用 cursor 分页，单页最多 500。这样“最近1000条”严格表示最近 1000 条 Svip 消息，而不是最近 1000 条已命中链接的消息。脚本不会加入 `--sender-role` 或 `--url-domain`，不会调用 `send`、`forward`、`media download`，不会访问 PikPak 链接；域名匹配完全在本地完成。

也可以对已经保存的 tgctl `--json` / `--jsonl` 结构化输出离线分类：

```powershell
python scripts/filter_svip_resource_replies.py --input .\svip-page.json --pretty
```

离线输入仍必须读取本地 Svip 绑定，并只接受 `message.chat_id == bindings.Svip.chat_id` 的消息。

## URL 规则

分类脚本从 tgctl 消息结构中的 `entities[].url`、`text` 和 `caption` 提取 URL，然后用 `urllib.parse.urlsplit` 解析 hostname，并进行本地 IDNA 规范化。

只接受：

- `mypikpak.com`
- `*.mypikpak.com`

明确拒绝：

- `mypikpak.com.evil.com`
- `notmypikpak.com`

不请求 URL、不做 HEAD/GET、不使用网页标题、重定向、正文署名或昵称作为身份依据。

## 确定性分类

### `verified_moderator`

只有 Telegram/tgctl 结构化字段明确给出以下任一证据时进入：

- `sender.is_creator is true`
- `sender.is_admin is true`
- `sender_type == anonymous_admin` 且 `anonymous_admin == true`
- `posted_as_chat_id == 当前 Svip chat_id`，且 sender peer 类型是 chat/channel/anonymous_admin

不根据昵称、正文署名或 `forward_origin` 猜管理员。

### `excluded_known_member`

当 sender 是明确 `user`，并且当前角色快照同时给出：

- `is_creator == false`
- `is_admin == false`

即视为已知普通成员。即使消息含 PikPak 链接，也从主结果排除，并在摘要中单独报告数量。

### `trusted_official_reply`

仅当：

- `sender_type == unknown`
- `unknown_reason == telegram_sender_not_provided`
- 同时存在 `reply_to_message_id`
- 且 `media.media_type == photo` 或存在 `photo_id`

才进入高可信主结果。

### `needs_review`

包括：

- `telegram_sender_not_provided` 但只有“回复”或“图片”之一；
- `forwarded_message_without_actual_sender`；
- 其他存在 PikPak URL、但 sender 证据不足以自动信任或明确排除的情况。

转发来源永远不会升级 actual sender。

### `excluded_insufficient_evidence`

当 `telegram_sender_not_provided` 且既没有回复关系，也没有图片时排除。

## 输出契约

默认 JSON：

- `primary`: `verified_moderator` + `trusted_official_reply`
- `needs_review`: 单独输出
- `summary.excluded_known_member_count`: 已知普通成员排除数
- `summary.excluded_insufficient_evidence_count`: 证据不足排除数

每个输出记录至少包含：

```text
message_id
date
pikpak_url
classification
evidence
```

脚本不生成、补全或猜测 `sender_id`；默认记录中不输出 `sender_id`。

`evidence` 只记录 tgctl 结构化字段和本地可重复判断，例如 `is_admin`、`anonymous_admin`、`posted_as_current_chat`、`unknown_reason`、回复/图片存在性及解析后的 PikPak hostname。

## 自然语言映射

### 读取Svip最近1000条官方PikPak回复

运行：

```powershell
python scripts/filter_svip_resource_replies.py --run-tgctl --limit 1000 --pretty
```

返回 `primary`、`needs_review` 和排除统计。

### 提取Svip本月管理员资源链接

由 Skill 用用户本地时区计算本月 `[since, until)`，传给 tgctl，并只显示 `verified_moderator`：

```powershell
python scripts/filter_svip_resource_replies.py --run-tgctl --limit 5000 --since <month-start> --until <next-month-start> --classification verified_moderator --pretty
```

### 复核Svip可疑PikPak回复

```powershell
python scripts/filter_svip_resource_replies.py --run-tgctl --limit 1000 --view review --pretty
```

只展示 `needs_review`，仍保留完整摘要用于解释。

## 验收解释

真实 Svip 最近 1000 条的经验目标约为：

- 主结果约 101 条高可信隐藏/官方回复；
- 约 2 条 `needs_review`；
- 约 1 条 `excluded_known_member`。

这些数字不是代码常量，也不是测试断言；Telegram 新消息会改变数量。验收依据是每条 `classification` 与 `evidence` 是否满足上述确定性规则。
