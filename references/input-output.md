# Input and output contract

## Accepted input

Accept any combination of:

- pasted plain text;
- multiple Telegram Desktop HTML files from one or more exported chats;
- Telegram Desktop JSON;
- TXT, CSV, MD, or LOG text files.

MissAV, Twitter, Bad.news, and Haijiao all accept the same containers above; do not require a separate file type for a particular tool. One file can be run through multiple selected tools, with each tool applying its own extraction and review rules.

For HTML, read visible message text, links, dates, message IDs, and the export chat title. For JSON, support the official message/text-array shape and preserve the explicit chat/container identity when present. For plain text, create a transient source identity from the input label and a content hash; do not pretend it is a Telegram chat.

## Preview and selection

Preview must report file count, parsed count, included/excluded-by-time count, source count, and parsing errors. Date filtering is inclusive at minute precision for user-facing values; messages without a date remain included unless the host explicitly documents another policy.

Display each source independently with its title, kind, count, stable key, and current bound tools. The user can search/filter messages and select individual messages, the current filtered set, or all preview messages. A missing binding for a selected source blocks processing before any database write.

Multipart HTML files from the same exported chat merge by a stable chat/export key. Do not merge files merely because their filenames look similar.

## Message identity and transient privacy

For connected Telegram sources, use `account_id + chat_id + message_id`. For official exports use the strongest available export-chat key plus message ID. For pasted text, use the source label plus deterministic content index/hash. A content edit updates the same identity; it is not a new message.

Raw text is transient. It may appear in the current preview and in the response only when the user asks for a copyable excerpt. It must not enter permanent history, logs, backups, result packages, rule packages, or telemetry.

## Result shape

Every derived row should carry:

```json
{
  "tool": "missav | twitter | badnews | haijiao | av123",
  "canonical_key": "stable tool-specific key",
  "primary_value": "code, creator, or URL",
  "secondary_value": "detail/profile URL when applicable",
  "source_key": "transient or connected source identity",
  "rule_version": "immutable version identifier",
  "status": "new | duplicate | historical | invalid | review | error | excluded",
  "reason": "short machine-readable reason"
}
```

The response must separate primary and secondary lists, preserve order, and state counts. A result is not “new” merely because it came from a new file; compare its canonical key against permanent history.

## Generated files

- TXT: UTF-8, one value per line, no explanatory header in copy-ready lists.
- CSV: UTF-8 with a header, quoted cells, and formula-injection protection for cells beginning with `=`, `+`, `-`, or `@`.
- JSON: versioned envelope with counts, rule version, source summary, and rows; never raw message body.
- MissAV script: validated template plus escaped injected code/tag blocks.
- Raindrop HTML: escaped title/URL/tags, the three fixed folders, and an exclusion report for second-layer blacklist hits.
- Result/history/rule packages: manifest version, created time, record count, SHA-256, rule version, and conflict-safe import preview.
