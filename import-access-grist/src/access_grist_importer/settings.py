from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .grist_client import GristConfig


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.json"
CONFIG_EXAMPLE_PATH = ROOT_DIR / "config.example.json"


@dataclass(frozen=True)
class AccessConfig:
    source_table: str = ""


@dataclass(frozen=True)
class ImportConfig:
    dry_run: bool = True


@dataclass(frozen=True)
class Settings:
    grist: GristConfig
    access: AccessConfig
    import_options: ImportConfig


def _read_config() -> dict[str, Any]:
    config_path = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE_PATH
    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_settings() -> Settings:
    raw = _read_config()
    grist = raw.get("grist", {})
    access = raw.get("access", {})
    import_options = raw.get("import", {})

    return Settings(
        grist=GristConfig(
            server_url=str(grist.get("server_url", "")).strip(),
            api_key=str(grist.get("api_key", "")).strip(),
            doc_id=str(grist.get("doc_id", "")).strip(),
            table_id=str(grist.get("table_id", "")).strip(),
            time_real_table_id=str(
                grist.get("time_real_table_id", grist.get("table_id", "TimeReal"))
            ).strip(),
            team_table_id=str(grist.get("team_table_id", "Team")).strip(),
            verify_ssl=bool(grist.get("verify_ssl", True)),
            ca_bundle=str(grist.get("ca_bundle", "")).strip(),
        ),
        access=AccessConfig(
            source_table=str(access.get("source_table", "Temps")).strip(),
        ),
        import_options=ImportConfig(
            dry_run=bool(import_options.get("dry_run", True)),
        ),
    )
