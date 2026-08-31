from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "filter_svip_resource_replies.py"
SPEC = importlib.util.spec_from_file_location("svip_filter", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

CHAT_ID = -1009000000001
BASE_URL = "https://mypikpak.com/s/abc"


def sender(**overrides):
    value = {
        "sender_id": 101,
        "sender_type": "user",
        "display_name": None,
        "username": None,
        "posted_as_chat_id": None,
        "is_creator": False,
        "is_admin": False,
        "admin_title": None,
        "anonymous_admin": False,
        "via_bot_id": None,
        "role_basis": "current_snapshot",
        "unknown_reason": None,
    }
    value.update(overrides)
    return value


def message(message_id, *, sender_value, url=BASE_URL, reply=None, photo=False, chat_id=CHAT_ID):
    return {
        "chat_id": chat_id,
        "source_chat_id": chat_id,
        "message_id": message_id,
        "date": "2026-08-31T12:00:00+08:00",
        "sender": sender_value,
        "text": url,
        "caption": None,
        "entities": [],
        "reply_to_message_id": reply,
        "forward_origin": None,
        "media": {"media_type": "photo", "photo_id": 7000 + message_id} if photo else None,
    }


class SvipResourceReplyTests(unittest.TestCase):
    def test_required_synthetic_matrix(self):
        rows = [
            message(1, sender_value=sender(is_admin=True)),
            message(2, sender_value=sender(sender_id=CHAT_ID, sender_type="anonymous_admin", posted_as_chat_id=CHAT_ID, is_creator=None, is_admin=True, anonymous_admin=True, role_basis="telegram_anonymous_admin")),
            message(3, sender_value=sender(sender_id=CHAT_ID, sender_type="chat", posted_as_chat_id=CHAT_ID, is_creator=None, is_admin=None, role_basis="telegram_sender_peer")),
            message(4, sender_value=sender()),
            message(5, sender_value=sender(sender_id=None, sender_type="unknown", is_creator=None, is_admin=None, role_basis="telegram_message_fields", unknown_reason="telegram_sender_not_provided"), reply=88, photo=True),
            message(6, sender_value=sender(sender_id=None, sender_type="unknown", is_creator=None, is_admin=None, role_basis="telegram_message_fields", unknown_reason="telegram_sender_not_provided"), reply=88),
            message(7, sender_value=sender(sender_id=None, sender_type="unknown", is_creator=None, is_admin=None, role_basis="telegram_message_fields", unknown_reason="telegram_sender_not_provided"), photo=True),
            message(8, sender_value=sender(sender_id=None, sender_type="unknown", is_creator=None, is_admin=None, role_basis="telegram_message_fields", unknown_reason="forwarded_message_without_actual_sender")),
            message(9, sender_value=sender(is_admin=True), url="https://mypikpak.com.evil.com/s/abc"),
        ]
        result = mod.classify_messages(rows, expected_chat_id=CHAT_ID)
        self.assertEqual(result["summary"]["verified_moderator_message_count"], 3)
        self.assertEqual(result["summary"]["trusted_official_reply_message_count"], 1)
        self.assertEqual(result["summary"]["primary_message_count"], 4)
        self.assertEqual(result["summary"]["needs_review_message_count"], 3)
        self.assertEqual(result["summary"]["excluded_known_member_count"], 1)
        self.assertEqual(result["summary"]["no_matching_pikpak_url_count"], 1)
        self.assertEqual([row["classification"] for row in result["primary"]], ["verified_moderator", "verified_moderator", "verified_moderator", "trusted_official_reply"])

    def test_owner_is_verified(self):
        row = message(10, sender_value=sender(is_creator=True, is_admin=True))
        classification, evidence = mod.classify_message(row, expected_chat_id=CHAT_ID)
        self.assertEqual(classification, "verified_moderator")
        self.assertEqual(evidence["reason"], "telegram_current_owner")

    def test_missing_sender_without_context_is_excluded(self):
        row = message(11, sender_value=sender(sender_id=None, sender_type="unknown", is_creator=None, is_admin=None, role_basis="telegram_message_fields", unknown_reason="telegram_sender_not_provided"))
        classification, evidence = mod.classify_message(row, expected_chat_id=CHAT_ID)
        self.assertEqual(classification, "excluded_insufficient_evidence")
        self.assertEqual(evidence["reason"], "missing_sender_without_reply_or_photo")

    def test_forward_origin_never_promotes_sender(self):
        row = message(12, sender_value=sender(sender_id=None, sender_type="unknown", is_creator=None, is_admin=None, role_basis="telegram_message_fields", unknown_reason="forwarded_message_without_actual_sender"))
        row["forward_origin"] = {"sender_type": "user", "is_admin": True, "sender_id": 999}
        classification, evidence = mod.classify_message(row, expected_chat_id=CHAT_ID)
        self.assertEqual(classification, "needs_review")
        self.assertEqual(evidence["reason"], "forward_origin_is_not_actual_sender")

    def test_known_member_is_excluded_even_with_link(self):
        result = mod.classify_messages([message(13, sender_value=sender())], expected_chat_id=CHAT_ID)
        self.assertEqual(result["summary"]["excluded_known_member_count"], 1)
        self.assertEqual(result["primary"], [])
        self.assertEqual(result["needs_review"], [])

    def test_domain_parsing_accepts_real_subdomain_and_rejects_lookalike(self):
        self.assertTrue(mod.is_pikpak_url("https://cdn.mypikpak.com/path"))
        self.assertTrue(mod.is_pikpak_url("https://MYPiKPAK.com/path"))
        self.assertFalse(mod.is_pikpak_url("https://mypikpak.com.evil.com/path"))
        self.assertFalse(mod.is_pikpak_url("https://notmypikpak.com/path"))

    def test_wrong_chat_id_is_never_processed(self):
        result = mod.classify_messages([message(14, sender_value=sender(is_admin=True), chat_id=CHAT_ID - 1)], expected_chat_id=CHAT_ID)
        self.assertEqual(result["summary"]["wrong_chat_excluded_count"], 1)
        self.assertEqual(result["primary"], [])

    def test_output_does_not_fabricate_sender_id(self):
        row = message(15, sender_value=sender(sender_id=None, sender_type="unknown", is_creator=None, is_admin=None, unknown_reason="telegram_sender_not_provided"), reply=1, photo=True)
        record = mod.classify_messages([row], expected_chat_id=CHAT_ID)["primary"][0]
        self.assertNotIn("sender_id", record)
        for field in ("message_id", "date", "pikpak_url", "classification", "evidence"):
            self.assertIn(field, record)

    def test_tgctl_command_is_read_only_and_does_not_use_sender_role(self):
        command = mod.build_tgctl_command("tgctl.exe", chat_id=CHAT_ID, page_limit=500, since="2026-08-01T00:00:00+08:00")
        self.assertIn("messages", command)
        self.assertIn("history", command)
        self.assertNotIn("search", command)
        self.assertNotIn("--url-domain", command)
        self.assertNotIn("--sender-role", command)
        self.assertNotIn("download", command)
        self.assertNotIn("send", command)
        self.assertNotIn("forward", command)


if __name__ == "__main__":
    unittest.main()
