# Import Access vers Grist

Petite application Python destinee a importer des donnees depuis un fichier
Access `.accdb` vers une table Grist.

Le flux actuel importe la table Access `Temps` vers la table Grist `TimeReal`.
Les lignes sont groupees par `NumeroProjet + ID_Collaborateur + Mois`, puis
`Temps` est additionne dans `Allocation_Days`.

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

L'application ouvre une fenetre avec :

- un bouton pour choisir le fichier `.accdb` ;
- un bouton `Analyser / Simuler` ou `Importer dans Grist` selon `dry_run` ;
- une barre de progression pendant la lecture Access et le transfert Grist ;
- un resume des lignes lues, preparees, ignorees, supprimees et inserees.

## Configuration

Copier `config.example.json` vers `config.json`, puis renseigner :

- `grist.api_key`
- `grist.server_url`
- `grist.doc_id`
- `grist.time_real_table_id`
- `grist.team_table_id`
- `import.dry_run`
- `grist.verify_ssl` / `grist.ca_bundle` si le reseau d'entreprise intercepte HTTPS

Le fichier `config.json` est ignore par Git pour eviter de versionner la cle API.

`dry_run` vaut `true` par defaut. Dans ce mode, l'application lit Access et
Grist, prepare les lignes, puis affiche un resume sans modifier `TimeReal`.
Pour remplacer les donnees Grist, mettre `dry_run` a `false`.

Si Python affiche une erreur `CERTIFICATE_VERIFY_FAILED`, il faut idealement
renseigner `grist.ca_bundle` avec le chemin du certificat racine de l'entreprise.
En depannage local uniquement, `grist.verify_ssl` peut etre mis a `false`.

## Regles d'import

- Access `Date_Temps` devient Grist `Mois` au format `MM/YYYY`.
- Access `Temps` est additionne dans Grist `Allocation_Days`.
- Access `T_fk_ID_Affaire` devient Grist `NumeroProjet`.
- Access `T_fk_ID_Collaborateur` devient Grist `ID_Collaborateur`.
- Le collaborateur est conserve uniquement si `T_fk_ID_Collaborateur` existe
  dans Grist `Team.IdTrefle`.
- Grist `TimeReal.Name` est rempli avec `Team.PrenonNom`.
- Quand `dry_run` vaut `false`, toutes les lignes existantes de `TimeReal`
  sont supprimees, puis remplacees par les lignes preparees.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Export `.exe`

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe build_exe.py
```

Le script lit `config.json`, l'embarque dans l'application, puis cree
`dist/ImportAccessGrist.exe`.

Pour l'envoyer a quelqu'un, fournir seulement :

```text
ImportAccessGrist/
  ImportAccessGrist.exe
```

En mode `.exe`, l'application lit d'abord un eventuel `config.json` place a
cote de l'executable, puis utilise la config embarquee si aucun fichier externe
n'est present. En mode developpement, elle garde le comportement actuel et lit
`config.json` a la racine de `import-access-grist`.

Attention : embarquer la config veut dire que la cle API est incluse dans le
`.exe`. Utiliser une cle dediee et limitee au besoin d'import.

## Notes

La lecture `.accdb` utilisera `pyodbc`. Sur Windows, il faut que le driver
Access soit installe :

```text
Microsoft Access Driver (*.mdb, *.accdb)
```
