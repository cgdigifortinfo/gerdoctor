# Step Templates

Der Slice kapselt den vollständigen Lebenszyklus wiederverwendbarer
Schrittvorlagen: Auflisten, Anlegen, Bearbeiten, Löschen, Erzeugen aus einem
bestehenden Step und Anwenden auf ein Survey.

Beim Anwenden werden nachfolgende Steps versioniert verschoben, der neue Step
erhält seine erste unveränderliche Version und alle betroffenen Nutzer erhalten
eine initiale Progress-Revision. Diese historischen Operationen werden über die
bestehenden Step-Versioning-Schnittstellen angebunden.

`domain.py` enthält die reinen Bereinigungs- und Erzeugungsregeln. Instanzfelder
wie ID, Reihenfolge, Aktivstatus und Zeitstempel gelangen nicht aus einer
Vorlage in eine neue Step-Instanz. Repository, Service, HTTP-Modelle und
Fehlerabbildung befinden sich vollständig in diesem Slice.

Der Slice ist Bestandteil des strikten mypy-, 100-%-Line-/Branch-Coverage- und
Mutation-Testing-Gates.
