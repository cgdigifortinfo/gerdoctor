# Step Chain Logic

Stand: 2026-06-22

Diese Notiz beschreibt die aktuell gepruefte Step-Logik und die vorgenommenen Korrekturen.

## Rollen und Grundprinzip

Es gibt weiterhin drei Rollen:

- `user`: bearbeitet Journey/Survey im Dashboard.
- `partner`: sieht und bearbeitet zugewiesene bzw. eingereichte Nutzer.
- `admin`: verwaltet Users, Partners, Steps, Surveys, CMS, E-Mail-Vorlagen, Audit Log und Settings.

Steps werden datengetrieben in MongoDB gespeichert und nach `order` sortiert geladen. Conditions entscheiden, ob ein Step sichtbar, blockiert oder automatisch abgeschlossen ist.

## Step-Typen

Aktuelle Step-Typen:

- `form`
- `decision`
- `partner_selection`
- `partner_multiselection`
- `milestone`
- `display`

## Condition-Actions

Wichtige Actions:

- `hide`: Step wird fuer den Nutzer unsichtbar und aus Fortschritt/ETA herausgerechnet.
- `block`: Step bleibt sichtbar, aber gesperrt.
- `auto_complete`: Step wird automatisch abgeschlossen.
- `redirect`: im Editor vorhanden, aktuell nicht Kern des Flows.

## Condition-Operatoren

Wichtige Operatoren:

- `equals`
- `not_equals`
- `contains`
- `not_empty`
- `empty`
- `status_is`
- `status_not`
- `has_upload`
- `missing_upload`

Compound Conditions:

- `all_of`
- `any_of`

## Typische Muster

Decision/Upload/Partner:

- Upload-Step wird versteckt, wenn Decision nicht `upload` ist.
- Partner-Step wird versteckt, wenn Decision nicht `partner` ist.
- Bei Jobangeboten wird Partner-Multiselect nur bei passender Decision gezeigt.

Milestone:

- Milestone wird automatisch abgeschlossen, wenn ein zugehoeriger Upload-Step echte Datei-Daten mit `file_id` enthaelt.
- Milestone blockiert, wenn Upload gewaehlt wurde, aber keine Datei vorhanden ist.
- Milestone blockiert, wenn vorherige Entscheidung/Partneraktion noch offen ist.

## Korrigierte lineare Kette

Vor der Korrektur waren spaetere Bloecke zu stark an den Approbations-Meilenstein gekoppelt. Dadurch konnten mehrere grosse Bloecke gleichzeitig sichtbar werden, sobald Step 6 abgeschlossen war.

Jetzt gilt fuer den bestehenden Aerzte-Flow eine lineare Freischaltung:

- Step 7 wartet auf Step 6.
- Step 11 wartet auf Step 10.
- Step 15 wartet auf Step 14.
- Step 19 wartet auf Step 18.
- Step 22 wartet auf Step 21.

Die blockierenden/versteckenden Conditions nutzen jeweils den vorherigen Meilenstein:

- `block`, wenn vorheriger Milestone nicht abgeschlossen ist.
- `hide`, wenn vorheriger Milestone nicht abgeschlossen ist.

Dadurch bleibt die sichtbare Journey logisch von Anfang bis Ende.

## Aktueller Core-Flow des alten Aerzte-Surveys

Der bestehende Default-Flow hat 25 Steps:

1. `Persoenliche Daten`
2. `Schnellstart oder Selbststart?`
3. `Antragstellung Approbation`
4. `Dokumente Antragstellung Approbation`
5. `Service Antragstellung Approbation`
6. `Uebersicht Antragstellung Approbation`
7. `Fachsprachenpruefung`
8. `Dokumente Fachsprachenpruefung`
9. `Service Fachsprachenpruefung`
10. `Uebersicht Fachsprachenpruefung`
11. `Gleichwertigkeitspruefung`
12. `Dokumente Gleichwertigkeitspruefung`
13. `Service Gleichwertigkeitspruefung`
14. `Uebersicht Gleichwertigkeitspruefung`
15. `Kenntnispruefung`
16. `Dokumente Kenntnispruefung`
17. `Service Kenntnispruefung`
18. `Uebersicht Kenntnispruefung`
19. `Jobangebote`
20. `Partner Jobangebote`
21. `Uebersicht Jobangebote`
22. `Weiterbildung`
23. `Dokumente Weiterbildung`
24. `Service Weiterbildung`
25. `Uebersicht Weiterbildung`

