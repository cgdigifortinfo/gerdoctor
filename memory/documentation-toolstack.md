# Dokumentation: Lastenheft, Pflichtenheft und Toolstack

Stand: 2026-07-14

Diese Notiz dokumentiert den erstellten Dokumentationsstand für Lastenheft und
Pflichtenheft der GERdoctor/IHCA Multi-Survey-Plattform.

## Erstellte Dateien

Im Repo wurden folgende Dateien angelegt:

- `docs/lastenheft.md`
- `docs/pflichtenheft.md`
- `docs/toolstack.md`
- `docs/lastenheft.docx`
- `docs/pflichtenheft.docx`
- `scripts/export_docs.sh`
- `scripts/render_charts.sh`

## Inhaltlicher Stand

`docs/lastenheft.md` beschreibt die Software aus Auftraggeber-/Fachsicht:

- Zielbestimmung und Ausgangssituation;
- Stakeholder und Rollen;
- Produktumfang;
- Muss-, Soll- und Kann-Anforderungen;
- Multi-Survey-Fähigkeit;
- generische Survey-/Step-Logik;
- Ärzte- und Pflege-Survey als Beispielszenarien;
- Partner- und Adminfunktionen;
- Upload-/Dateisicherheit;
- Performance- und Betriebsanforderungen;
- Datenschutz und Abnahmekriterien;
- PNG/SVG-Prozessübersicht.

`docs/pflichtenheft.md` beschreibt die technische Umsetzung:

- Systemarchitektur;
- Backend-, Frontend- und Datenbankkomponenten;
- Datenmodell für Survey, User, Step, Progress, Partner Submissions und Files;
- Step Engine und Condition-Logik inklusive generischem Etappenmuster;
- API-Endpunkte für Public, Auth, User, Partner, Admin und Dateien;
- Frontend-Routen und Kernseiten;
- Rechte- und Sicherheitskonzept;
- Performance-Konzept inklusive MongoDB-Indizes;
- Betrieb, Seed, Tests und technische Abnahmekriterien.

`docs/toolstack.md` beschreibt den Dokumentations-Workflow:

- Markdown als Quelldokumentformat;
- Git für Versionierung;
- PNG-Bilddateien für Diagramme; SVG-Quelldateien liegen zusätzlich unter
  `docs/charts/`.
- Pandoc für Export nach DOCX, HTML oder PDF.

## Toolstack-Status

Systemweites `pandoc` konnte in der Codex-Umgebung nicht per `apt` installiert
werden, weil `sudo` ein interaktives Passwort verlangt.

Als funktionierende Alternative wurde das Docker-Image `pandoc/core:latest`
gezogen und getestet:

```bash
docker run --rm pandoc/core --version
```

Ergebnis: `pandoc 3.10`.

Das Export-Skript `scripts/export_docs.sh` nutzt automatisch:

1. lokal installiertes `pandoc`, falls vorhanden;
2. sonst Docker mit `pandoc/core`.

Bei Docker-Export setzt das Skript `--user "$(id -u):$(id -g)"`, damit die
erzeugten Dateien dem lokalen Benutzer gehören.

`scripts/export_docs.sh` ruft vor dem Dokumentexport `scripts/render_charts.sh`
auf. Dieses Skript rendert die SVG-Quellen zu PNG. Wenn lokal kein
`rsvg-convert` existiert, nutzt es `rsvg-convert` im Docker-Image
`pandoc/core` und mountet `/usr/share/fonts`, damit die Diagrammtexte nicht als
Rechtecke gerendert werden.

## Export

DOCX wurde erfolgreich erzeugt:

```bash
scripts/export_docs.sh docx
```

Erzeugte Dateien:

- `docs/lastenheft.docx`
- `docs/pflichtenheft.docx`

Weitere mögliche Exporte:

```bash
scripts/export_docs.sh html
scripts/export_docs.sh pdf
```

Hinweis: PDF-Export kann je nach Pandoc-Image und Umgebung eine zusätzliche
PDF-/LaTeX-Engine benötigen. DOCX ist derzeit der robust verifizierte Export.

## Verifikation

Nach dem Anlegen der Dokumente und Skripte wurde geprüft:

```bash
git diff --check
```

Ergebnis: keine Whitespace-/Diff-Fehler.

Dateien und Besitzrechte wurden geprüft; die DOCX-Dateien gehören dem lokalen
Benutzer `chrizz1001`.

## Chart-Rendering

Die ursprünglichen Mermaid-Codeblöcke wurden durch PNG-Bilddateien ersetzt,
damit die Charts in den DOCX-Dateien sichtbar gerendert werden. Die SVG-Dateien
bleiben als bearbeitbare Quellen erhalten.

Diagrammdateien:

- `docs/charts/lastenheft-prozessuebersicht.svg`
- `docs/charts/lastenheft-prozessuebersicht.png`
- `docs/charts/pflichtenheft-systemarchitektur.svg`
- `docs/charts/pflichtenheft-systemarchitektur.png`
- `docs/charts/pflichtenheft-step-engine.svg`
- `docs/charts/pflichtenheft-step-engine.png`

Die Markdown-Dokumente referenzieren diese Dateien direkt per Bildsyntax. Die
DOCX-Dateien wurden danach neu exportiert.

