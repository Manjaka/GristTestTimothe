from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config.json"
EMBEDDED_CONFIG_PATH = (
    ROOT_DIR / "src" / "access_grist_importer" / "_embedded_config.py"
)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(
            "config.json introuvable. Cree-le depuis config.example.json avant de builder."
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_embedded_config(config: dict) -> None:
    EMBEDDED_CONFIG_PATH.write_text(
        "# Fichier genere par build_exe.py. Ne pas modifier a la main.\n"
        f"CONFIG = {config!r}\n",
        encoding="utf-8",
    )


def build_exe() -> None:
    config = load_config()
    write_embedded_config(config)
    src_dir = ROOT_DIR / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src_dir)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--paths",
            str(src_dir),
            "--name",
            "ImportAccessGrist",
            "app.py",
        ],
        cwd=ROOT_DIR,
        env=env,
        check=True,
    )


if __name__ == "__main__":
    build_exe()
