from __future__ import annotations

from pathlib import Path
from tkinter import Tk, filedialog, messagebox

from .importer import format_summary, prepare_import, replace_time_real
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
        prepared_import = prepare_import(database_path, settings)
    except Exception as error:
        messagebox.showerror(
            "Import impossible",
            f"Impossible de preparer l'import.\n\n{error}",
        )
        return

    target_table = settings.grist.resolved_time_real_table_id
    summary_text = (
        "Fichier Access selectionne :\n"
        f"{database_path}\n\n"
        f"Table Access source : {settings.access.source_table or 'Temps'}\n"
        f"Table Grist cible : {target_table}\n\n"
        f"{format_summary(prepared_import.summary)}"
    )

    if settings.import_options.dry_run:
        messagebox.showinfo("Simulation import TimeReal", summary_text)
        return

    confirmed = messagebox.askyesno(
        "Confirmer le remplacement TimeReal",
        summary_text
        + "\n\nATTENTION : toutes les lignes actuelles de TimeReal seront supprimees "
        "puis remplacees par ces donnees.\n\nContinuer ?",
    )
    if not confirmed:
        return

    try:
        final_summary = replace_time_real(prepared_import, settings)
    except Exception as error:
        messagebox.showerror(
            "Import Grist impossible",
            f"Erreur pendant le remplacement de TimeReal.\n\n{error}",
        )
        return

    messagebox.showinfo(
        "Import TimeReal termine",
        format_summary(final_summary),
    )