### Font-Fix 2026-07-14

Beim ersten SVG-zu-PNG-Rendering wurden Texte in den Chart-Bildern als Rechtecke
gerendert, weil der Container die referenzierte Schrift nicht sauber auflösen
konnte. Fix:

- SVGs verwenden jetzt explizit `"DejaVu Sans"` statt `Arial`.
- `scripts/render_charts.sh` mountet `/usr/share/fonts` in den Docker-Container.
- Für den Container werden `HOME=/tmp` und `XDG_CACHE_HOME=/tmp` gesetzt, damit
  Fontconfig ohne Cache-Warnungen arbeiten kann.
- Die PNGs wurden neu gerendert und die DOCX-Dateien erneut exportiert.

## Inhaltsüberarbeitung 2026-07-14

Die Dokumente wurden fachlich generalisiert:

- Ärzte- und Pflege-Survey werden nicht mehr als finaler Produktfokus
  beschrieben, sondern als Beispielkonfigurationen.
- Ziel ist die grundsätzliche Darstellbarkeit mehrerer fachlicher Szenarien über
  dieselbe generische Survey-/Step-Engine.
- Eigenschaften und Zusammenhänge der Steps werden generisch beschrieben:
  Step-Typen, Conditions, Visibility, Blocking, Auto-Complete, Uploads,
  Partnerauswahl, Meilensteine und Progress-Berechnung.
- Der Ärzte-Kontext wird als anwendernahes Beispiel genutzt.
- Punkt 5.2 im Pflichtenheft "Typisches Muster" bleibt enthalten und wurde mit
  einem Ärzte-Beispiel für Antragstellung Approbation konkretisiert.

## Strukturüberarbeitung 2026-07-14

Deckblatt und Inhaltsverzeichnis wurden am Anfang der Dokumente ergänzt:

- `docs/lastenheft.md`
- `docs/pflichtenheft.md`
- `docs/toolstack.md`

Das Pflichtenheft wurde zusätzlich stärker tabellarisch strukturiert:

- Datenmodelle zeigen Feld, Datentyp und Kurzbeschreibung.
- Backend-Schnittstellen zeigen Bereich, Methode/Endpoint, erwartete Parameter,
  Rückgabetyp und Kurzbeschreibung.
- Frontend-Routen zeigen Route, erwartete Parameter, Rückgabetyp/Ansicht und
  Kurzbeschreibung.
- Frontend-Kernseiten und API-Client-Funktionen wurden ebenfalls tabellarisch
  beschrieben.

## Ausschreibungsergänzung 2026-07-14

Lastenheft und Pflichtenheft wurden nach bestem Wissen mit üblichen Angaben für
öffentliche Ausschreibungen ergänzt. Nicht bekannte Auftraggeberinformationen
wurden als Platzhalter oder als zu bestätigende Annahmen markiert.

Ergänzt im Lastenheft:

- formale Angaben und Dokumenthistorie;
- Geltungsbereich und normative Referenzen;
- Glossar;
- Anforderungskatalog mit IDs, Prioritäten und Akzeptanzkriterien;
- nichtfunktionale Anforderungen mit üblichen Richtwerten;
- Datenschutz-, Sicherheits- und Compliance-Anforderungen;
- Liefergegenstände und Mitwirkungspflichten;
- Abnahmeverfahren und beispielhafte Bewertungsmatrix;
- offene Auftraggeberangaben.

Ergänzt im Pflichtenheft:

- Produktionsbetrieb und Deployment;
- Umgebungsvariablen und Secret-Management;
- Betriebs-SLAs als Standardannahme;
- Rollen- und Rechtematrix;
- Datenschutz- und Sicherheitskonzept;
- Barrierefreiheitsanforderungen;
- Monitoring, Logging, Backup und Restore;
- Test- und Abnahmekonzept;
- Migration, Wartung und Support;
- Ausschreibungsannahmen.

## Aktueller Git-Status-Hinweis

### Letzte Word-Änderungsübernahme 2026-07-14

Aus `docs/lastenheft_new.docx` wurde die nachvollzogene Änderung übernommen:

- Deckblatt im Lastenheft: Projektname geändert von
  `GERdoctor / IHCA Multi-Survey-Plattform` zu
  `IHCA Multi-Survey-Plattform`.

Nicht übernommen wurden eine reine Leerzeichenänderung und ein gelöschter
Testtext `test2`, weil sie keine fachliche Dokumentänderung darstellen.
`docs/lastenheft.docx` wurde danach neu exportiert und enthält keine
Word-Änderungsmarker.

## Aktueller Git-Status-Hinweis vor Commit

Die Dokumentationsdateien sind neu beziehungsweise geändert:

- `docs/`
- `scripts/export_docs.sh`
- `scripts/render_charts.sh`
- `memory/documentation-toolstack.md`

Unabhängig davon existieren aus der vorherigen Performance-/Security-Session
weiterhin Backend-/Memory-Änderungen, die beim nächsten Commit mitgesichert
werden sollen:

- `backend/helpers.py`
- `backend/server.py`
- `backend/tests/test_reload_performance.py`
- `backend/tests/test_file_access_security.py`
- `memory/data-structures-surveys.md`
- `memory/programming-notes.md`
- `memory/step-system-notes.md`
