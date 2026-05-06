from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class GristConfig:
    server_url: str
    api_key: str
    doc_id: str
    table_id: str


class GristClient:
    def __init__(self, config: GristConfig) -> None:
        self.config = config

    @property
    def records_url(self) -> str:
        server_url = self.config.server_url.rstrip("/")
        return (
            f"{server_url}/api/docs/{self.config.doc_id}"
            f"/tables/{self.config.table_id}/records"
        )

    def add_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        if not records:
            return {"records": []}

        response = requests.post(
            self.records_url,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "records": [
                    {
                        "fields": record,
                    }
                    for record in records
                ]
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

