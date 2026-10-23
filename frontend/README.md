# GerDoctor Frontend

Das Frontend basiert auf React, Vite und Tailwind CSS. Node.js 24.22.1 LTS (siehe `.nvmrc`) und npm 11 oder neuer werden benötigt. Jest läuft unabhängig vom Buildsystem; die bestehenden Coverage-Grenzen und Mutation-Shards bleiben aktiv.

## Befehle

```bash
npm ci
npm start
npm run lint
npm run build
npm run test:coverage -- --runInBand
```

GerDoctor wird lokal auf `http://localhost:3001` gestartet. `REACT_APP_BACKEND_URL` bleibt leer, damit der Browser die API unter `/api` auf demselben Host anspricht. Der Entwicklungs-Proxy leitet diese Requests über `API_PROXY_TARGET` (standardmäßig `http://localhost:8001`) an das Backend weiter.

Vite erzeugt den Produktionsbuild weiterhin unter `build/`, damit das Plesk-Deployment denselben Pfad verwenden kann. Die HTML-Einstiegsdatei liegt jetzt unter `index.html`. JSX in bestehenden `.js`-Dateien und der Alias `@/` bleiben unterstützt. Nur `REACT_APP_BACKEND_URL` wird als öffentliche Buildvariable übernommen.

Tailwind CSS 4 wird über das Vite-Plugin eingebunden; Theme und Design-Tokens liegen in `src/index.css`. Unterstützt werden Chrome/Edge ab 111, Firefox ab 128 und Safari ab 16.4. Die Utility-Namen wurden mit dem offiziellen Tailwind-Migrationswerkzeug angepasst.

Der gezielte `qs`-Override für `typed-rest-client` aktualisiert die von Stryker verwendete transitive Abhängigkeit auf die sicherheitsbereinigte, kompatible Version 6.16.1. Sobald `typed-rest-client` diese Version selbst verwendet, kann der Override entfallen.
