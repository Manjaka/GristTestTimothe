from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from access_grist_importer.mapping import (  # noqa: E402
    build_team_index,
    build_time_real_records,
    format_month,
)


class TimeRealMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.team_records = [
            {
                "id": 1,
                "fields": {
                    "IdTrefle": "741",
                    "PrenonNom": "Jean-Marie Phaine",
                },
            },
            {
                "id": 2,
                "fields": {
                    "IdTrefle": "616",
                    "PrenonNom": "Dimitri Tarze",
                },
            },
        ]
        self.team_index = build_team_index(self.team_records)

    def test_formats_month_from_access_date(self) -> None:
        self.assertEqual(format_month("2026-03-19T11:00:00.000Z"), "03/2026")
        self.assertEqual(format_month("19/03/2026"), "03/2026")

    def test_reads_access_columns_case_insensitively(self) -> None:
        records, summary = build_time_real_records(
            [
                {
                    "Date_temps": "2026-03-01",
                    "Temps": 2,
                    "T_fk_ID_Affaire": "1455",
                    "T_fk_ID_Collaborateur": "741",
                },
            ],
            self.team_index,
        )

        self.assertEqual(summary.records_prepared, 1)
        self.assertEqual(records[0]["Mois"], "03/2026")

    def test_aggregates_same_project_collaborator_and_month(self) -> None:
        records, summary = build_time_real_records(
            [
                {
                    "Date_Temps": "2026-03-01",
                    "Temps": 2,
                    "T_fk_ID_Affaire": "1455",
                    "T_fk_ID_Collaborateur": "741",
                },
                {
                    "Date_Temps": "2026-03-18",
                    "Temps": "1,5",
                    "T_fk_ID_Affaire": "1455",
                    "T_fk_ID_Collaborateur": "741",
                },
            ],
            self.team_index,
        )

        self.assertEqual(summary.records_prepared, 1)
        self.assertEqual(records[0]["Allocation_Days"], 3.5)
        self.assertEqual(records[0]["Mois"], "03/2026")
        self.assertEqual(records[0]["Name"], "Jean-Marie Phaine")

    def test_keeps_projects_separate_for_same_collaborator_and_month(self) -> None:
        records, summary = build_time_real_records(
            [
                {
                    "Date_Temps": "2026-03-01",
                    "Temps": 2,
                    "T_fk_ID_Affaire": "1455",
                    "T_fk_ID_Collaborateur": "741",
                },
                {
                    "Date_Temps": "2026-03-18",
                    "Temps": 1,
                    "T_fk_ID_Affaire": "9999",
                    "T_fk_ID_Collaborateur": "741",
                },
            ],
            self.team_index,
        )

        self.assertEqual(summary.records_prepared, 2)
        self.assertEqual({record["NumeroProjet"] for record in records}, {"1455", "9999"})

    def test_skips_unknown_collaborator_and_invalid_rows(self) -> None:
        records, summary = build_time_real_records(
            [
                {
                    "Date_Temps": "2026-03-01",
                    "Temps": 2,
                    "T_fk_ID_Affaire": "1455",
                    "T_fk_ID_Collaborateur": "999",
                },
                {
                    "Date_Temps": "pas une date",
                    "Temps": 2,
                    "T_fk_ID_Affaire": "1455",
                    "T_fk_ID_Collaborateur": "741",
                },
                {
                    "Date_Temps": "2026-03-01",
                    "Temps": "",
                    "T_fk_ID_Affaire": "1455",
                    "T_fk_ID_Collaborateur": "741",
                },
            ],
            self.team_index,
        )

        self.assertEqual(records, [])
        self.assertEqual(summary.skipped_unknown_collaborator, 1)
        self.assertEqual(summary.skipped_invalid_date, 1)
        self.assertEqual(summary.skipped_invalid_time, 1)


if __name__ == "__main__":
    unittest.main()
