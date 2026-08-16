# GerDoctor

GerDoctor begleitet internationale Fachkräfte durch strukturierte Anerkennungsprozesse. Das Repository enthält ein React-Frontend, eine FastAPI-Anwendung und MongoDB als Datenbank.

## Lokale Entwicklung

```bash
docker compose up -d mongo backend
cd frontend
npm install --legacy-peer-deps
npm start
```

Das Frontend ist in der lokalen GerDoctor-Entwicklungsumgebung unter `http://localhost:3001` erreichbar, die API unter `http://localhost:8001/api/`. Der Browser verwendet `/api` auf demselben Host; CRACO leitet diese Requests lokal an Port `8001` weiter.

## Frontend

```bash
cd frontend
npm run build
npm test -- --watchAll=false --passWithNoTests
```

## Backend-Tests

```bash
cd backend
python -m pip install -r requirements-test.txt
pytest -q
```

Produktive Plesk-Hinweise befinden sich in `deploy/plesk/README.md`.