Hinweis: Dieser Flow ist noch nicht der finale Pflege-Flow.

Aktueller Datenbankstand: `aerzte` und `pflege` haben jeweils 25 aktive Steps.
Step-Orders sind deshalb nur innerhalb eines Surveys
eindeutig; Admin- und Testabfragen müssen immer nach Survey filtern.

## Pflege-Flow

Der Pflege-Flow verwendet dieselbe vierteilige Mechanik je Kernetappe:
Decision -> Dokumente oder Partner -> Übersicht/Meilenstein.

- 1–2: Registrierung und Schnellstart/Selbststart
- 3–6: Anerkennung Pflege
- 7–10: Sprachschule
- 11–14: Fachsprachenprüfung
- 15–18: Vorbereitungskurs Kenntnisprüfung
- 19–22: Kenntnisprüfung
- 23–25: Jobangebote, Partnerauswahl und Übersicht

Die Etappen werden linear über den jeweils vorherigen Meilenstein freigeschaltet.
Im Pflege-Survey gibt es weder den Begriff Approbation noch eine Etappe
Gleichwertigkeitsprüfung. Passende Pflege-Partner-Tags existieren für alle fünf
Service-Schritte.

## Migration

Neue Datei:

- `backend/migrate_linear_step_chain.py`

Die Migration ist idempotent und setzt die Conditions auf den Orders:

- `7 -> 6`
- `11 -> 10`
- `15 -> 14`
- `19 -> 18`
- `22 -> 21`

Ausgefuehrte Migration im Backend-Container:

```bash
docker exec gerdoctor-backend sh -lc 'cd /app/backend && python migrate_linear_step_chain.py'
```

Ergebnis sinngemaess:

```text
Updated step 7 -> waits for 6
Updated step 11 -> waits for 10
Updated step 15 -> waits for 14
Updated step 19 -> waits for 18
Updated step 22 -> waits for 21
```

## Audit-Ergebnis

Nach Migration wurde die Sichtbarkeit geprueft:

- Frischer User: sichtbar `[1, 2, 3]`
- Nach Milestone 6: sichtbar `[1, 2, 3, 7]`
- Nach Milestone 10: sichtbar `[1, 2, 3, 7, 11]`
- Nach Milestone 18: sichtbar `[1, 2, 3, 7, 11, 15, 19]`

Interpretation:

- Die sichtbare Kette ist linear.
- Zukunfts-Steps koennen technisch weiterhin in Blockerlisten auftauchen, sind aber fuer den Nutzer verborgen, solange die Vorgaenger nicht abgeschlossen sind.

## Admin-Bereich Erkenntnisse

Step-Editor:

- Step-Liste und Flow-Builder sind im Admin-Tab fuer Steps erreichbar.
- Conditions koennen im Step-Dialog gepflegt werden.
- Presets sind ueber `data-testid^="condition-preset-"` erreichbar.
- Step-Dialog zeigt Basic, Type Settings, Fields, Requirements, Mappings, Conditions, Notifications und Translations.

Impersonation:

- Admin kann User impersonieren.
- Getesteter Demo-User war `dr.schmidt@chrizz1001.de`.
- Impersonation navigiert fuer normale User nach `/dashboard`.
- Fuer Partner-User navigiert die App nach `/partner-dashboard`.

## Offene fachliche Aufgabe

Der neue Pflege-Survey braucht eine eigene fachliche Step-Kette. Noch zu definieren:

- Welche Pflege-Zielgruppen unterschieden werden, z. B. Altenpflege, Krankenpflege, Pflegefachkraft.
- Welche Dokumente pro Zielgruppe erforderlich sind.
- Ob Anerkennung, Fachsprachpruefung, Arbeitgebervermittlung und Weiterbildung getrennte Module werden.
- Welche Steps echte Uploads, Partnerauswahl, automatische Meilensteine oder Admin-/Partner-Freigaben brauchen.
- Welche E-Mail-Events pro Step gesendet werden.
- Welche Partner-Tags fuer Pflege gelten.
