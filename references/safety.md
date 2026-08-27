# Safety and confirmation rules

当前版本是离线本地模式。Telegram、123AV、MissAV、Bad.news、海角和 Raindrop 的网络访问均默认禁止；后文的网络条目只是未来兼容适配器的安全边界，不是当前执行许可。

## Secrets and privacy

Never ask the user to paste or upload Telegram API hash, Bot Token, OTP, password, Session, cookies, browser storage, Raindrop token, or a database containing them. The host may read a preconfigured secure store, but the Skill must see only a capability result and sanitized error. Never put secrets or raw Telegram text in logs, packages, generated source, or a response unless the user explicitly asks for a transient excerpt.

## Network boundaries

Manual mode performs no Telegram, MissAV, Bad.news, Haijiao, Twitter, Raindrop, or 123AV network requests. A browser script is output, not executed, unless the user explicitly asks the host to run a supported browser action.

Before a connected network action, state destination, purpose, scope, and expected side effect. HTTP 200 is not proof of a valid page or successful remote write; inspect the documented success evidence and classify access challenges, login pages, 404/429/403, timeout, and rate limit separately.

## Account and browser actions

Require a final confirmation immediately before Telegram login, marking read, 123AV favorite/follow actions, or any action that changes a remote account. Stop on CAPTCHA, unknown login state, or a page whose success cannot be verified. Never click through an ambiguous page or read passwords/cookies/Local Storage/Session Storage.

123AV account work is single-lane per site. On normal network or Error 1015, wait 10 seconds and resume from the last confirmed item. Do not retry an unknown side effect blindly.

## Data mutation

Before delete, restore, overwrite, migration commit, rule commit, or package import: show a preview, affected count, conflicts, and a one-time confirmation. Create a snapshot first. Use one transaction and report partial external effects separately if a remote action occurred.

## AI uncertainty

Never turn a one-off “smart guess” into a permanent filter. Put uncertain formats into a review list, explain the evidence, and only add a rule after explicit confirmation plus a regression sample. When the user asks for a plain list, do not mix explanations or guessed values into the plain-text block.
