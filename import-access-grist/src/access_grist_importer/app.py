from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import (
    END,
    DISABLED,
    NORMAL,
    DoubleVar,
    StringVar,
    Tk,
    filedialog,
    messagebox,
)
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

from .importer import (
    PreparedImport,
    format_summary,
    prepare_import,
    replace_time_real,
)
from .settings import Settings, load_settings


class ImportAccessGristApp:
    def __init__(self, root: Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self.events: Queue[tuple[str, Any]] = Queue()
        self.selected_file: Path | None = None
        self.running = False
        self.progress_indeterminate = False

        self.root.title("Import Access vers Grist")
        self.root.geometry("760x560")
        self.root.minsize(680, 480)

        self.file_var = StringVar(value="Aucun fichier selectionne")
        self.status_var = StringVar(value="Pret")
        self.progress_var = DoubleVar(value=0)

        self._build_ui()
        self.root.after(100, self._process_events)

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main_frame,
            text="Import Access vers Grist - TimeReal",
            font=("Segoe UI", 13, "bold"),
        )
        title_label.pack(anchor="w")

        config_label = ttk.Label(
            main_frame,
            text=(
                f"Source Access : {self.settings.access.source_table or 'Temps'} | "
                f"Cible Grist : {self.settings.grist.resolved_time_real_table_id}"
            ),
        )
        config_label.pack(anchor="w", pady=(4, 14))

        file_frame = ttk.LabelFrame(main_frame, text="Fichier Access", padding=12)
        file_frame.pack(fill="x")

        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x")

        file_entry = ttk.Entry(file_row, textvariable=self.file_var, state="readonly")
        file_entry.pack(side="left", fill="x", expand=True)

        self.choose_button = ttk.Button(
            file_row,
            text="Choisir un fichier Access",
            command=self.choose_file,
        )
        self.choose_button.pack(side="left", padx=(10, 0))

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(14, 8))

        action_label = (
            "Analyser / Simuler"
            if self.settings.import_options.dry_run
            else "Importer dans Grist"
        )
        self.run_button = ttk.Button(
            action_frame,
            text=action_label,
            command=self.start_prepare,
        )
        self.run_button.pack(side="left")

        mode_label = (
            "Mode simulation : aucune donnee Grist ne sera modifiee."
            if self.settings.import_options.dry_run
            else "Mode import : TimeReal sera remplace apres confirmation."
        )
        ttk.Label(action_frame, text=mode_label).pack(side="left", padx=(12, 0))

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(8, 0))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.pack(fill="x")

        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(anchor="w", pady=(6, 12))

        summary_frame = ttk.LabelFrame(main_frame, text="Resume", padding=8)
        summary_frame.pack(fill="both", expand=True)

        self.summary_text = ScrolledText(
            summary_frame,
            wrap="word",
            height=18,
            font=("Consolas", 9),
        )
        self.summary_text.pack(fill="both", expand=True)
        self._set_summary(
            "Selectionne un fichier .accdb, puis lance l'analyse."
        )

    def choose_file(self) -> None:
        if self.running:
            return

        file_path = filedialog.askopenfilename(
            parent=self.root,
            title="Selectionner un fichier Access",
            filetypes=[
                ("Base Access", "*.accdb"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not file_path:
            return

        self.selected_file = Path(file_path)
        self.file_var.set(str(self.selected_file))
        self.status_var.set("Fichier pret pour l'analyse")

    def start_prepare(self) -> None:
        if self.running:
            return

        if not self.selected_file:
            messagebox.showwarning(
                "Fichier manquant",
                "Selectionne d'abord un fichier Access .accdb.",
                parent=self.root,
            )
            return

        self._set_busy(True)
        self._set_summary("")
        self._set_progress("prepare", 0, 0, "Demarrage de l'analyse")

        Thread(
            target=self._prepare_worker,
            args=(self.selected_file,),
            daemon=True,
        ).start()

    def _prepare_worker(self, database_path: Path) -> None:
        try:
            prepared_import = prepare_import(
                database_path,
                self.settings,
                on_progress=self._emit_progress,
            )
        except Exception as error:
            self.events.put(("error", ("Import impossible", str(error))))
            return

        target_table = self.settings.grist.resolved_time_real_table_id
        summary_text = (
            "Fichier Access selectionne :\n"
            f"{database_path}\n\n"
            f"Table Access source : {self.settings.access.source_table or 'Temps'}\n"
            f"Table Grist cible : {target_table}\n\n"
            f"{format_summary(prepared_import.summary, include_transfer_counts=False)}"
        )

        if self.settings.import_options.dry_run:
            self.events.put(("done", summary_text))
            return

        self.events.put(("confirm", (prepared_import, summary_text)))

    def _replace_worker(self, prepared_import: PreparedImport) -> None:
        try:
            final_summary = replace_time_real(
                prepared_import,
                self.settings,
                on_progress=self._emit_progress,
            )
        except Exception as error:
            self.events.put(("error", ("Import Grist impossible", str(error))))
            return

        self.events.put(("done", format_summary(final_summary)))

    def _emit_progress(
        self,
        step: str,
        current: int,
        total: int,
        message: str,
    ) -> None:
        self.events.put(("progress", (step, current, total, message)))

    def _process_events(self) -> None:
        try:
            while True:
                event_name, payload = self.events.get_nowait()
                if event_name == "progress":
                    step, current, total, message = payload
                    self._set_progress(step, current, total, message)
                elif event_name == "confirm":
                    prepared_import, summary_text = payload
                    self._handle_confirmation(prepared_import, summary_text)
                elif event_name == "done":
                    self._set_progress("done", 1, 1, "Termine")
                    self._set_summary(payload)
                    self.status_var.set("Operation terminee")
                    self._set_busy(False)
                elif event_name == "error":
                    title, message = payload
                    self._set_progress("error", 0, 1, "Erreur")
                    self._set_summary(f"{title}\n\n{message}")
                    self.status_var.set("Erreur")
                    self._set_busy(False)
                    messagebox.showerror(title, message, parent=self.root)
        except Empty:
            pass

        self.root.after(100, self._process_events)

    def _handle_confirmation(
        self,
        prepared_import: PreparedImport,
        summary_text: str,
    ) -> None:
        self._set_summary(summary_text)
        confirmed = messagebox.askyesno(
            "Confirmer le remplacement TimeReal",
            summary_text
            + "\n\nATTENTION : toutes les lignes actuelles de TimeReal seront "
            "supprimees puis remplacees par ces donnees.\n\nContinuer ?",
            parent=self.root,
        )
        if not confirmed:
            self.status_var.set("Import annule")
            self._set_busy(False)
            self._set_progress("cancel", 0, 1, "Import annule")
            return

        self._set_progress("replace", 0, 0, "Remplacement TimeReal")
        Thread(
            target=self._replace_worker,
            args=(prepared_import,),
            daemon=True,
        ).start()

    def _set_busy(self, value: bool) -> None:
        self.running = value
        state = DISABLED if value else NORMAL
        self.choose_button.configure(state=state)
        self.run_button.configure(state=state)

    def _set_summary(self, text: str) -> None:
        self.summary_text.configure(state=NORMAL)
        self.summary_text.delete("1.0", END)
        if text:
            self.summary_text.insert("1.0", text)
        self.summary_text.configure(state=DISABLED)

    def _set_progress(
        self,
        step: str,
        current: int,
        total: int,
        message: str,
    ) -> None:
        self.status_var.set(message)

        if total and total > 0:
            if self.progress_indeterminate:
                self.progress_bar.stop()
                self.progress_indeterminate = False
            self.progress_bar.configure(mode="determinate")
            self.progress_var.set(max(0, min(100, (current / total) * 100)))
            return

        if not self.progress_indeterminate:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start(12)
            self.progress_indeterminate = True


def main() -> None:
    settings = load_settings()
    root = Tk()
    ImportAccessGristApp(root, settings)
    root.mainloop()
