# Local data, curated library, and administration contract

## Permanent data

The local host may persist only derived business data that the user explicitly chose to keep:

- source identity and tool bindings;
- deterministic message identity and content hash;
- canonical result rows and result lineage;
- permanent library rows and their history keys;
- reference Tags, both blacklists, immutable rule versions and diffs;
- optional compact run/output metadata and error classification (never the full input record);
- Raindrop mapping only when it is a local export artifact, not an API credential or remote session.

Do not persist Telegram message body, OTP, password, API hash, Bot Token, cookie, browser storage, or session text in these tables.

The selected-row library is the product's durable knowledge base. A processed row that the user did not select remains transient and must not enter the library merely because it appeared in a preview.

## History semantics

- A repeated message/tool pair is idempotent and can still be listed as a result of the new run.
- An edited message supersedes prior lineage and reprocesses affected tools.
- A deleted message creates a tombstone or inactive lineage; do not silently erase audit history.
- Manual text tools save a derived row only after the user selects it. The saved row is available to future reference and deduplication checks.
- “Historical” means its canonical key already exists in the curated library; it is distinct from “duplicate in this input”.

## Curated library files

Keep the authoritative selected rows in a local CSV (or the equivalent local table) with at least `tool`, `canonical_key`, `primary_value`, `secondary_value`, `tags`, `folder`, `first_seen_at`, `last_seen_at`, `seen_count`, `rule_version`, and `status`. Generate a smaller `history-index.csv` from it for quick checks; never edit the generated index as the source of truth.

Reference Tags and the two MissAV blacklists remain separate files. A tag blacklist must not delete a curated result, and a result-library row must not silently become a blacklist entry. Any automatic suggestion is placed in a preview list until the user explicitly promotes it.

Updates use a temporary file plus atomic replace, preserve a timestamped backup, validate headers/unique keys/UTF-8, and reject partial or ambiguous rows. A CSV may be opened by other AI tools, but the local host remains responsible for locking and conflict detection.

## Data operations

All query, create, update, bulk-update, delete, restore, copy, and export operations use a host adapter with a table whitelist and field validation. Use cursor pagination for large data. Cross-page selection is represented by a filter descriptor plus exclusions, not an unbounded ID list.

Destructive or high-impact writes require:

1. a preview with affected count and conflict/invalid details;
2. an operation-specific confirmation token or explicit confirmation;
3. a pre-operation snapshot;
4. one transaction, with rollback on any error;
5. an audit record that excludes raw text and secrets.

The UI may expose a business view and an advanced table view, but never arbitrary SQL. Long text uses a proper editor rather than repeated single-field prompts.

## Packages and migration

Result, library, rule, and backup packages contain a manifest and SHA-256. Import always previews new, duplicate, conflict, invalid, and skipped counts before writing; conflicts never silently overwrite.

v0.5.13 migration is read-only until confirmation: check source integrity/schema/hash, preview mappings, create a destination snapshot, then commit business records in one transaction. Migrate codes, tags, task history, reliable source bindings, and Raindrop export mappings. Do not migrate sessions, credentials, read positions, Bot offsets, raw Telegram bodies, caches, network task internals, or 123AV account state.

## UI-only operations

Bulk Tag/blacklist editing, source-binding correction, large conflict review, database backup/restore, and legacy migration may use a small UI. The UI is an adapter to this contract, not a second product logic layer.
