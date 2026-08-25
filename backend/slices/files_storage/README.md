# Files & Storage

Der Slice „Files & Storage“ ist vollständig extrahiert.

Enthalten sind:

- Domainregeln für Dateitypen, Größenlimits, Pfade und Zugriffsentscheidungen
- unveränderliche, typisierte Modelle
- Repository- und Storage-Ports
- MongoDB-Repository
- Service für Upload, Download, Berechtigungen und historischen Dateischutz
- FastAPI-spezifische Fehlerübersetzung
- lokaler Storage-Adapter unter `infrastructure`
- Slice-Dokumentation in dieser `README.md`

Die alten Storage-Helfer und Zugriffsregeln wurden aus `server.py` und
`helpers.py` entfernt. Upload, Download, Startup-Initialisierung und Dateischutz
bei Benutzerlöschungen verwenden jetzt den neuen Service.

## Qualitätsprüfung

- 473 Domain-/Architekturtests erfolgreich
- 100 % Line- und Branch-Coverage bei 2.806 Statements und 752 Branches
- 148 betroffene Regressionstests erfolgreich
- Striktes mypy: 122 Dateien ohne Befund
- Mutation Testing: alle 32 Files-&-Storage-Domainmutanten getötet
- `git diff --check`: keine Formatierungsfehler
- Keine verbliebenen Verweise auf die entfernten Storage-Helfer gefunden
