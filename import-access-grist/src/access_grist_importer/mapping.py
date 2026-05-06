from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


ACCESS_DATE_COLUMN = "Date_Temps"
ACCESS_DAYS_COLUMN = "Temps"
ACCESS_PROJECT_COLUMN = "T_fk_ID_Affaire"
ACCESS_COLLABORATOR_COLUMN = "T_fk_ID_Collaborateur"

TEAM_ID_COLUMN = "IdTrefle"
TEAM_NAME_COLUMN = "PrenonNom"


@dataclass
class ImportSummary:
    access_rows_read: int = 0
    records_prepared: int = 0
    skipped_missing_project: int = 0
    skipped_missing_collaborator: int = 0
    skipped_unknown_collaborator: int = 0
    skipped_invalid_date: int = 0
    skipped_invalid_time: int = 0
    deleted_records: int = 0
    inserted_records: int = 0
    dry_run: bool = True
    unknown_collaborators: set[str] = field(default_factory=set)

    @property
    def skipped_total(self) -> int:
        return (
            self.skipped_missing_project
            + self.skipped_missing_collaborator
            + self.skipped_unknown_collaborator
            + self.skipped_invalid_date
            + self.skipped_invalid_time
        )


def normalize_identifier(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return str(int(value))

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value).strip()

    if isinstance(value, Decimal):
        return str(int(value)) if value == value.to_integral_value() else str(value)

    text = str(value).strip()
    if not text:
        return ""

    try:
        decimal_value = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return text

    if decimal_value == decimal_value.to_integral_value():
        return str(int(decimal_value))

    return text


def normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def get_row_value(row: dict[str, Any], column_name: str) -> Any:
    if column_name in row:
        return row.get(column_name)

    normalized_column_name = column_name.strip().lower()
    for key, value in row.items():
        if str(key).strip().lower() == normalized_column_name:
            return value

    return None


def parse_days(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value if value > 0 else None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        decimal_value = Decimal(str(value))
        return decimal_value if decimal_value > 0 else None

    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return None

    try:
        decimal_value = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None

    return decimal_value if decimal_value > 0 else None


def parse_access_date(value: Any) -> date | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    date_formats = (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
    )

    for date_format in date_formats:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue

    return None


def format_month(value: Any) -> str:
    parsed_date = parse_access_date(value)
    if not parsed_date:
        return ""

    return f"{parsed_date.month:02d}/{parsed_date.year}"


def decimal_to_grist_number(value: Decimal) -> int | float:
    rounded = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP).normalize()
    if rounded == rounded.to_integral_value():
        return int(rounded)
    return float(rounded)


def build_team_index(team_records: list[dict[str, Any]]) -> dict[str, str]:
    team_index: dict[str, str] = {}

    for record in team_records:
        fields = record.get("fields", record)
        if not isinstance(fields, dict):
            continue

        collaborator_id = normalize_identifier(fields.get(TEAM_ID_COLUMN))
        name = normalize_text(fields.get(TEAM_NAME_COLUMN))
        if collaborator_id and name and collaborator_id not in team_index:
            team_index[collaborator_id] = name

    return team_index


def build_time_real_records(
    access_rows: list[dict[str, Any]],
    team_index: dict[str, str],
) -> tuple[list[dict[str, Any]], ImportSummary]:
    summary = ImportSummary(access_rows_read=len(access_rows))
    grouped_days: "OrderedDict[tuple[str, str, str], Decimal]" = OrderedDict()

    for row in access_rows:
        project_number = normalize_identifier(get_row_value(row, ACCESS_PROJECT_COLUMN))
        collaborator_id = normalize_identifier(
            get_row_value(row, ACCESS_COLLABORATOR_COLUMN)
        )

        if not project_number:
            summary.skipped_missing_project += 1
            continue

        if not collaborator_id:
            summary.skipped_missing_collaborator += 1
            continue

        collaborator_name = team_index.get(collaborator_id)
        if not collaborator_name:
            summary.skipped_unknown_collaborator += 1
            summary.unknown_collaborators.add(collaborator_id)
            continue

        month = format_month(get_row_value(row, ACCESS_DATE_COLUMN))
        if not month:
            summary.skipped_invalid_date += 1
            continue

        days = parse_days(get_row_value(row, ACCESS_DAYS_COLUMN))
        if days is None:
            summary.skipped_invalid_time += 1
            continue

        key = (project_number, collaborator_id, month)
        grouped_days[key] = grouped_days.get(key, Decimal("0")) + days

    records = [
        {
            "NumeroProjet": project_number,
            "ID_Collaborateur": collaborator_id,
            "Mois": month,
            "Allocation_Days": decimal_to_grist_number(days),
            "Name": team_index[collaborator_id],
        }
        for (project_number, collaborator_id, month), days in sorted(
            grouped_days.items(),
            key=lambda item: (
                item[0][0],
                item[0][1],
                item[0][2][3:],
                item[0][2][:2],
            ),
        )
    ]

    summary.records_prepared = len(records)
    return records, summary
