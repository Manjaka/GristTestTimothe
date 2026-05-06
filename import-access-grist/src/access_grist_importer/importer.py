from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .access_reader import fetch_rows
from .grist_client import GristClient
from .mapping import ImportSummary, build_team_index, build_time_real_records
from .settings import Settings


@dataclass(frozen=True)
class PreparedImport:
    records: list[dict[str, Any]]
    summary: ImportSummary


def prepare_import(database_path: Path, settings: Settings) -> PreparedImport:
    grist_client = GristClient(settings.grist)
    team_records = grist_client.fetch_records(settings.grist.team_table_id)
    team_index = build_team_index(team_records)

    if not team_index:
        raise ValueError(
            "Aucun collaborateur exploitable trouve dans Grist Team "
            "(colonnes attendues : IdTrefle et PrenonNom)."
        )

    access_rows = fetch_rows(database_path, settings.access.source_table or "Temps")
    records, summary = build_time_real_records(access_rows, team_index)
    summary.dry_run = settings.import_options.dry_run
    return PreparedImport(records=records, summary=summary)


def replace_time_real(prepared_import: PreparedImport, settings: Settings) -> ImportSummary:
    grist_client = GristClient(settings.grist)
    target_table_id = settings.grist.resolved_time_real_table_id
    existing_records = grist_client.fetch_records(target_table_id)
    record_ids = [
        int(record.get("id"))
        for record in existing_records
        if str(record.get("id", "")).strip().isdigit()
    ]

    if record_ids:
        grist_client.delete_records(target_table_id, record_ids)

    if prepared_import.records:
        grist_client.add_records(target_table_id, prepared_import.records)

    prepared_import.summary.deleted_records = len(record_ids)
    prepared_import.summary.inserted_records = len(prepared_import.records)
    prepared_import.summary.dry_run = False
    return prepared_import.summary


def format_summary(summary: ImportSummary) -> str:
    unknown_collaborators = ", ".join(sorted(summary.unknown_collaborators))
    if not unknown_collaborators:
        unknown_collaborators = "Aucun"

    lines = [
        f"Lignes Access lues : {summary.access_rows_read}",
        f"Lignes TimeReal preparees : {summary.records_prepared}",
        f"Lignes ignorees : {summary.skipped_total}",
        f"  - Affaire manquante : {summary.skipped_missing_project}",
        f"  - Collaborateur manquant : {summary.skipped_missing_collaborator}",
        f"  - Collaborateur absent de Team : {summary.skipped_unknown_collaborator}",
        f"  - Date_Temps invalide : {summary.skipped_invalid_date}",
        f"  - Temps vide ou invalide : {summary.skipped_invalid_time}",
        f"Collaborateurs inconnus : {unknown_collaborators}",
    ]

    if summary.dry_run:
        lines.append("")
        lines.append("Mode dry-run actif : aucune donnee Grist ne sera modifiee.")
    else:
        lines.extend(
            [
                "",
                f"Lignes TimeReal supprimees : {summary.deleted_records}",
                f"Lignes TimeReal inserees : {summary.inserted_records}",
            ]
        )

    return "\n".join(lines)

