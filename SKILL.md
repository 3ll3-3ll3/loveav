---
name: loveav
description: "Use this skill as a local-first LoveAV content workbench for Telegram exports, pasted text, curated libraries, v0.5.13-compatible filters, and Whos.tv solved-answer collection."
---

# LoveAV Skill

This Skill is the primary product surface. It makes Codex or another compatible AI execute the TG content workflow; a UI is only an occasional administration fallback. Use the current rules as a stable baseline, then apply the adaptive review loop in [rule learning](references/rule-learning.md) when an input is unfamiliar. Never silently invent, enable, or discard a new rule.

## Operating modes

Select one mode before doing work:

- **Manual (default):** accept pasted text or Telegram Desktop HTML/JSON/TXT/CSV/MD/LOG files. Do not connect to Telegram, do not ask for API credentials, and do not mark anything read.
- **Local library:** after a preview, add only the rows the user explicitly chooses to keep to the local curated library. Use that library for future deduplication and reference checks; do not treat every processed row as permanent history.
- **Administration:** use only for editing curated records, reference Tags, the two MissAV blacklists, backups, migration, or conflict review. Prefer a small local editor when a large table is required.

Telegram personal API, Bot API, Work/cloud execution, background synchronization, remote Raindrop writes, and 123AV account actions are intentionally out of the active scope. The v0.5.13 compatibility document records them for reference only; never propose them or request their credentials in this Skill's default workflow.

Treat the local companion data directory (`loveav-data/` beside this Skill, or an explicitly configured equivalent) as part of the Skill's runtime state. Its curated CSV rows and rule files are private user data, not files to publish with the Skill. If the companion library is absent, start with an empty library and say so. When upgrading from an older installation, recognize `tg-toolbox-data/` as the legacy directory only if the user explicitly points to it; do not silently move or delete it.

Manual mode is the default even if a connected adapter exists. Never switch modes merely because a file looks like a Telegram export.

The first four content functions (MissAV, Twitter, Bad.news, and Haijiao) share one input contract: any combination of Telegram Desktop HTML/JSON, TXT, CSV, MD, LOG, or pasted plain text. The file type is only an input container; the selected tool decides what can be extracted from its text. Whos.tv has its separate returned-JSON workflow.

## Standard workflow

1. **Classify the request.** Identify input, selected tools, time range, local library policy, and requested outputs. If a required choice is missing, ask one short question; do not save anything with guessed settings.
2. **Preview transient input.** Parse all pasted text and selected files together. Merge Telegram Desktop multipart files from the same export session, retain message date/source/message ID where available, and deduplicate by the stable message identity. Keep raw message text only in the current request/preview memory.
3. **Show sources before processing.** Present each source title, kind, count, and a stable key. Reuse a saved binding only when the key matches. If a source has no binding or could map to multiple tools, ask the user to choose; never infer from filename alone.
4. **Apply baseline rules and adaptive review.** Run each selected tool independently, preserving order and canonical deduplication. Apply the established baseline in [tool rules](references/tool-rules.md), then inspect unfamiliar or borderline candidates with the evidence checklist in [rule learning](references/rule-learning.md). Do not discard a candidate solely because its shape is new; classify it as `review` when evidence is insufficient.
5. **Apply library and blacklists.** Compare canonical result keys with the selected-row library before reporting “new”. If an optional `seen-index.csv` also contains the key but it is absent from the curated library, label it “以前见过但未精选” and do not silently suppress it. Apply the two MissAV blacklist layers in their distinct order; never merge them. A proposed rule remains a suggestion until the user confirms it and a regression sample is recorded.
6. **Return useful output immediately.** Give a compact summary followed by copy-ready fenced plain text. Separate primary values from links. Generate files only when requested. Read [input/output contract](references/input-output.md).
7. **Persist only selected derived data.** Save only rows the user explicitly keeps, plus the canonical key, tags, rule version, source hash, and timestamps. Do not save every run, Telegram raw text, or transient previews.
8. **Report failures precisely.** Separate parse errors, invalid candidates, network errors, access challenges, rate limits, user confirmation requirements, and partial completion. Offer retry/resume only when the host exposes a checkpoint; never claim success from a timeout or an HTTP status alone.

## Adaptive rule learning

