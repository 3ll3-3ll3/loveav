#!/usr/bin/env python3
"""Read a v0.5.13 SQLite database and create local Skill library candidates.

The source database is opened read-only.  By default this script creates:
  - indexes/seen-index.csv: every legacy code identity and status;
  - preview/curated-candidates.csv: legacy rows eligible for user selection;
  - preview/review-candidates.csv: rows that need manual review;
  - preview/observed-actress-tags.csv: tags observed in the old database;
  - legacy/raindrop-metadata.csv: non-secret legacy bookmark fields;
  - rules/*-blacklist.csv: optional copies of old blacklist text files;
  - manifest.json and MIGRATION_PREVIEW.md.

Pass --activate-ok only after the user explicitly confirms that legacy `ok`
rows should become the initial curated library.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


CODE_RE = re.compile(r"^(?:FC2-PPV-\d{5,9}|[A-Z]{2,12}-\d{2,7}(?:-[A-Z0-9]{1,12})?)$")
SECRET_WORDS = ("token", "secret", "password", "passwd", "otp", "session", "cookie", "api_hash", "credential")


def normalize_code(value: object) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[＿_\s]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    fc2 = re.fullmatch(r"FC2-?(?:PPV-?)?(\d{5,9})", text, re.IGNORECASE)
    if fc2:
        text = f"FC2-PPV-{fc2.group(1)}"
    return text if CODE_RE.fullmatch(text) else ""


def safe_text(value: object) -> str:
    return str(value or "").replace("\x00", "").strip()


def csv_value(value: object) -> str:
    """Prevent formula interpretation when a CSV is opened in a spreadsheet."""
    text = safe_text(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"pragma table_info({quote_identifier(table)})").fetchall()
    return {str(row[1]) for row in rows}


def query_rows(connection: sqlite3.Connection, table: str, wanted: Iterable[str]) -> list[dict[str, object]]:
    columns = table_columns(connection, table)
    selected = [name for name in wanted if name in columns and not any(word in name.lower() for word in SECRET_WORDS)]
    if not selected:
        return []
    sql = "select " + ", ".join(quote_identifier(name) for name in selected) + f" from {quote_identifier(table)}"
    return [dict(zip(selected, row)) for row in connection.execute(sql).fetchall()]


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: csv_value(row.get(field, "")) for field in fieldnames})
                count += 1
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return count


def read_blacklist_file(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    output: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        value = re.sub(r"\s+", " ", raw).strip()
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def build_rows(connection: sqlite3.Connection) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    code_rows = query_rows(
        connection,
        "codes",
        [
            "id", "code", "best_url", "status", "source_url", "missav_error",
            "raindrop_folder", "raindrop_title", "raindrop_excerpt", "raindrop_note",
            "raindrop_cover", "raindrop_created", "raindrop_collection_id", "raindrop_remote_id",
            "created_at", "updated_at",
        ],
    )
    if not code_rows:
        raise RuntimeError("旧数据库没有可读取的 codes 表或该表为空。")

    tag_rows = query_rows(connection, "actress_tags", ["id", "tag_name", "created_at", "updated_at"])
    tag_by_id = {int(row["id"]): safe_text(row.get("tag_name")) for row in tag_rows if row.get("id") is not None}
    links = query_rows(connection, "actress_code_map", ["actress_id", "code_id"])
    tags_by_code: defaultdict[int, list[str]] = defaultdict(list)
    for link in links:
        code_id, actress_id = link.get("code_id"), link.get("actress_id")
        if code_id is None or actress_id is None:
            continue
        tag = tag_by_id.get(int(actress_id), "")
        if tag and tag not in tags_by_code[int(code_id)]:
            tags_by_code[int(code_id)].append(tag)

    genre_rows = query_rows(connection, "genre_tags", ["id", "name"])
    genre_by_id = {int(row["id"]): safe_text(row.get("name")) for row in genre_rows if row.get("id") is not None}
    genre_links = query_rows(connection, "code_genres", ["code_id", "genre_id"])
    genres_by_code: defaultdict[int, list[str]] = defaultdict(list)
    for link in genre_links:
        code_id, genre_id = link.get("code_id"), link.get("genre_id")
        if code_id is None or genre_id is None:
            continue
        genre = genre_by_id.get(int(genre_id), "")
        if genre and genre not in genres_by_code[int(code_id)]:
            genres_by_code[int(code_id)].append(genre)

    seen_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    for row in sorted(code_rows, key=lambda item: int(item.get("id") or 0)):
        code = normalize_code(row.get("code"))
        status = safe_text(row.get("status")) or "unknown"
        code_id = int(row.get("id") or 0)
        tags = tags_by_code[code_id]
        genres = genres_by_code[code_id]
        base = {
            "tool": "missav",
            "canonical_key": code.replace("-", "") if code else f"legacy-id-{code_id}",
            "primary_value": code or safe_text(row.get("code")),
            "secondary_value": safe_text(row.get("best_url")),
            "status": status,
            "tags": "|".join(tags),
            "genres": "|".join(genres),
            "folder": safe_text(row.get("raindrop_folder")),
            "first_seen_at": safe_text(row.get("created_at")),
            "last_seen_at": safe_text(row.get("updated_at")) or safe_text(row.get("created_at")),
            "seen_count": 1,
            "rule_version": "v0.5.13-legacy",
            "legacy_id": code_id,
            "selection_state": "pending" if status == "ok" and code else "review",
            "notes": safe_text(row.get("missav_error")),
        }
        seen_rows.append({
            "tool": "missav",
            "canonical_key": base["canonical_key"],
            "primary_value": base["primary_value"],
            "status": status,
            "legacy_id": code_id,
            "source": "v0.5.13 codes",
        })
        if status == "ok" and code:
            candidate_rows.append(base)
        else:
            review_rows.append(base)

    observed = Counter(tag for tags in tags_by_code.values() for tag in tags)
    observed_rows = [
        {"tag": tag, "code_count": count, "candidate_reference": "review"}
        for tag, count in sorted(observed.items(), key=lambda item: (-item[1], item[0]))
    ]
    return seen_rows, candidate_rows, review_rows + observed_rows


def write_legacy_metadata(connection: sqlite3.Connection, output: Path) -> int:
    rows = query_rows(
        connection,
        "codes",
        ["id", "code", "best_url", "raindrop_folder", "raindrop_title", "raindrop_excerpt", "raindrop_note", "raindrop_cover", "raindrop_created", "raindrop_collection_id", "raindrop_remote_id"],
    )
    fields = ["legacy_id", "code", "best_url", "folder", "title", "excerpt", "note", "cover", "created", "collection_id", "remote_id"]
    normalized = []
    for row in rows:
        normalized.append({
            "legacy_id": row.get("id"), "code": normalize_code(row.get("code")) or row.get("code"),
            "best_url": row.get("best_url"), "folder": row.get("raindrop_folder"),
            "title": row.get("raindrop_title"), "excerpt": row.get("raindrop_excerpt"),
            "note": row.get("raindrop_note"), "cover": row.get("raindrop_cover"),
            "created": row.get("raindrop_created"), "collection_id": row.get("raindrop_collection_id"),
            "remote_id": row.get("raindrop_remote_id"),
        })
    return write_csv(output, fields, normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="v0.5.13 missav_data.db (opened read-only)")
    parser.add_argument("--output", required=True, type=Path, help="private output directory, normally loveav/user-data/...")
    parser.add_argument("--blacklist-dir", type=Path, help="optional old missav-blacklists directory")
    parser.add_argument("--activate-ok", action="store_true", help="explicitly activate legacy status=ok candidates as curated-results.csv")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if not source.exists() or source.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise SystemExit(f"找不到可读 SQLite 文件：{source}")
    output.mkdir(parents=True, exist_ok=True)

    uri = f"file:{source.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
        required = {"codes", "actress_tags", "actress_code_map"}
        missing = sorted(required - tables)
        if missing:
            raise SystemExit(f"旧数据库缺少必要表：{', '.join(missing)}")
        seen_rows, candidate_rows, review_and_observed = build_rows(connection)
        observed_rows = [row for row in review_and_observed if "tag" in row]
        review_rows = [row for row in review_and_observed if "tag" not in row]
        files: dict[str, int] = {}
        files["indexes/seen-index.csv"] = write_csv(
            output / "indexes/seen-index.csv",
            ["tool", "canonical_key", "primary_value", "status", "legacy_id", "source"],
            seen_rows,
        )
        files["preview/curated-candidates.csv"] = write_csv(
            output / "preview/curated-candidates.csv",
            ["tool", "canonical_key", "primary_value", "secondary_value", "status", "tags", "genres", "folder", "first_seen_at", "last_seen_at", "seen_count", "rule_version", "legacy_id", "selection_state", "notes"],
            candidate_rows,
        )
        files["preview/review-candidates.csv"] = write_csv(
            output / "preview/review-candidates.csv",
            ["tool", "canonical_key", "primary_value", "secondary_value", "status", "tags", "genres", "folder", "first_seen_at", "last_seen_at", "seen_count", "rule_version", "legacy_id", "selection_state", "notes"],
            review_rows,
        )
        files["preview/observed-actress-tags.csv"] = write_csv(
            output / "preview/observed-actress-tags.csv",
            ["tag", "code_count", "candidate_reference"],
            observed_rows,
        )
        files["legacy/raindrop-metadata.csv"] = write_legacy_metadata(connection, output / "legacy/raindrop-metadata.csv")
    finally:
        connection.close()

    if args.activate_ok:
        active = [dict(row, selection_state="active", status="active") for row in candidate_rows]
        active_path = output / "library/curated-results.csv"
        if active_path.exists():
            backup_path = output / "backups" / f"curated-results-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(active_path, backup_path)
        files["library/curated-results.csv"] = write_csv(
            active_path,
            ["tool", "canonical_key", "primary_value", "secondary_value", "status", "tags", "genres", "folder", "first_seen_at", "last_seen_at", "seen_count", "rule_version", "legacy_id", "selection_state", "notes"],
            active,
        )
        files["library/missav-codes.csv"] = write_csv(
            output / "library/missav-codes.csv",
            ["canonical_key", "code", "missav_url", "tags", "genres", "folder", "first_seen_at", "last_seen_at", "rule_version", "status"],
            [
                {
                    "canonical_key": row["canonical_key"], "code": row["primary_value"],
                    "missav_url": row["secondary_value"], "tags": row["tags"], "genres": row["genres"],
                    "folder": row["folder"], "first_seen_at": row["first_seen_at"], "last_seen_at": row["last_seen_at"],
                    "rule_version": row["rule_version"], "status": row["status"],
                }
                for row in active
            ],
        )
        files["indexes/history-index.csv"] = write_csv(
            output / "indexes/history-index.csv",
            ["tool", "canonical_key", "primary_value", "status", "source"],
            [
                {"tool": row["tool"], "canonical_key": row["canonical_key"], "primary_value": row["primary_value"], "status": row["status"], "source": "curated-results.csv"}
                for row in active
            ],
        )

    blacklist_dir = args.blacklist_dir.resolve() if args.blacklist_dir else None
    blacklist_files = {
        "rules/reference-blacklist.csv": "1-参考女优Tag库黑名单.txt",
        "rules/raindrop-export-blacklist.csv": "2-Raindrop导出黑名单.txt",
    }
    for relative, filename in blacklist_files.items():
        values = read_blacklist_file(blacklist_dir / filename) if blacklist_dir else []
        files[relative] = write_csv(output / relative, ["pattern", "match_type", "enabled", "note"], [{"pattern": value, "match_type": "exact_tag", "enabled": 1, "note": "migrated from v0.5.13"} for value in values])

    source_hash = sha256_file(source)
    manifest = {
        "format_version": "tg-toolbox-library-migration-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {"name": source.name, "sha256": source_hash, "read_only": True},
        "selection_policy": "Only explicitly selected curated-candidates become library/curated-results.csv; seen-index is not a curated library.",
        "counts": {"seen": len(seen_rows), "curated_candidates": len(candidate_rows), "review_candidates": len(review_rows), "observed_actress_tags": len(observed_rows)},
        "files": {},
    }
    for relative, count in files.items():
        target = output / relative
        manifest["files"][relative] = {"rows": count, "sha256": sha256_file(target)}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# v0.5.13 数据迁移预览",
        "",
        f"- 源数据库：`{source.name}`",
        f"- 源 SHA-256：`{source_hash}`",
        f"- 已见番号：{len(seen_rows)}",
        f"- `ok` 精选候选：{len(candidate_rows)}（{'已按显式参数激活' if args.activate_ok else '默认未激活'}）",
        f"- 待复核候选：{len(review_rows)}",
        f"- 观察到的女优 Tag：{len(observed_rows)}（仅候选，不自动加入参考库）",
        "",
        "`indexes/seen-index.csv` 用于判断旧库是否见过；只有用户明确选择的行才能进入 `library/curated-results.csv`。" if not args.activate_ok else "本次使用了显式 `--activate-ok`；仅旧库中状态为 `ok` 且能规范化的行进入 `library/curated-results.csv`，其余仍在待复核文件。",
        "原始数据库未写入，凭据、Session、Telegram 原文未读取或导出。",
    ]
    (output / "MIGRATION_PREVIEW.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "source_sha256": source_hash, "files": files}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
