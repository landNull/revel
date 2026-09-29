import os
import tempfile
import unittest
from pathlib import Path

from revel.adapters.mail import ingest_many, ingest_rfc822, upsert_email, write_mail_env
from revel.store import MemoryGraphStore


class MailAdapterTests(unittest.TestCase):
    def test_upsert_by_message_id(self) -> None:
        store = MemoryGraphStore()
        a = upsert_email(store, subject="Hello", message_id="<a@x>")
        b = upsert_email(store, subject="Hello again", message_id="<a@x>")
        self.assertEqual(a.id, b.id)
        self.assertEqual(a.type, "email")

    def test_rfc822_and_batch(self) -> None:
        store = MemoryGraphStore()
        raw = b"From: ada@ex\nSubject: Re: contract\nMessage-ID: <c@x>\n\nbody\n"
        node = ingest_rfc822(store, raw)
        self.assertEqual(node.title, "Re: contract")
        batch = ingest_many(store, [{"subject": "Two", "message_id": "<d@x>"}])
        self.assertEqual(len(batch), 1)

    def test_mail_env_is_mode_600_and_can_omit_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mail.env"
            os.environ["REVEL_MAIL_ENV"] = str(path)
            written = write_mail_env(
                {"REVEL_IMAP_HOST": "imap.zoho.com", "REVEL_MAIL_PASSWORD": "secret"},
                include_password=False,
            )
            text = written.read_text()
            self.assertNotIn("secret", text)
            self.assertEqual(written.stat().st_mode & 0o777, 0o600)
            written = write_mail_env(
                {"REVEL_IMAP_HOST": "imap.zoho.com", "REVEL_MAIL_PASSWORD": "secret"},
                include_password=True,
            )
            self.assertIn("REVEL_MAIL_PASSWORD=secret", written.read_text())
            del os.environ["REVEL_MAIL_ENV"]


if __name__ == "__main__":
    unittest.main()
