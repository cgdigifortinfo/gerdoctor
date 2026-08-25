# Audit Trail

Der Slice kapselt das unveränderliche fachliche Änderungsprotokoll und dessen
gefilterte Anzeige im Adminbereich.

Enthalten sind:

- vollständig typisierte, unveränderliche Audit-Einträge und Ergebnisseiten
- reine Regeln für Eintragserzeugung, Aktions-/Zeitraumfilter und Pagination
- Repository-Port und MongoDB-Adapter
- Service für Schreiben, Lesen und Indexinitialisierung
- zentrale Zeitquelle über den vorhandenen Infrastrukturadapter
- kompatible `create_audit_log`-Fassade für bestehende Aufrufer

Alle bisherigen Audit-Schreibstellen verwenden dadurch ohne fachliche
Verhaltensänderung den neuen Service. Die Admin-Abfrage delegiert ebenfalls an
den Slice und unterstützt weiterhin Aktion, Von-/Bis-Zeitpunkt, Limit und
Offset. Der Timestamp-Index wird über die Slice-Initialisierung angelegt.

## Qualitätsprüfung

- 100 % Line- und Branch-Coverage für alle Slice-Module
- striktes mypy für Modelle, Domain, Port, Repository und Service
- Mutation Testing für Domain und Modelle ohne überlebende Mutationen
- Regressionstests für Audit-API, Berechtigungen, Template-Audits und
  Step-Versionierung
