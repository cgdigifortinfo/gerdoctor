# Event-System

Der Slice kapselt persistente Domain-Events, konfigurierbare Handler,
synchronen Dispatch, Retry und die providerneutrale Notification-Outbox.

Enthalten sind:

- unveränderliche, vollständig typisierte Ergebnis- und Seitenmodelle
- reine Regeln für Handler-Normalisierung und Dispatch-Vorprüfungen
- deterministische Event-, Ergebnis- und Outbox-Dokumente
- kanonische Konfigurationen für Partnerabschluss, Ablehnung und Dokumentupload
- Repository- und Notification-Ports
- MongoDB-Repository für Konfigurationen, Events und Outbox
- Service für Seeding, Emit, Process, Retry und Adminabfragen
- Adapter zum Slice `Email Templates & Notifications`
- HTTP-Fehlerabbildung für die Admin-API

Events werden vor ihrer Verarbeitung gespeichert. Fehlgeschlagene Zustellungen
bleiben dadurch im Adminbereich sichtbar und können erneut verarbeitet werden.
Browser/App-Nachrichten werden idempotent anhand von Event- und Handler-ID in
die Outbox geschrieben.

`event_system.py` bleibt als schmale, importstabile Kompatibilitätsfassade für
bestehende Aufrufer bestehen. Die Admin-Endpunkte delegieren direkt an den
neuen Service.

## Qualitätsprüfung

- 100 % Line- und Branch-Coverage für alle Slice-Module
- striktes mypy für Domain, Ports, Repository, Adapter, Service und Webgrenze
- Mutation Testing für Domain und Modelle ohne überlebende Mutationen
- Regressionstests für Partnerabschluss, Ablehnung, E-Mail-Handler,
  Browser/App-Outbox, Retry und Berechtigungen
