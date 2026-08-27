# v0.5.13 parity reference (disabled network adapters)

The Skill carries the reusable user-facing behavior of the stable Windows v0.5.13 product. This version intentionally does not activate Telegram connections, cloud execution, background queues, or 123AV account actions. The entries below prevent future migrations from forgetting old behavior; they are not permission to request credentials or perform network side effects.

## Reusable in every compatible host

- Four deterministic text filters: MissAV, Twitter, Bad.news, and Haijiao.
- Multiple-file and pasted-text input, source recognition, minute-level time filtering, selection, stable deduplication, permanent-history comparison, and copy-ready output.
- MissAV code normalization, detail-link candidates, reference Tag extraction, two independent blacklists, validated browser-script generation, and three-folder Raindrop HTML export.
- One source may be bound to several tools; a message is received once and each selected tool gets its own independent queue/status. Tool failures must not block another tool.
- Incremental/history/manual-read semantics: `never` never changes Telegram read state; `manual` waits for an explicit confirmation; `safe_auto` marks read only after successful durable ingestion and a valid checkpoint. Historical pulls never auto-mark read.
- Rule versioning, preview/commit/rollback semantics, package manifests, conflict-safe imports, CSV/JSON/TXT generation, and privacy boundaries.
- Task/history/result views, error categories, retry/resume semantics when supplied by the host, business CRUD, snapshots, recycle-bin recovery, and v0.5.13 business-data migration.

## Not active in the local-only version

- Telegram personal API QR/phone/2FA login, dialog discovery, group/channel history pagination, manual read marking, checkpoints, edit/delete propagation, and account-safe session storage.
- Telegram Bot API updates, privacy-mode limitations, global offset handling, source discovery for groups/channels, and source fan-out.
- 123AV exact page verification, independent lookup pipeline, Chrome extension bridge, in-app serial assistant, 10-second rate-limit recovery, and export-only mode.

If a future local host adds these capabilities, it must expose checks such as:

```text
telegram.sources.list
telegram.history.load
telegram.sync.incremental
telegram.mark_read (manual confirmation only)
av123.lookup
av123.account.serial_action
```

Until then, remain in manual mode. Do not replace a missing adapter with web scraping or an untrusted AI guess.

## Environment differences

- A compatible local host may provide file access and a small local library adapter.
- No environment should maintain a second copy of the filtering rules. Any future executor must call this Skill's rule contract or a shared deterministic implementation.

## Deliberately excluded from parity

- Work/cloud execution or automatic upgrading to paid cloud services.
- Silent Telegram or Raindrop network writes.
- Direct Raindrop API synchronization in the Skill; generate import files unless the user explicitly enables a separate, confirmed adapter.
- Any secret, personal database, browser profile, or raw message archive inside the Skill package.
