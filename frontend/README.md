# GerDoctor Frontend

Das Frontend basiert auf React, CRACO und Tailwind CSS. Es verwendet ausschließlich die UI-Komponenten unter `src/components/ui`, die von GerDoctor tatsächlich importiert werden.

## Befehle

```bash
npm install --legacy-peer-deps
npm start
npm run build
npm test -- --watchAll=false --passWithNoTests
```

Der Entwicklungsserver verwendet standardmäßig `http://localhost:3000`. Die API-Adresse wird über `REACT_APP_BACKEND_URL` gesetzt; für den lokalen Proxy kann `API_PROXY_TARGET` verwendet werden.
