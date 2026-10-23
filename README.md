# GerDoctor

GerDoctor begleitet internationale Fachkräfte durch strukturierte Anerkennungsprozesse. Das Repository enthält ein React-Frontend, eine FastAPI-Anwendung und MongoDB als Datenbank.

## Lokale Entwicklung

```bash
docker compose up -d mongo backend
cd frontend
npm ci
npm start
```

Das Frontend benötigt Node.js 24.22.1 LTS oder eine neuere 24.x-Version und ist lokal unter `http://localhost:3001` erreichbar, die API unter `http://localhost:8001/api/`. Der Browser verwendet `/api` auf demselben Host; Vite leitet diese Requests lokal an Port `8001` weiter. Mit `docker compose up -d --build` laufen alle drei Dienste in Docker.

## Frontend

```bash
cd frontend
npm run build
npm run lint
npm run test:coverage -- --runInBand
```

## Backend-Tests

```bash
cd backend
python -m pip install -r requirements-test.txt
pytest -c pytest.next.ini
pytest -c pytest.domain.ini
mypy
```

Produktive Plesk-Hinweise befinden sich in `deploy/plesk/README.md`.

## Abhängigkeiten

Der Sicherheitsstand vom 23.10.2026 verwendet Node.js 24 LTS, Vite 8, Tailwind CSS 4, Jest 30 sowie die aktualisierte FastAPI-/Starlette-Laufzeit und MongoDB 7.0.45. Details zur Frontend-Migration und den Browser-Mindestversionen stehen in `frontend/README.md`.

`bcrypt` bleibt auf der aktuellen 4.x-Version: Version 5 verändert das Verhalten für bestehende Passwörter mit mehr als 72 Bytes und benötigt eine gesonderte Passwortmigration. Motor 3.7.1 und PyMongo 4.19.0 sind aktualisiert; der spätere Wechsel von Motor auf die native asynchrone PyMongo-API muss separat umgesetzt und getestet werden. Die aktuellen npm- und Python-Abhängigkeiten haben zum Prüfzeitpunkt keine bekannten Audit-Befunde.
