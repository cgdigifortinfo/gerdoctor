# CMS & Public Settings

Dieser Slice kapselt editierbare CMS-Inhalte, die globale Website-Konfiguration
und deren sichere öffentliche Darstellung.

## Verantwortlichkeiten

- `domain.py`: Normalisierung historisch verschachtelter CMS-Daten, Backfill von
  Standardinhalten sowie Filter- und Maskierungsregeln für Settings.
- `models.py`: unveränderliche CMS-Werte.
- `ports.py`: typisierte Persistenzschnittstelle.
- `repository.py`: MongoDB-Adapter für `cms_content` und `site_settings`.
- `service.py`: Lesen, Bearbeiten und idempotentes Initialisieren von CMS und
  Website-Einstellungen.
- `web.py`: Pydantic-Modelle der HTTP-Grenze.

Stripe-Schlüssel werden hier ausschließlich gefiltert oder maskiert. Ermittlung
des Stripe-Status und Subscription-Logik bleiben in ihren zuständigen Slices und
werden am Composition Root zugeliefert.

## Qualitätsschutz

Der Slice gehört zum strikten mypy-Gate sowie zum 100-%-Line-/Branch-Coverage-
Gate. `domain.py` und `models.py` sind Teil des Mutation-Testings. Tests decken
auch Legacy-Wrapper, optionale Übersetzungen, Secret-Leaks, Backfills und
idempotentes Seeding ab.
