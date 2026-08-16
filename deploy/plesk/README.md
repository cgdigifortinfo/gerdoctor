# GerDoctor auf Plesk

Das App-Image enthaelt Backend und das gebaute React-Frontend. Es lauscht intern
auf Port `8001`. MongoDB wird als separater Container aus `mongo:7` betrieben.

## Erforderliche App-Umgebungsvariablen

- `MONGO_URL=mongodb://<mongo-container>:27017`
- `DB_NAME=gerdoctor`
- `JWT_SECRET=<langes-zufaelliges-geheimnis>`
- `FRONTEND_URL=https://<oeffentliche-domain>`
- `LOCAL_STORAGE_ROOT=/var/lib/gerdoctor/uploads`

Fuer `/var/lib/gerdoctor/uploads` und `/data/db` muessen persistente Volumes
konfiguriert werden. Die App-Domain wird in Plesk auf den internen App-Port
`8001` gelegt. Der MongoDB-Port sollte nicht oeffentlich freigegeben werden.

## Seed (nur bei einer neuen/leeren Installation)

Im App-Container ausfuehren:

```sh
python /app/backend/seed_baseline.py --force
```

Der Seed ersetzt die konfigurierte Datenbank und den Upload-Inhalt. Nicht auf
einer bestehenden Produktivdatenbank ausfuehren.
