from __future__ import annotations

from pathlib import Path
from tkinter import Tk, filedialog, messagebox

from .access_reader import list_tables
from .settings import load_settings


def choose_access_file() -> Path | None:
    root = Tk()
    root.withdraw()
    root.update()

    file_path = filedialog.askopenfilename(
        title="Selectionner un fichier Access",
        filetypes=[
            ("Base Access", "*.accdb"),
            ("Tous les fichiers", "*.*"),
        ],
    )
    root.destroy()

    return Path(file_path) if file_path else None


def main() -> None:
    settings = load_settings()
    database_path = choose_access_file()
    if not database_path:
        return

    try:
        tables = list_tables(database_path)
    except Exception as error:
        messagebox.showerror(
            "Lecture Access impossible",
            f"Impossible de lire le fichier Access.\n\n{error}",
        )
        return

    target_table = settings.grist.table_id or "TimeReal"
    messagebox.showinfo(
        "Fichier charge",
        "Fichier Access selectionne :\n"
        f"{database_path}\n\n"
        "Tables detectees :\n"
        f"{', '.join(tables) if tables else 'Aucune table'}\n\n"
        f"Table Grist cible : {target_table}\n\n"
        "Les regles d'import seront ajoutees a l'etape suivante.",
    )

