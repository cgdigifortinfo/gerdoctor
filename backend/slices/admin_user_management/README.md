# Admin User Management

Der Slice kapselt die administrativen Nutzer-Lebenszyklen und koordiniert dabei
Identity, Gruppen und Rechte, Survey-Zuweisung, Partnerverknüpfungen,
historischen Dateischutz und Audit Trail.

Enthalten sind typisierte Commands und Ergebnisse, reine Regeln für Rollen,
Partnerzuordnung, Berechtigungs-Overrides, Suchfilter, initialen
Survey-Fortschritt und revisionssichere Archivierung sowie Repository-Port,
MongoDB-Adapter, Service und HTTP-Fehlerabbildung.

Suche, Nutzeranlage, Rollenwechsel, Bulk-Rollen, Rechteänderungen und Soft-Delete
delegieren an den Slice. Detailansicht und Progress-Bearbeitung bleiben bei den
bereits zuständigen Versionierungs- und Survey-Slices. Der primäre Admin ist vor
Rollenwechsel, Rechteüberschreibung und Löschung geschützt. Beim Archivieren
bleiben historische Dateien erhalten und Partnerrelationen werden gelöst.

## Qualitätsprüfung

- 100 % Line- und Branch-Coverage für alle Slice-Module
- striktes mypy für Domain, Modelle, Ports, Repository, Service und Webgrenze
- Mutation Testing für Domain und Modelle
- Regressionstests für CRUD, Rollen/Rechte, Survey-Zuweisung,
  Partnerrelationen und historischen Dateischutz
