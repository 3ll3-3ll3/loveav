#!/usr/bin/env python3
from __future__ import annotations

import argparse
import encodings.idna as _stdlib_idna
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

TARGET_DOMAIN = "mypikpak.com"
SCHEMA = "loveav.svip-pikpak-resource-replies.v1"
MAX_TGCTL_PAGE = 500
_URL_RE = re.compile(r"(?i)(?:https?://|www\.)[^\s<>\]\[(){}\"']+")


class WorkflowError(RuntimeError):
    pass


def _canonical_hostname(hostname: str) -> str | None:
    raw = str(hostname or "").strip().rstrip(".")
    if not raw or ":" in raw:
        return None
    labels: list[str] = []
    try:
        for label in raw.split("."):
            if not label:
                return None
            labels.append(_stdlib_idna.ToASCII(label).decode("ascii").casefold())
    except (UnicodeError, UnicodeDecodeError):
        return None
    return ".".join(labels)


def _url_hostname(value: str) -> str | None:
    raw = str(value or "").strip().rstrip(".,;:!?)]}")
    if not raw:
        return None
    candidate = raw if "://" in raw else f"http://{raw}"
    try:
        hostname = urlsplit(candidate).hostname
    except ValueError:
        return None
    return _canonical_hostname(hostname or "")


def is_pikpak_url(value: str) -> bool:
    hostname = _url_hostname(value)
    return bool(hostname and (hostname == TARGET_DOMAIN or hostname.endswith(f".{TARGET_DOMAIN}")))


def _iter_entity_urls(message: dict[str, Any]) -> Iterable[str]:
    entities = message.get("entities")
    if not isinstance(entities, list):
        return
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        direct = entity.get("url")
        if isinstance(direct, str) and direct:
            yield direct


def extract_pikpak_urls(message: dict[str, Any]) -> list[str]:
    candidates: list[str] = list(_iter_entity_urls(message))
    for field in ("text", "caption"):
        value = message.get(field)
        if isinstance(value, str):
            candidates.extend(match.group(0) for match in _URL_RE.finditer(value))
    output: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = candidate.strip().rstrip(".,;:!?)]}")
        if cleaned and cleaned not in seen and is_pikpak_url(cleaned):
            seen.add(cleaned)
            output.append(cleaned)
    return output


def _has_photo(message: dict[str, Any]) -> bool:
    media = message.get("media")
    if not isinstance(media, dict):
        return False
    return media.get("media_type") == "photo" or media.get("photo_id") is not None


def _base_evidence(message: dict[str, Any], expected_chat_id: int) -> dict[str, Any]:
    sender = message.get("sender")
    if not isinstance(sender, dict):
        sender = {}
    posted_as = sender.get("posted_as_chat_id")
    return {
        "sender_type": sender.get("sender_type"),
        "is_creator": sender.get("is_creator"),
        "is_admin": sender.get("is_admin"),
        "anonymous_admin": sender.get("anonymous_admin") is True,
        "posted_as_current_chat": posted_as == expected_chat_id,
        "role_basis": sender.get("role_basis"),
        "unknown_reason": sender.get("unknown_reason"),
        "reply_to_message_id_present": message.get("reply_to_message_id") is not None,
        "photo_present": _has_photo(message),
    }


def classify_message(message: dict[str, Any], *, expected_chat_id: int) -> tuple[str, dict[str, Any]]:
    evidence = _base_evidence(message, expected_chat_id)
    sender_type = evidence["sender_type"]
    unknown_reason = evidence["unknown_reason"]

    if evidence["is_creator"] is True:
        evidence["reason"] = "telegram_current_owner"
        return "verified_moderator", evidence
    if sender_type == "anonymous_admin" and evidence["anonymous_admin"]:
        evidence["reason"] = "telegram_anonymous_admin"
        return "verified_moderator", evidence
    if evidence["posted_as_current_chat"] and sender_type in {"chat", "channel", "anonymous_admin"}:
        evidence["reason"] = "telegram_current_chat_send_as"
        return "verified_moderator", evidence
    if evidence["is_admin"] is True:
        evidence["reason"] = "telegram_current_admin"
        return "verified_moderator", evidence
    if sender_type == "user" and evidence["is_creator"] is False and evidence["is_admin"] is False:
        evidence["reason"] = "telegram_known_ordinary_member"
        return "excluded_known_member", evidence
    if unknown_reason == "forwarded_message_without_actual_sender":
        evidence["reason"] = "forward_origin_is_not_actual_sender"
        return "needs_review", evidence
    if sender_type == "unknown" and unknown_reason == "telegram_sender_not_provided":
        reply_present = evidence["reply_to_message_id_present"]
        photo_present = evidence["photo_present"]
        if reply_present and photo_present:
            evidence["reason"] = "missing_sender_plus_reply_and_photo"
            return "trusted_official_reply", evidence
        if reply_present or photo_present:
            evidence["reason"] = "missing_sender_with_only_one_context_signal"
            return "needs_review", evidence
        evidence["reason"] = "missing_sender_without_reply_or_photo"
        return "excluded_insufficient_evidence", evidence
    evidence["reason"] = "sender_evidence_not_sufficient_for_automatic_trust"
    return "needs_review", evidence


