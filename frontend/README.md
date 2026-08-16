# GerDoctor Frontend

Das Frontend basiert auf React, CRACO und Tailwind CSS. Es verwendet ausschließlich die UI-Komponenten unter `src/components/ui`, die von GerDoctor tatsächlich importiert werden.

## Befehle

```bash
npm install --legacy-peer-deps
npm start
npm run build
npm test -- --watchAll=false --passWithNoTests
```

GerDoctor wird lokal auf `http://localhost:3001` gestartet. `REACT_APP_BACKEND_URL` bleibt leer, damit der Browser die API unter `/api` auf demselben Host anspricht. Der Entwicklungs-Proxy leitet diese Requests über `API_PROXY_TARGET` (standardmäßig `http://localhost:8001`) an das Backend weiter.
