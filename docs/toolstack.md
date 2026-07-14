# Dokumentations-Toolstack

## Deckblatt

| Feld | Inhalt |
|---|---|
| Projekt | GERdoctor / IHCA Multi-Survey-Plattform |
| Dokument | Dokumentations-Toolstack |
| Stand | 2026-07-14 |
| Status | Arbeitsdokument |
| Zweck | Beschreibung des Markdown-, Chart- und Pandoc-Workflows |

## Inhaltsverzeichnis

- [Empfohlener Stack](#empfohlener-stack)
- [Dateien](#dateien)
- [Installationsstatus in dieser Umgebung](#installationsstatus-in-dieser-umgebung)
- [Pandoc installieren](#pandoc-installieren)
- [Export-Kommandos](#export-kommandos)
- [Diagramme](#diagramme)

## Empfohlener Stack

Dieses Repo nutzt für Lastenheft und Pflichtenheft einen schlanken,
versionierbaren Dokumentationsstack:

- Markdown für die Quelldokumente;
- Git für Versionshistorie und Review;
- PNG-Bilddateien für Diagramme, damit DOCX-Exporte die Charts direkt rendern;
- Pandoc für Export nach PDF, DOCX oder HTML.

## Dateien

- `docs/lastenheft.md`
- `docs/pflichtenheft.md`
- `docs/toolstack.md`

## Installationsstatus in dieser Umgebung

- `git`: vorhanden über das Repo.
- `npm`: vorhanden.
- `docker`: installiert; Pandoc ist über das Image `pandoc/core:latest`
  nutzbar.
- `pandoc`: nicht systemweit installiert.

Die automatische systemweite Installation von `pandoc` wurde versucht, ist aber
an einem fehlenden `sudo`-Passwort-Prompt gescheitert. Als Alternative wurde das
Docker-Image `pandoc/core:latest` erfolgreich gezogen und getestet.

## Pandoc installieren

Auf Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y pandoc
```

Alternative mit Docker, falls Docker-Socket verfügbar ist:

```bash
docker run --rm -v "$PWD:/data" pandoc/core \
  docs/lastenheft.md -o docs/lastenheft.docx
```

Das Repo-Skript nutzt automatisch lokales `pandoc` oder fällt auf Docker zurück:

```bash
scripts/export_docs.sh docx
scripts/export_docs.sh html
scripts/export_docs.sh pdf
```

Vor dem Export rendert `scripts/export_docs.sh` die Diagramme über
`scripts/render_charts.sh` neu. Das Render-Skript nutzt lokal installiertes
`rsvg-convert` oder fällt auf `rsvg-convert` im Docker-Image `pandoc/core`
zurück. Dabei wird `/usr/share/fonts` in den Container gemountet, damit deutsche
Umlaute und reguläre Buchstaben korrekt als Text im PNG erscheinen.

## Export-Kommandos

DOCX:

```bash
pandoc docs/lastenheft.md -o docs/lastenheft.docx
pandoc docs/pflichtenheft.md -o docs/pflichtenheft.docx
```

HTML:

```bash
pandoc docs/lastenheft.md -o docs/lastenheft.html
pandoc docs/pflichtenheft.md -o docs/pflichtenheft.html
```

PDF:

```bash
pandoc docs/lastenheft.md -o docs/lastenheft.pdf
pandoc docs/pflichtenheft.md -o docs/pflichtenheft.pdf
```

Hinweis: PDF-Export benötigt je nach System zusätzlich eine LaTeX-Engine.
DOCX ist für Auftraggeberdokumente meist der robustere erste Export.

## Diagramme

Die Dokumente referenzieren Diagramme als PNG-Bilddateien unter `docs/charts/`.
Zusätzlich liegen die bearbeitbaren SVG-Quelldateien im selben Ordner. Dadurch
rendert Pandoc die Charts beim DOCX-Export als eingebettete Bilder, statt
Mermaid-Codeblöcke unverarbeitet in das Word-Dokument zu übernehmen.
