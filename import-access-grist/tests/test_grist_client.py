from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from access_grist_importer.grist_client import (  # noqa: E402
    DEFAULT_CHUNK_SIZE,
    GristClient,
    GristConfig,
)


class FakeResponse:
    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload or {"records": []}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class GristClientProgressTests(unittest.TestCase):
    def test_add_records_reports_progress_by_chunk(self) -> None:
        config = GristConfig(
            server_url="https://example.test",
            api_key="token",
            doc_id="doc",
        )
        client = GristClient(config)
        records = [{"Name": f"Person {index}"} for index in range(DEFAULT_CHUNK_SIZE + 2)]
        progress_events: list[tuple[str, int, int, str]] = []

        with patch(
            "access_grist_importer.grist_client.requests.post",
            return_value=FakeResponse(),
        ) as post_mock:
            client.add_records(
                "TimeReal",
                records,
                on_progress=lambda *event: progress_events.append(event),
            )

        self.assertEqual(post_mock.call_count, 2)
        self.assertEqual(progress_events[0][0], "insert")
        self.assertEqual(progress_events[0][1], DEFAULT_CHUNK_SIZE)
        self.assertEqual(progress_events[0][2], len(records))
        self.assertEqual(progress_events[-1][1], len(records))


if __name__ == "__main__":
    unittest.main()

