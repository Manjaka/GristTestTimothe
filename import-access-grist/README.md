# Import Access vers Grist

Petite application Python destinee a importer des donnees depuis un fichier
Access `.accdb` vers une table Grist.

## Structure

```text
import-access-grist/
  app.py
  requirements.txt
  config.example.json
  src/
    access_grist_importer/
      __main__.py
      app.py
      access_reader.py
      grist_client.py
      mapping.py
      settings.py
```

## Lancement local

```powershell
cd import-access-grist
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Configuration

Copier `config.example.json` vers `config.json`, puis renseigner :

- `grist.api_key`
- `grist.server_url`
- `grist.doc_id`
- `grist.table_id`

Le fichier `config.json` est ignore par Git pour eviter de versionner la cle API.

## Notes

La lecture `.accdb` utilisera `pyodbc`. Sur Windows, il faut que le driver
Access soit installe :

```text
Microsoft Access Driver (*.mdb, *.accdb)
```