When the baseline does not confidently classify a candidate, use a three-way outcome: accept, reject, or `review`. For `review`, preserve only a transient evidence snippet in the response, explain which checks disagree, and ask for a focused confirmation instead of guessing. Record confirmed/rejected examples as a versioned rule suggestion with scope, rationale, and false-positive guard. Promote a suggestion to the active rules only after explicit user confirmation and at least one positive and one negative regression example; keep tool-specific rules separate unless evidence proves they are shared. If the host has no write adapter, return the suggestion in a copyable form and do not claim that the Skill learned it. Read [rule learning](references/rule-learning.md) for the exact lifecycle and storage fields.

## Whos.tv solved answers

Treat requests to scrape, continue, validate, organize, classify, or update whos.tv solved answers as the fifth main function. Read [Whos.tv solved-answer rules](references/whostv-solved-answers.md) before acting.

- Generate full console scripts with `node scripts/generate_whostv_scraper.js --pages n` or `--incremental`; do not hand-edit a partial script in chat.
- When the user supplies `whos_tv_solved_answers*.json`, run `node scripts/organize_whos_answers.js <path>` and trust no output until its validation succeeds.
- Do not update the cutoff or create final Markdown after a failed validation.
- Keep Whos.tv answer documents separate from the curated MissAV history. Only add an extracted code to the curated library if the user separately selects it.

## Canonical host operations

Map these logical operations to whatever MCP, CLI, or local adapter is available:

```text
input.preview(files, pasted_text, start, end)
input.process(preview_id, selected_message_keys, source_bindings, tools)
history.search(tool, canonical_query, include_deleted)
rules.get / rules.preview / rules.suggest / rules.review / rules.commit / rules.rollback
results.query / results.copy / results.export
script.generate(codes, reference_tags, both_blacklists)
whostv.script.generate(mode, pages_or_cutoff)
whostv.answers.validate / whostv.answers.organize / whostv.state.update
library.preview_import / library.commit_selected / library.query / library.update / library.remove
library.export / library.backup / library.verify
rules.export / rules.import_preview
```

If the host only supports analysis and not writes, still complete parsing/filtering/output in the conversation and state which derived data the user must explicitly save through the UI. Never simulate a successful database write.

## Output rules

- MissAV: separate one-code-per-line list, one-URL-per-line list, complete browser script when requested, and Raindrop import HTML when requested.
- Twitter: separate creator/handle list and profile URL list.
- Bad.news and Haijiao: one canonical direct-post URL per line; exclude app, category, advertising, tracking, and junk URLs.
- Whos.tv: validate the returned JSON, then generate one date-named Markdown file with the fixed four-category order and the pure-code list at the top.
- Generic exports: UTF-8 TXT, CSV with formula-injection protection, JSON, and versioned result/library/rule packages.
- Always state counts for input, excluded-by-time, invalid, duplicate, historical, new, `review`, and error records when those counts are available.
- Do not put explanations inside a copy-ready list. Keep labels and lists separate.

## Safety and confirmation

Before any destructive local side effect, read [safety](references/safety.md) and obtain confirmation at the last responsible moment. In particular, confirm before importing/overwriting curated data, deleting library rows, changing rules, restoring backups, or exporting raw message text. Manual parsing and local derived output do not need confirmation.

## UI boundary

The UI is not the daily workflow. Open it only for large curated-library edits, rule/blacklist maintenance, backup/restore, v0.5.13 migration, or a host capability that cannot be expressed safely in chat. The UI must call the same host operations and rules; it must not maintain a second implementation.

## References

- [Tool rules](references/tool-rules.md) — MissAV, Twitter, Bad.news, Haijiao, and 123AV behavior.
- [Input and output contract](references/input-output.md) — accepted sources, normalization, selection, and files.
- [Data contract](references/data-contract.md) — history, CRUD, packages, migration, and privacy fields.
- [Curated library](references/curated-library.md) — selected-row CSV data, deduplication, blacklists, and atomic updates.
- [Legacy parity](references/legacy-parity.md) — v0.5.13 capabilities retained as a disabled reference only.
- [v0.5.13 feature map](references/v0513-feature-map.md) — parity checklist for future adapters.
- [Safety](references/safety.md) — credentials, network, account actions, destructive operations, and recovery.
- [Rule learning](references/rule-learning.md) — suspicious candidates, evidence review, suggestions, promotion, and regression samples.
- [Examples](references/examples.md) — natural-language requests and expected response shape.
- [Whos.tv solved answers](references/whostv-solved-answers.md) — scraping, dynamic cutoff, validation, classification, archive, and Markdown rules.

For one-time local migration from the old SQLite database, use `scripts/migrate_v0513_library.py`. It is read-only on the source and creates a preview; never pass `--activate-ok` until the user explicitly approves promoting the successful legacy rows into the curated library.