def classify_messages(messages: Iterable[dict[str, Any]], *, expected_chat_id: int) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {
        "verified_moderator": [],
        "trusted_official_reply": [],
        "needs_review": [],
        "excluded_known_member": [],
        "excluded_insufficient_evidence": [],
    }
    classification_message_counts: Counter[str] = Counter()
    input_count = 0
    wrong_chat_count = 0
    no_matching_url_count = 0

    for message in messages:
        input_count += 1
        if not isinstance(message, dict):
            no_matching_url_count += 1
            continue
        if message.get("chat_id") != expected_chat_id:
            wrong_chat_count += 1
            continue
        urls = extract_pikpak_urls(message)
        if not urls:
            no_matching_url_count += 1
            continue
        classification, evidence = classify_message(message, expected_chat_id=expected_chat_id)
        classification_message_counts[classification] += 1
        for url in urls:
            record = {
                "message_id": message.get("message_id"),
                "date": message.get("date"),
                "pikpak_url": url,
                "classification": classification,
                "evidence": {**evidence, "pikpak_hostname": _url_hostname(url)},
            }
            groups[classification].append(record)

    primary = groups["verified_moderator"] + groups["trusted_official_reply"]
    return {
        "schema": SCHEMA,
        "summary": {
            "input_message_count": input_count,
            "wrong_chat_excluded_count": wrong_chat_count,
            "no_matching_pikpak_url_count": no_matching_url_count,
            "verified_moderator_message_count": classification_message_counts["verified_moderator"],
            "trusted_official_reply_message_count": classification_message_counts["trusted_official_reply"],
            "primary_message_count": classification_message_counts["verified_moderator"] + classification_message_counts["trusted_official_reply"],
            "needs_review_message_count": classification_message_counts["needs_review"],
            "excluded_known_member_count": classification_message_counts["excluded_known_member"],
            "excluded_insufficient_evidence_count": classification_message_counts["excluded_insufficient_evidence"],
            "primary_url_count": len(primary),
            "needs_review_url_count": len(groups["needs_review"]),
        },
        "primary": primary,
        "needs_review": groups["needs_review"],
        "excluded_known_members": groups["excluded_known_member"],
        "excluded_insufficient_evidence": groups["excluded_insufficient_evidence"],
    }


def _default_config_path() -> Path:
    data_dir = os.environ.get("LOVEAV_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "svip-resource-replies.json"
    return Path(__file__).resolve().parents[1] / "loveav-data" / "svip-resource-replies.json"


def load_config(path: Path) -> tuple[int, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"缺少本地私有配置：{path}。请在 bindings.Svip.chat_id 中写入精确 chat_id。") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"无法读取本地私有配置：{path}") from exc
    bindings = payload.get("bindings")
    svip = bindings.get("Svip") if isinstance(bindings, dict) else None
    chat_id = svip.get("chat_id") if isinstance(svip, dict) else None
    if not isinstance(chat_id, int) or isinstance(chat_id, bool) or chat_id == 0:
        raise WorkflowError("本地配置 bindings.Svip.chat_id 必须是非零整数。")
    tgctl = payload.get("tgctl_path") or os.environ.get("LOVEAV_TGCTL") or "tgctl"
    if not isinstance(tgctl, str) or not tgctl.strip():
        raise WorkflowError("tgctl_path 必须是非空字符串。")
    return chat_id, tgctl.strip()


def _parse_json_envelope(text: str) -> tuple[list[dict[str, Any]], str | None, bool]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WorkflowError("tgctl 未返回有效 JSON。") from exc
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        code = None
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            code = payload["error"].get("code")
        raise WorkflowError(f"tgctl 调用失败{f'：{code}' if code else ''}。")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise WorkflowError("tgctl JSON 缺少 data.items。")
    items = [item for item in data["items"] if isinstance(item, dict)]
    cursor = data.get("next_cursor")
    if cursor is not None and not isinstance(cursor, str):
        cursor = None
    return items, cursor, data.get("has_more") is True


