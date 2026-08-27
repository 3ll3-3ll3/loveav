# Curated library contract

这是本地 Skill 的精选资料库，不是所有处理记录的归档。每次处理得到的候选先停留在预览中，只有用户明确选择“保留/入库”的行才写入。

## 文件布局

建议把个人数据放在 Skill 目录外的 `loveav-data/`；如果必须随 Skill 携带，也应使用被 `.gitignore` 排除的 `user-data/`：

```text
loveav-data/
├─ library/
│  ├─ curated-results.csv       # 权威精选记录
│  └─ missav-codes.csv          # 可选的 MissAV 便携视图
├─ rules/
│  ├─ reference-tags.txt
│  ├─ reference-blacklist.csv
│  ├─ raindrop-export-blacklist.csv
│  ├─ rule-suggestions.csv    # 待用户确认的未知格式建议
│  └─ learned-rules.csv       # 已确认并带回归样本的新增规则
├─ indexes/
│  ├─ history-index.csv         # 从 curated-results.csv 生成，不手工编辑
│  └─ seen-index.csv            # 旧库/历史输入已见身份，可含待复核项
├─ exports/
└─ backups/
```

## 精选记录格式

```csv
tool,canonical_key,primary_value,secondary_value,tags,folder,first_seen_at,last_seen_at,seen_count,rule_version,status,notes
missav,ABCD123,ABCD-123,https://missav.ai/...,女优甲|女优乙,参考女优Tag命中,2026-08-27T10:00:00Z,2026-08-27T10:00:00Z,1,v1,active,
```

约束：

- `tool + canonical_key` 唯一；同一番号不同 URL 不产生第二行。
- `tags` 使用明确分隔符，不把逗号含义混入 CSV；导出时按工具规则拆分。
- `folder` 只记录用户最终选择的归类，不参与番号去重。
- `status` 建议使用 `active`、`removed`、`review`；移除保留墓碑和原因。
- 所有写入使用 UTF-8、带表头、正确引用字段，并防止 CSV 公式注入。

## 黑名单格式

黑名单不要混在精选库里。建议每层独立 CSV：

```csv
pattern,match_type,enabled,note
某女优,exact_tag,1,
```

`reference-blacklist.csv` 只取消参考女优 Tag 的命中资格，不能删除精选番号；`raindrop-export-blacklist.csv` 命中时只阻止该结果进入 Raindrop 导出，保留记录和排除原因。若需要屏蔽具体番号/链接，另建 `exact-exclude.csv`，不要伪装成女优 Tag 黑名单。

## 入库与查重

1. 处理当前输入并生成候选预览。
2. 在预览中分开显示：本次重复、精选库已有、黑名单排除、无效、待确认和可入库。
3. 用户只勾选要保留的行并确认。
4. 写入前校验表头、唯一键、规则版本和 CSV 编码；先创建备份。
5. 原子更新 `curated-results.csv`，再生成 `history-index.csv` 和对应工具视图；`seen-index.csv` 可单独保留已见但未精选的身份。
6. 记录最小元数据（时间、来源文件哈希、规则版本、数量），不保存原始 Telegram 正文。

未勾选的候选不会被当作精选历史；如果它们出现在 `seen-index.csv`，下一次只提示“以前见过但未精选”，不自动过滤。只有明确入库的行才会被视为历史。

## 规则与库的关系

- 参考女优 Tag 库：用于判断 MissAV 是否命中参考人物。
- 第一层黑名单：从参考命中计算中排除 Tag，但不删除精选结果。
- 第二层黑名单：阻止 Raindrop 导出，不删除精选结果。
- `rule-suggestions.csv`：保存待复核的未知格式，不直接参与正式过滤。
- `learned-rules.csv`：只保存用户确认、带正负回归样本且已版本化的新增规则。
- 精选结果库：用于未来历史查重和用户自己的参考样本。
- 精选库不反向修改规则，除非用户明确要求“把这些 Tag 加入规则”。
