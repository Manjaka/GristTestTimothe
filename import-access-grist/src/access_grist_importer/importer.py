from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .access_reader import fetch_rows
from .grist_client import GristClient, ProgressCallback
from .mapping import ImportSummary, build_team_index, build_time_real_records
from .settings import Settings


@dataclass(frozen=True)
class PreparedImport:
    records: list[dict[str, Any]]
    summary: ImportSummary


def emit_progress(
    on_progress: ProgressCallback | None,
    step: str,
    current: int,
    total: int,
    message: str,
) -> None:
    if on_progress:
        on_progress(step, current, total, message)


def prepare_import(
    database_path: Path,
    settings: Settings,
    on_progress: ProgressCallback | None = None,
) -> PreparedImport:
    grist_client = GristClient(settings.grist)
    emit_progress(on_progress, "team", 0, 0, "Lecture Team Grist")
    team_records = grist_client.fetch_records(
        settings.grist.team_table_id,
        on_progress=on_progress,
    )
    team_index = build_team_index(team_records)

    if not team_index:
        raise ValueError(
            "Aucun collaborateur exploitable trouve dans Grist Team "
            "(colonnes attendues : IdTrefle et PrenonNom)."
        )

    emit_progress(on_progress, "access", 0, 0, "Lecture Access Temps")
    access_rows = fetch_rows(database_path, settings.access.source_table or "Temps")
    emit_progress(
        on_progress,
        "access",
        len(access_rows),
        len(access_rows),
        f"Lecture Access terminee : {len(access_rows)} lignes",
    )
    emit_progress(on_progress, "mapping", 0, 0, "Preparation des lignes TimeReal")
    records, summary = build_time_real_records(access_rows, team_index)
    summary.dry_run = settings.import_options.dry_run
    emit_progress(
        on_progress,
        "mapping",
        len(records),
        len(records),
        f"Preparation terminee : {len(records)} lignes TimeReal",
    )
    return PreparedImport(records=records, summary=summary)


def replace_time_real(
    prepared_import: PreparedImport,
    settings: Settings,
    on_progress: ProgressCallback | None = None,
) -> ImportSummary:
    grist_client = GristClient(settings.grist)
    target_table_id = settings.grist.resolved_time_real_table_id
    emit_progress(on_progress, "existing", 0, 0, "Lecture TimeReal existant")
    existing_records = grist_client.fetch_records(
        target_table_id,
        on_progress=on_progress,
    )
    record_ids = [
        int(record.get("id"))
        for record in existing_records
        if str(record.get("id", "")).strip().isdigit()
    ]

    if record_ids:
        grist_client.delete_records(
            target_table_id,
            record_ids,
            on_progress=on_progress,
        )
    else:
        emit_progress(on_progress, "delete", 0, 0, "Aucune ligne TimeReal a supprimer")

    if prepared_import.records:
        grist_client.add_records(
            target_table_id,
            prepared_import.records,
            on_progress=on_progress,
        )
    else:
        emit_progress(on_progress, "insert", 0, 0, "Aucune ligne TimeReal a inserer")

    prepared_import.summary.deleted_records = len(record_ids)
    prepared_import.summary.inserted_records = len(prepared_import.records)
    prepared_import.summary.dry_run = False
    emit_progress(on_progress, "done", 1, 1, "Import TimeReal termine")
    return prepared_import.summary


def format_summary(
    summary: ImportSummary,
    include_transfer_counts: bool = True,
    max_unknown_collaborators: int = 120,
) -> str:
    unknown_values = sorted(summary.unknown_collaborators)
    visible_unknowns = unknown_values[:max_unknown_collaborators]
    unknown_collaborators = ", ".join(visible_unknowns)
    if len(unknown_values) > len(visible_unknowns):
        unknown_collaborators += (
            f" ... (+{len(unknown_values) - len(visible_unknowns)} autres)"
        )
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
    elif include_transfer_counts:
        lines.extend(
            [
                "",
                f"Lignes TimeReal supprimees : {summary.deleted_records}",
                f"Lignes TimeReal inserees : {summary.inserted_records}",
            ]
        )

    return "\n".join(lines)
