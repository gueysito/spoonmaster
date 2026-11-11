"""Bundled ladder data, bounded scout dispatch, private cache and explicit review."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from spoonmaster.locales import (
    LocaleService,
    LocaleStore,
    bundled,
    place,
    source_url,
)
from spoonmaster.taste import TasteError, TasteStore
from spoonmaster.taste_service import TasteService

SOURCES = [
    {
        "name": "Synthetic dining guide",
        "url": "https://example.com/dining",
        "role": "quality",
        "reason": "User-provided local guide; trust still needs review.",
    }
]


def response(url="https://example.com/dining"):
    return json.dumps(
        {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Synthetic local guide",
                        "url": url,
                        "description": "An attributed snippet.",
                    }
                ]
            },
        }
    )


class LocaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "data"
        self.clock = [0]
        self.taste = TasteService(
            lambda: self.path,
            clock=lambda: self.clock[0],
            identity=lambda session: None,
        )
        self.taste.bind("chat", "local-cli")
        self.calls = []

        def dispatch(name, args):
            self.calls.append((name, args))
            return response()

        self.service = LocaleService(self.taste)
        self.store = LocaleStore(self.path / "taste.sqlite3")

    def tool(self, action="get", country="JP", city="Tokyo", session="chat", **extras):
        return json.loads(
            self.service.tool(
                {"action": action, "country_code": country, "city": city, **extras},
                session_id=session,
            )
        )

    def confirm(self, proposal, session="chat"):
        result = self.service.command(
            proposal["confirmation"].removeprefix("/spoon "), platform="cli", session_id=session
        )
        return json.loads(result) if result.startswith("{") else {"saved": True, "text": result}

    def test_japan_and_other_bundled_ladders_load_as_data_without_network_or_storage(self):
        result = self.tool()
        self.assertEqual(result["status"], "bundled")
        self.assertEqual(result["ladder"]["sources"][0]["name"], "Tabelog")
        self.assertEqual(result["ladder"]["sources"][-1]["access"], "disabled")
        self.assertEqual(result["ladder"]["sources"][1]["access"], "link_only")
        self.assertFalse(self.calls)
        self.assertFalse(self.path.exists())
        for country in ("TH", "ID"):
            self.assertEqual(bundled(country)["status"], "bundled")
        self.assertEqual(bundled("KR")["status"], "scout_needed")

    def test_proposal_needs_direct_confirmation_and_survives_new_session_after_saving(self):
        result = self.tool("propose", "PT", "Lisbon", sources=SOURCES)
        self.assertFalse(self.path.exists())
        self.assertEqual(self.confirm(result, "other")["error"], "confirmation_expired")
        self.assertTrue(self.confirm(result)["saved"])
        self.taste.bind("later", "local-cli")
        saved = self.tool(country="PT", city="lisbon", session="later")
        self.assertEqual(saved["status"], "confirmed")
        self.assertEqual(saved["saved_city_ladder"]["sources"], SOURCES)
        self.assertIsNone(TasteStore(self.store.path).read("local-cli"))

    def test_saved_ladders_are_owner_isolated_and_deletion_is_targeted(self):
        self.confirm(self.tool("propose", "PT", "Lisbon", sources=SOURCES))
        self.taste.bind("intruder", "other-owner")
        self.assertIsNone(
            self.tool(country="PT", city="Lisbon", session="intruder")["saved_city_ladder"]
        )
        self.confirm(self.tool("propose", "ES", "Madrid", sources=SOURCES))
        self.service.command("locale forget PT Lisbon", platform="cli", session_id="chat")
        self.assertIsNone(self.store.read_city("local-cli", place("PT", "Lisbon")))
        self.assertIsNotNone(self.store.read_city("local-cli", place("ES", "Madrid")))
        TasteStore(self.store.path).control("local-cli", "delete")
        self.assertIsNone(self.store.read_city("local-cli", place("ES", "Madrid")))

    def test_unsafe_urls_and_access_escalation_are_rejected(self):
        for url in (
            "http://example.com",
            "https://127.0.0.1",
            "https://localhost",
            "https://host.local",
            "https://user:secret@example.com",
            "https://example.com:8443",
            "https://example.com/?key=x",
            "https://example.com/#secret",
            "https://example.com/[click]",
            "javascript:alert(1)",
        ):
            with self.subTest(url=url):
                self.assertFalse(source_url(url))
                self.assertEqual(
                    self.tool("propose", "PT", "Lisbon", sources=[{**SOURCES[0], "url": url}])[
                        "error"
                    ],
                    "invalid_sources",
                )
        self.assertEqual(
            self.tool("propose", "PT", "Lisbon", sources=[{**SOURCES[0], "access": "scrape"}])[
                "error"
            ],
            "invalid_sources",
        )
        self.assertFalse(self.path.exists())

    def test_invalid_city_or_scope_never_dispatches(self):
        for city in ("", "Tokyo site:private.com", "35.1,139.1", "Tokyo\nprivate", "x" * 81):
            self.assertEqual(self.tool("get", city=city)["error"], "invalid_locale")
        self.assertEqual(self.tool("get", session=None)["error"], "private_context_required")
        self.assertFalse(self.calls)

    def test_expired_and_cross_profile_tokens_fail_without_saving(self):
        result = self.tool("propose", "PT", "Lisbon", sources=SOURCES)
        self.clock[0] += 901
        self.assertEqual(self.confirm(result)["error"], "confirmation_expired")
        result = self.tool("propose", "PT", "Lisbon", sources=SOURCES)
        self.taste.state_directory = lambda: self.path / "other"
        self.assertEqual(self.confirm(result)["error"], "confirmation_expired")
        self.assertFalse(self.path.exists())

    def test_stale_saved_ladder_requires_review(self):
        self.confirm(self.tool("propose", "PT", "Lisbon", sources=SOURCES))
        with self.store.transaction() as db:
            row = db.execute("SELECT data FROM locales").fetchone()
            value = json.loads(row[0])
            value["reviewed_at"] = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
            db.execute("UPDATE locales SET data=?", (json.dumps(value),))
        self.assertEqual(self.tool(country="PT", city="Lisbon")["status"], "review_required")

    def test_replacement_conflict_and_failed_write_do_not_claim_saved(self):
        self.confirm(self.tool("propose", "PT", "Lisbon", sources=SOURCES))
        pending = self.tool("propose", "PT", "Lisbon", sources=SOURCES)
        self.store.forget_city("local-cli", place("PT", "Lisbon"))
        self.assertEqual(self.confirm(pending)["error"], "locale_changed")
        pending = self.tool("propose", "PT", "Lisbon", sources=SOURCES)
        with patch.object(LocaleStore, "save_city", side_effect=TasteError("storage_unavailable")):
            self.assertFalse(self.confirm(pending)["saved"])
        self.assertTrue(self.confirm(pending)["saved"])
