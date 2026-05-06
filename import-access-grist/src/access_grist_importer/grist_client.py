from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import requests
from requests import HTTPError


DEFAULT_CHUNK_SIZE = 500
ProgressCallback = Callable[[str, int, int, str], None]


@dataclass(frozen=True)
class GristConfig:
    server_url: str
    api_key: str
    doc_id: str
    table_id: str = "TimeReal"
    time_real_table_id: str = "TimeReal"
    team_table_id: str = "Team"
    verify_ssl: bool = True
    ca_bundle: str = ""

    @property
    def resolved_time_real_table_id(self) -> str:
        return self.time_real_table_id or self.table_id or "TimeReal"


class GristClient:
    def __init__(self, config: GristConfig) -> None:
        self.config = config

    def _validate_config(self) -> None:
        missing = [
            name
            for name, value in {
                "grist.server_url": self.config.server_url,
                "grist.api_key": self.config.api_key,
                "grist.doc_id": self.config.doc_id,
            }.items()
            if not str(value or "").strip()
        ]
        if missing:
            raise ValueError(
                "Configuration Grist incomplete : " + ", ".join(missing)
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _request_verify(self) -> bool | str:
        if self.config.ca_bundle:
            return self.config.ca_bundle
        return self.config.verify_ssl

    def records_url(self, table_id: str) -> str:
        self._validate_config()
        if not table_id:
            raise ValueError("Le nom de table Grist est obligatoire.")

        server_url = self.config.server_url.rstrip("/")
        return (
            f"{server_url}/api/docs/{self.config.doc_id}"
            f"/tables/{table_id}/records"
        )

    def fetch_records(
        self,
        table_id: str,
        on_progress: ProgressCallback | None = None,
    ) -> list[dict[str, Any]]:
        if on_progress:
            on_progress("fetch", 0, 0, f"Lecture Grist {table_id}")

        response = requests.get(
            self.records_url(table_id),
            headers=self._headers(),
            verify=self._request_verify(),
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        records = payload.get("records", [])
        normalized_records = records if isinstance(records, list) else []
        if on_progress:
            on_progress(
                "fetch",
                len(normalized_records),
                len(normalized_records),
                f"Lecture Grist {table_id} terminee",
            )
        return normalized_records

    def delete_records(
        self,
        table_id: str,
        record_ids: list[int],
        on_progress: ProgressCallback | None = None,
    ) -> None:
        ids: list[int] = []
        for record_id in record_ids:
            try:
                normalized_id = int(record_id)
            except (TypeError, ValueError):
                continue
            if normalized_id > 0:
                ids.append(normalized_id)

        if not ids:
            if on_progress:
                on_progress("delete", 0, 0, "Aucune ligne TimeReal a supprimer")
            return

        deleted_count = 0
        for start_index in range(0, len(ids), DEFAULT_CHUNK_SIZE):
            chunk = ids[start_index : start_index + DEFAULT_CHUNK_SIZE]
            try:
                response = requests.post(
                    f"{self.records_url(table_id)}/delete",
                    headers=self._headers(),
                    json=chunk,
                    verify=self._request_verify(),
                    timeout=30,
                )
                response.raise_for_status()
            except HTTPError as error:
                if error.response is None or error.response.status_code != 404:
                    raise

                response = requests.post(
                    self.data_delete_url(table_id),
                    headers=self._headers(),
                    json=chunk,
                    verify=self._request_verify(),
                    timeout=30,
                )
                response.raise_for_status()

            deleted_count += len(chunk)
            if on_progress:
                on_progress(
                    "delete",
                    deleted_count,
                    len(ids),
                    f"Suppression TimeReal {deleted_count}/{len(ids)}",
                )

    def data_delete_url(self, table_id: str) -> str:
        self._validate_config()
        if not table_id:
            raise ValueError("Le nom de table Grist est obligatoire.")

        server_url = self.config.server_url.rstrip("/")
        return (
            f"{server_url}/api/docs/{self.config.doc_id}"
            f"/tables/{table_id}/data/delete"
        )

    def add_records(
        self,
        table_id: str,
        records: list[dict[str, Any]],
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        if not records:
            if on_progress:
                on_progress("insert", 0, 0, "Aucune ligne TimeReal a inserer")
            return {"records": []}

        created_records: list[dict[str, Any]] = []
        for start_index in range(0, len(records), DEFAULT_CHUNK_SIZE):
            chunk = records[start_index : start_index + DEFAULT_CHUNK_SIZE]
            response = requests.post(
                self.records_url(table_id),
                headers=self._headers(),
                json={
                    "records": [
                        {
                            "fields": record,
                        }
                        for record in chunk
                    ]
                },
                verify=self._request_verify(),
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            created_records.extend(payload.get("records", []))
            if on_progress:
                on_progress(
                    "insert",
                    min(start_index + len(chunk), len(records)),
                    len(records),
                    f"Insertion TimeReal {min(start_index + len(chunk), len(records))}/{len(records)}",
                )

        return {"records": created_records}
