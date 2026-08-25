# Backend-Architekturgrenzen

Jeder fachliche Bereich liegt geschlossen unter `slices/<slice-name>/`. Ein
Slice enthält seine Dateien `domain.py`, `models.py`, optional `mappers.py`,
`repository.py`, `service.py`, `ports.py` und seine HTTP-Adapter. Dadurch sind
zusammengehörige Regeln, Persistenz und Anwendungsfälle direkt auffindbar.

## `infrastructure`

Enthält technische Adapter wie Systemzeit, Identifier, MongoDB-ID-Konvertierung,
Storage sowie später konkrete E-Mail- und Stripe-Clients. Diese Module kennen
keine FastAPI-Requests oder HTTP-Statuscodes und enthalten keine Fachregeln.

## `web`

Enthält ausschließlich die FastAPI-/HTTP-Grenze: Übersetzung typisierter
Domainfehler, Request-Aufbereitung und Response-Serialisierung. Das Paket darf
Domain- und Service-Typen kennen, aber keine Geschäftsentscheidungen treffen und
nicht direkt auf MongoDB zugreifen.

## `shared`

Enthält nur kleine, stabile und dependency-freie Typdefinitionen. Aktuell sind
das rekursive JSON-Typen. Fachliche Modelle, Helper, Datenbankzugriff und
Frameworkcode sind hier ausdrücklich nicht erlaubt.

## Abhängigkeitsrichtung

```text
web -> services -> domain
          |
          v
     repositories -> infrastructure

shared darf von allen Ebenen verwendet werden, kennt selbst aber keine Ebene.
```

Neue allgemeine Funktionen werden nicht automatisch nach `shared` verschoben.
Sie verbleiben im fachlichen Slice, bis mindestens zwei unabhängige Verbraucher
eine wirklich identische, fachlich neutrale Abstraktion benötigen.

`unit_tests_next/test_architecture_boundaries.py` erzwingt diese Importgrenzen
innerhalb aller Slice-Ordner.
Insbesondere dürfen Domainmodule weder BSON/FastAPI noch Repository-, Service-,
Web- oder Infrastrukturadapter importieren. Webmodule dürfen nicht direkt auf
die Datenbank oder Repositoryadapter zugreifen.
