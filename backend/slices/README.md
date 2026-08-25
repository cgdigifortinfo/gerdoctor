# Backend slices

Jeder fachliche Slice lebt vollständig in einem eigenen Python-Paket unter
`slices/<slice_name>/`. Abhängigkeiten zwischen Slices erfolgen ausschließlich
über deren öffentliche Module und niemals über frühere Sammelordner wie
`domain/`, `repositories/` oder `services/`.

Die Module innerhalb eines Slice folgen, soweit fachlich benötigt, diesem
Schema:

- `domain.py`: reine Geschäftsregeln
- `models.py`: typisierte Ein- und Ausgabemodelle
- `mappers.py`: Übersetzung zwischen Persistenz- und Domänenmodellen
- `ports.py`: technische Schnittstellen
- `repository.py`: Persistenzzugriff
- `service.py`: Anwendungsfälle und Orchestrierung
- `web.py` beziehungsweise `web_*.py`: FastAPI-nahe Adapter
- `migration.py` oder `facade.py`: slice-spezifische Migrationen und stabile
  Übergangsschnittstellen

Universelle kleine Typen bleiben in `shared/`, technische Adapter ohne
fachliche Ownership in `infrastructure/`. Ausführbare Migrationen dürfen als
CLI-Einstiegspunkte im Backend-Root liegen, ihre Geschäftslogik gehört jedoch
in den zuständigen Slice.