def load_structured_messages(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if not stripped:
        return []
    if stripped.startswith("{"):
        try:
            items, _, _ = _parse_json_envelope(text)
            return items
        except WorkflowError:
            pass
    messages: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkflowError(f"第 {line_no} 行不是有效 JSON。") from exc
        if not isinstance(payload, dict):
            continue
        if payload.get("type") == "item" and isinstance(payload.get("data"), dict):
            messages.append(payload["data"])
        elif "message_id" in payload:
            messages.append(payload)
    return messages


def build_tgctl_command(tgctl_path: str, *, chat_id: int, page_limit: int, cursor: str | None = None, since: str | None = None, until: str | None = None) -> list[str]:
    command = [tgctl_path, "messages", "history", "--chat", str(chat_id), "--limit", str(page_limit), "--json"]
    if since:
        command.extend(["--since", since])
    if until:
        command.extend(["--until", until])
    if cursor:
        command.extend(["--cursor", cursor])
    return command


def fetch_structured_messages(tgctl_path: str, *, chat_id: int, limit: int, since: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
    if limit <= 0:
        raise WorkflowError("limit 必须大于 0。")
    output: list[dict[str, Any]] = []
    cursor: str | None = None
    while len(output) < limit:
        page_limit = min(MAX_TGCTL_PAGE, limit - len(output))
        command = build_tgctl_command(tgctl_path, chat_id=chat_id, page_limit=page_limit, cursor=cursor, since=since, until=until)
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=300)
        except FileNotFoundError as exc:
            raise WorkflowError("找不到 tgctl；请在本地私有配置中设置 tgctl_path。") from exc
        except subprocess.TimeoutExpired as exc:
            raise WorkflowError("tgctl 只读查询超过 300 秒。") from exc
        stdout = completed.stdout.strip()
        if completed.returncode != 0:
            code = None
            if stdout:
                try:
                    payload = json.loads(stdout)
                    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
                        code = payload["error"].get("code")
                except json.JSONDecodeError:
                    pass
            raise WorkflowError(f"tgctl 只读查询失败，退出码 {completed.returncode}" + (f"，错误码 {code}" if code else "") + "。")
        items, next_cursor, has_more = _parse_json_envelope(stdout)
        output.extend(items)
        if not has_more or not next_cursor or not items:
            break
        cursor = next_cursor
    return output[:limit]


def _select_output(result: dict[str, Any], view: str, classifications: set[str]) -> dict[str, Any]:
    selected = {"schema": result["schema"], "summary": result["summary"]}

    def matches(record: dict[str, Any]) -> bool:
        return not classifications or record.get("classification") in classifications

    if view == "review":
        selected["needs_review"] = [row for row in result["needs_review"] if matches(row)]
        return selected
    selected["primary"] = [row for row in result["primary"] if matches(row)]
    selected["needs_review"] = [row for row in result["needs_review"] if matches(row)]
    if view == "all":
        selected["excluded_known_members"] = [row for row in result["excluded_known_members"] if matches(row)]
        selected["excluded_insufficient_evidence"] = [row for row in result["excluded_insufficient_evidence"] if matches(row)]
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministically classify Svip official PikPak resource replies from tgctl structured output.")
    parser.add_argument("--config", type=Path, default=_default_config_path(), help="local private config; default: loveav-data/svip-resource-replies.json")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="existing tgctl --json/--jsonl output")
    source.add_argument("--run-tgctl", action="store_true", help="run bounded read-only tgctl messages history using the private Svip chat binding")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--view", choices=["default", "review", "all"], default="default")
    parser.add_argument("--classification", action="append", choices=["verified_moderator", "trusted_official_reply", "needs_review", "excluded_known_member", "excluded_insufficient_evidence"], default=[])
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        chat_id, tgctl_path = load_config(args.config)
        if args.input:
            messages = load_structured_messages(args.input)
        elif args.run_tgctl:
            messages = fetch_structured_messages(tgctl_path, chat_id=chat_id, limit=args.limit, since=args.since, until=args.until)
        else:
            raise WorkflowError("必须显式选择 --input 或 --run-tgctl。")
        result = classify_messages(messages, expected_chat_id=chat_id)
        selected = _select_output(result, args.view, set(args.classification))
        print(json.dumps(selected, ensure_ascii=False, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")))
        return 0
    except (OSError, WorkflowError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
