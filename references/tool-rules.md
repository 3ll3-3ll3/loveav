# Tool rules

These are the baseline behavior requirements carried forward from Windows v0.5.13. They are rules, not a license to access a website without an explicit user request. They are not a closed-world rejection list: after the baseline pass, unfamiliar candidates must follow [the adaptive review lifecycle](rule-learning.md).

## MissAV

- Normalize codes to uppercase, collapse whitespace/underscore separators to `-`, collapse repeated hyphens, and normalize FC2 variants to `FC2-PPV-<digits>`.
- Accept the established alphanumeric code shape (`letters-digits` with an optional validated suffix) and clearly discard prose, URLs from unrelated sites, dates, category labels, and obvious noise. Preserve a trusted MissAV detail URL from the input when present; otherwise produce the canonical MissAV URL only where the host's rule adapter supports it. Borderline or new shapes go to `review` with evidence instead of being silently discarded.
- Treat URLs such as `https://missav.ai/dm558/110223-001` and `https://missav.ai/dm166/pondo-030326_001` as detail-page candidates. Do not require a short `AA-999` code when a trusted MissAV detail path supplies the identifier.
- The browser script is a validated user template. Inject only the normalized `CODE_TEXT`, current reference actress tags, and the export blacklist. Escape backticks and `${` before injection; never fabricate a replacement script when the template lacks its required placeholders.
- Reference Tag blacklist removes a tag from reference matching only. It does not remove the tag from the source library and does not prevent a film from entering the non-reference output folder.
- Raindrop export blacklist is independent: a matching actress tag sets `include_in_import=false` and excludes the film from generated Raindrop HTML/CSV, while the audit/report keeps the excluded record and reason.
- Generated bookmark output always creates three folders: `参考女优Tag命中`, `需要查找`, and `其他`. `需要查找` has priority for not-found, access-challenge, and unresolved metadata so an uncertain item is not hidden by a tag match.
- Actress Tag reference HTML extraction reads bookmark `TAGS` values, removes system/type boundary tags and duplicates, recognizes the established Japanese/Chinese/Latin name forms, shows a preview, then replaces the reference library only after confirmation.
- Never call the MissAV website from the Skill itself. A browser script is the default network mechanism.

## Twitter

- Prefer each message's ASCII `#tag` as the creator signal. Accept a valid `@handle` and an `x.com`/`twitter.com` profile URL as fallbacks.
- Handles are 1–15 ASCII letters, digits, or underscores. Exclude clearly reserved paths such as `home`, `explore`, `search`, `settings`, `login`, `messages`, and `notifications`; exclude obvious short topic tags and promotion/portal tags (especially a tag immediately following “传送门”). Borderline handles require `review` rather than silent rejection.
- Exclude handles ending in `_bot` for mention fallback. Deduplicate case-insensitively while preserving first-seen order.
- Return creator names and profile URLs as two separate lists using `https://x.com/<handle>`.

## Bad.news

- Accept only `https://bad.news/t/<digits>` on the canonical host, with optional query/fragment/trailing path removed.
- Exclude confirmed `/app`, category pages, home pages, tracking URLs, advertisements, and non-post links. Deduplicate exact canonical URLs while preserving first-seen order; an unfamiliar but plausible post path is a review candidate.

## Haijiao

- Accept only numeric direct posts under these seven categories: `hjjd`, `hjmz`, `hjyc`, `hjfn`, `hjsz`, `hjrq`, `hjhj`.
- Normalize to `https://www.haijiaolove.xyz/<category>/<digits>.html`.
- Exclude confirmed old domains, category pages, ads, redirects, tracking parameters, and other site paths. New numeric direct-post shapes are reviewed with their URL evidence before exclusion.

## Whos.tv solved answers

- This is the fifth active tool. It is a batch collection and document-generation workflow, not a Telegram text filter.
- Use the deterministic generator and organizer in `scripts/`; read `whostv-solved-answers.md` for the dynamic cutoff and exact Markdown contract.
- A successful Whos.tv result does not automatically enter the MissAV curated library. Extracted codes remain document content until the user explicitly selects them for library import.

## 123AV (legacy connected mode only)

- Keep query, account actions, and export separate. Query validates exact code evidence from the page title/body and does not treat a URL-only hit as success; classify missing, access challenge, login required, timeout, and network errors distinctly.
- Account actions are single-lane per site. Allowed modes are Chrome extension, in-app serial assistant, and export-only. Never read passwords, cookies, Local/Session Storage, or full page HTML.
- A normal network/`Error 1015` failure pauses for 10 seconds and resumes; an unknown login/CAPTCHA state becomes `verify_required` and stops side effects.
