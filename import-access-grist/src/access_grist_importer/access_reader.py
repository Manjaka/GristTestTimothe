from __future__ import annotations

from pathlib import Path
from typing import Any

import pyodbc


ACCESS_DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"


def build_connection_string(database_path: Path) -> str:
    return f"DRIVER={{{ACCESS_DRIVER}}};DBQ={database_path};"


def list_tables(database_path: Path) -> list[str]:
    with pyodbc.connect(build_connection_string(database_path)) as connection:
        cursor = connection.cursor()
        return sorted(
            row.table_name
            for row in cursor.tables(tableType="TABLE")
            if row.table_name and not str(row.table_name).startswith("MSys")
        )


def fetch_rows(database_path: Path, table_name: str) -> list[dict[str, Any]]:
    if not table_name:
        raise ValueError("Le nom de table Access est obligatoire.")

    with pyodbc.connect(build_connection_string(database_path)) as connection:
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM [{table_name}]")
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

