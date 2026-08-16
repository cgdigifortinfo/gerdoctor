# Lastenheft

## Deckblatt

| Feld | Inhalt |
|---|---|
| Projekt | IHCA Multi-Survey-Plattform |
| Dokument | Lastenheft |
| Stand | 2026-07-14 |
| Status | Entwurf auf Basis des aktuellen lokalen Projektstands |
| Zweck | Beschreibung der fachlichen Anforderungen an eine generische Survey-/Step-Plattform |
| Beispielszenarien | Ärzte-Survey und Pflege-Survey als Referenzkonfigurationen |
| Auftraggeber | Noch zu ergänzen |
| Ansprechpartner | Noch zu ergänzen |
| Vertraulichkeit | Ausschreibungsunterlage, Verteilung gemäß Vergabeverfahren |

## Inhaltsverzeichnis

- [1. Formale Angaben für Ausschreibungen](#1-formale-angaben-für-ausschreibungen)
- [2. Zielbestimmung](#2-zielbestimmung)
- [3. Ausgangssituation](#3-ausgangssituation)
- [4. Stakeholder und Rollen](#4-stakeholder-und-rollen)
- [5. Produktumfang](#5-produktumfang)
- [6. Muss-Anforderungen](#6-muss-anforderungen)
- [7. Soll-Anforderungen](#7-soll-anforderungen)
- [8. Kann-Anforderungen](#8-kann-anforderungen)
- [9. Nicht-Ziele](#9-nicht-ziele)
- [10. Rahmenbedingungen](#10-rahmenbedingungen)
- [11. Datenschutz und Sicherheit](#11-datenschutz-und-sicherheit)
- [12. Abnahmekriterien](#12-abnahmekriterien)
- [13. Prozessübersicht](#13-prozessübersicht)
- [14. Nichtfunktionale Anforderungen](#14-nichtfunktionale-anforderungen)
- [15. Datenschutz, Sicherheit und Compliance](#15-datenschutz-sicherheit-und-compliance)
- [16. Liefergegenstände und Mitwirkung](#16-liefergegenstände-und-mitwirkung)
- [17. Abnahme, Nachweise und Bewertung](#17-abnahme-nachweise-und-bewertung)
- [18. Annahmen und offene Auftraggeberangaben](#18-annahmen-und-offene-auftraggeberangaben)
- [19. Partnerregistrierung, Abonnements und Abrechnung](#19-partnerregistrierung-abonnements-und-abrechnung)
- [20. Glossar](#20-glossar)
- [21. Anforderungskatalog](#21-anforderungskatalog)

## 1. Formale Angaben für Ausschreibungen

### 1.1 Dokumenthistorie

| Version | Datum | Autor | Änderung | Freigabe |
|---|---|---|---|---|
| 0.1 | 2026-07-14 | Projektteam | Initiale Fassung auf Basis des Systemstands | Entwurf |
| 0.2 | 2026-07-14 | Projektteam | Generalisierung auf Survey-/Step-Plattform | Entwurf |
| 0.3 | 2026-07-14 | Projektteam | Ergänzung ausschreibungsrelevanter Angaben | Entwurf |

### 1.2 Geltungsbereich

| Bereich | Enthalten | Nicht enthalten |
|---|---|---|
| Softwareplattform | Survey-/Step-Engine, Rollen, Dashboards, Uploads, Partnerfunktionen, Admin-Verwaltung | Fachliche Rechtsberatung oder Anerkennungsentscheidung |
| Beispielszenarien | Ärzte- und Pflege-Survey als Referenzkonfigurationen | Abschließende Festlegung auf diese zwei Berufsgruppen |
| Betrieb | Betriebsfähige Webanwendung mit Datenbank, Uploadspeicher und Baseline-Daten | Finale Produktivhosting-Entscheidung ohne Auftraggebervorgaben |
| Dokumentation | Lastenheft, Pflichtenheft, Betriebs- und Testhinweise | Rechtsgutachten, Datenschutz-Folgenabschätzung als anwaltliche Leistung |

### 1.3 Normative und fachliche Referenzen

| Referenz | Relevanz |
|---|---|
| DSGVO, insbesondere Privacy by Design und Privacy by Default | Datenschutzanforderungen, technische und organisatorische Maßnahmen |
| BITV 2.0 / EN 301 549 / WCAG 2.1 AA | Barrierefreiheit für öffentliche Stellen und ICT-Beschaffung |
| BSI-Grundschutz sinngemäß | Orientierung für Sicherheits- und Betriebsanforderungen |
| OWASP ASVS / OWASP Top 10 sinngemäß | Orientierung für Webanwendungssicherheit |

## 2. Zielbestimmung

Die Software soll komplexe, mehrstufige Beratungs- und Qualifizierungsprozesse
als konfigurierbare digitale Journeys abbilden. Unterschiedliche fachliche
Szenarien werden als eigene Surveys modelliert und können jeweils eigene
Landingpages, Registrierungspfade, Prozessschritte, Partnerangebote und
Statuslogiken besitzen.

Die vorhandenen Surveys für Ärzte und Pflegepersonal dienen als Beispiele für
die grundsätzliche Darstellbarkeit solcher Szenarien. Sie zeigen, dass die
Software unterschiedliche Berufs- und Anerkennungskontexte über dieselbe
generische Survey-/Step-Engine abbilden kann. Als anwendernahes Beispiel wird in
diesem Dokument vor allem der Ärzte-Kontext verwendet.

Die Plattform soll Bewerberinnen und Bewerber durch strukturierte Prozesse
führen, Dokumente entgegennehmen, passende Dienstleister oder Partner vermitteln
und Admins sowie Partnern eine arbeitsfähige Verwaltungsoberfläche bereitstellen.

## 3. Ausgangssituation

In vielen Beratungs- und Anerkennungsprozessen müssen Nutzer mehrere fachliche
Etappen, Dokumente, Entscheidungen, Partnerleistungen und Freigaben koordinieren.
Statusinformationen, Nachweise, Partnerauswahl und Rückmeldungen liegen häufig
verteilt vor. Die Software soll solche Prozesse digitalisieren und für
unterschiedliche Zielgruppen oder Use Cases über getrennte Survey-URLs
wiederverwendbar machen.

Die aktuellen Surveys `aerzte` und `pflege` sind Beispielkonfigurationen. Sie
sind nicht als abschließende fachliche Produktgrenze zu verstehen, sondern als
Referenzszenarien für die generische Prozessmodellierung.

## 4. Stakeholder und Rollen

| Rolle | Interesse |
|---|---|
| Nutzer | Registrierung, geführte Journey, Uploads, Fortschritt, Partnerauswahl |
| Partner | Eingereichte Nutzer sehen, Bearbeitungsstand pflegen, Nachweise hochladen |
| Admin | Surveys, Steps, Nutzer, Partner, CMS, E-Mail-Vorlagen und Einstellungen verwalten |
| Betreiber | Wiederherstellbarer Betrieb, valide Datenbasis, Performance, Sicherheit |

## 5. Produktumfang

Die Plattform umfasst:

- öffentliche Landingpages je Survey, z. B. `/s/pflege`;
- Registrierung und Login;
- rollenbasierte Dashboards für Nutzer, Partner und Admins;
- erweitertes Nutzerrechte- und Nutzergruppensystem mit granularen
  Berechtigungen;
- datengetriebene Survey-/Step-Engine;
- Datei-Uploads und geschützte Downloads;
- Partnerauswahl und Partnerzuweisungen;
- Partnerregistrierung mit Abo-Buchung über einen Zahlungsanbieter;
- Abrechnung abgeschlossener Nutzer-Meilensteine je Partner;
- Umsatz- und Abrechnungsübersichten für Partner und Administratoren;
- E-Mail-Benachrichtigungen und editierbare E-Mail-Vorlagen;
- CMS-Inhalte für Landingpages;
- mehrsprachig vorbereitete Inhalte;
- Performance-optimierte API-Endpunkte;
- kanonischen Baseline-Seed für lokalen Betrieb und Tests.

## 6. Muss-Anforderungen

### 6.1 Registrierung und Authentifizierung

- Nutzer müssen sich mit E-Mail, Passwort und Name registrieren können.
- Registrierung über Survey-spezifische URLs muss den passenden Survey speichern.
- Login muss rollenbasiert zum passenden Dashboard führen.
- Admin-, Partner- und Nutzerrollen müssen getrennte Berechtigungen besitzen.
- Authentifizierung muss über Tokens und sichere Cookies unterstützt werden.

### 6.2 Multi-Survey-Fähigkeit

- Die Plattform muss mehrere Surveys parallel betreiben können.
- Die aktuellen Beispiel-Surveys `aerzte` und `pflege` müssen parallel
  darstellbar sein.
- Steps, Progress und Registrierung müssen survey-spezifisch funktionieren.
- Step-Orders dürfen nur innerhalb eines Surveys eindeutig sein müssen.
- Admins müssen Surveys verwalten und Steps nach Survey filtern können.

### 6.3 Generische Survey- und Step-Logik

- Ein Survey muss eine fachliche Journey als geordnete Step-Kette abbilden.
- Steps müssen unterschiedliche fachliche Aufgaben modellieren können, z. B.
  Formular, Entscheidung, Dokumentenupload, Partnerauswahl, Mehrfachauswahl,
  Meilenstein oder reine Anzeige.
- Steps müssen abhängig von vorherigen Antworten und Statuswerten sichtbar,
  versteckt, blockiert oder automatisch abschließbar sein können.
- Decisions müssen Folgepfade steuern können, z. B. Selbstbearbeitung per
  Upload oder Nutzung eines Partners.
- Meilensteine müssen abgeschlossene Etappen darstellen und Folgeschritte
  freischalten können.
- Fortschritt und voraussichtliche Bearbeitungsdauer müssen aus den sichtbaren
  und relevanten Steps berechnet werden.
- Upload-Schritte müssen erforderliche Dokumente erzwingen können.

### 6.4 Beispielszenarien Ärzte und Pflegepersonal

Die Plattform muss die beiden vorhandenen Szenarien grundsätzlich darstellen
können:

- Ärzte: z. B. persönliche Daten, Antragstellung Approbation,
  Fachsprachenprüfung, Kenntnisprüfung, Jobangebote und Weiterbildung.
- Pflegepersonal: z. B. Anerkennung Pflege, Sprachschule,
  Fachsprachenprüfung, Vorbereitungskurs Kenntnisprüfung, Kenntnisprüfung und
  Jobangebote.

Diese Beispiele dienen als Validierung der Modellierungsfähigkeit. Die
Plattform soll nicht auf genau diese Berufsgruppen festgelegt sein. Neue Surveys
sollen mit denselben Step-Typen, Bedingungen und Partnermechaniken angelegt
werden können.

Im Ärzte-Beispiel kann eine Etappe typischerweise so aussehen: Der Nutzer wählt,
ob er Dokumente selbst hochlädt oder einen Partner nutzt. Bei Upload wird ein
Dokumentenschritt sichtbar; bei Partnernutzung wird eine Partnerauswahl
sichtbar. Der zugehörige Meilenstein wird erst abgeschlossen, wenn die
erforderlichen Nachweise oder Partnerfreigaben vorliegen.

### 6.5 Partnerfunktionen

- Interessierte Partner müssen sich über eine eigene Partnerregistrierungsseite
  registrieren können.
- Partner müssen ein Abo über einen Zahlungsanbieter buchen können. Als
  Referenzanbieter wird Stripe angenommen; die fachliche Anforderung bleibt
  anbieterneutral.
- Ein Partnerkonto soll erst nach erfolgreicher Registrierung, Verifizierung und
  aktivem Abo vollständig nutzbar sein.
- Nutzer müssen passende Partner auswählen können.
- Partner müssen ihre eingereichten Nutzer sehen.
- Partner müssen abgeschlossene Fälle getrennt von aktiven Fällen sehen.
- Partner müssen Meilensteine freigeben und Nachweise hochladen können.
- Partner müssen Insights zu Anfragen, Fortschritt und Funnel erhalten.
- Partner müssen eine Übersicht ihrer abrechnungsrelevanten Abschlüsse,
  Umsätze, Abrechnungsperioden und Zahlungsstatus erhalten.

### 6.6 Adminfunktionen

- Admins müssen Nutzer, Partner, Surveys, Steps, CMS-Inhalte und E-Mail-Vorlagen
  verwalten können.
- Admins müssen Step-Logik, Bedingungen, Felder, Reihenfolge und Templates
  bearbeiten können.
- Admins müssen Nutzerfortschritt einsehen und bearbeiten können.
- Admins müssen Nutzer impersonieren können.
- Admins müssen eine zentrale Abrechnungsübersicht über alle Partner,
  abgeschlossenen Meilensteine, Umsätze, Zahlungsstatus und Exportdaten erhalten.

### 6.7 Datei- und Upload-Sicherheit

- Uploads müssen auf erlaubte Dateitypen begrenzt werden.
- Aktive Inhalte wie HTML, SVG oder JavaScript müssen blockiert werden.
- Dateinamen müssen sicher normalisiert werden.
- Datei-Downloads müssen auf Owner, Admin oder berechtigte Partner begrenzt sein.
- Uploadgrößen müssen begrenzt werden.

### 6.8 Performance und Betrieb

- Dashboard-Reloads müssen performant sein.
- Das User-Dashboard soll initial mit einem Bootstrap-Request geladen werden.
- Admin- und Partnerlisten müssen ohne serielle N+1-Abfragen funktionieren.
- Relevante MongoDB-Indizes müssen beim Backend-Start sichergestellt werden.
- Lokale Daten müssen über einen kanonischen Baseline-Seed reproduzierbar sein.

### 6.9 Nutzerrechte und Nutzergruppen

- Das System muss neben den Basisrollen `User`, `Partner` und `Admin`
  erweiterbare Nutzergruppen unterstützen.
- Nutzer müssen einer oder mehreren Gruppen zugeordnet werden können.
- Gruppen müssen Berechtigungsprofile bündeln können, z. B. für Fachadmin,
  Support, Abrechnung, Partner-Manager oder reine Leserechte.
- Berechtigungen müssen granular für Funktionsbereiche steuerbar sein, z. B.
  Surveys, Steps, Nutzerverwaltung, Partnerverwaltung, Billing, Dateien, CMS,
  E-Mail-Vorlagen und Audit Logs.
- Berechtigungen müssen additiv über Rollen und Gruppen wirken; explizite
  Einschränkungen oder Overrides müssen fachlich nachvollziehbar protokolliert
  werden.
- Admins müssen Nutzergruppen, Gruppenmitgliedschaften und Berechtigungsprofile
  verwalten können.
- Kritische Berechtigungsänderungen müssen auditierbar sein.

## 7. Soll-Anforderungen

- Landingpage und Auth-Flows sollen je Survey konfigurierbares Branding
  verwenden.
- E-Mail-Texte sollen über Admin-Oberfläche bearbeitbar sein.
- Partner-Matching soll anhand von Tags und Nutzerprofilen unterstützt werden.
- Admin-Step-Editor soll Flowbuilder, Simulator und Layout-Persistenz bieten.
- Tests sollen zentrale Journey-, Partner-, Security- und Performance-Fälle abdecken.
- Rechteprüfungen sollen performant gecacht oder gebündelt werden, ohne
  Berechtigungsänderungen dauerhaft veraltet auszuliefern.

## 8. Kann-Anforderungen

- Export und Import von Step-Konfigurationen als JSON.
- Webhook-Integration für externe Systeme.
- Wöchentliche Insights-E-Mail an Partner.
- Lokale Speicherung externer Branding-Assets.
- Spezielle Registrierungsfelder pro Survey.

## 9. Nicht-Ziele

- Die Plattform ersetzt keine rechtliche Beratung.
- Die Plattform garantiert keine Anerkennung, Prüfungszulassung,
  Partnerleistung oder Jobvermittlung.
- Die Plattform ist kein vollständiges CRM oder Bewerbermanagementsystem.
- Fachliche, rechtliche oder behördliche Entscheidungen werden nicht
  automatisiert.

## 10. Rahmenbedingungen

- Backend: Python/FastAPI.
- Datenbank: MongoDB.
- Frontend: React/CRACO.
- Lokaler Betrieb: Docker Compose für MongoDB und Backend, Frontend auf Port 3000.
- Persistente Volumes für Datenbank, Uploads und Backend-Temp-Dateien.
- Kanonischer Seed: `backend/seed_baseline.py`.

## 11. Datenschutz und Sicherheit

- Personenbezogene Daten dürfen nur rollen-, gruppen- und
  berechtigungsbasiert sichtbar sein.
- Partner dürfen nur ihnen zugeordnete Nutzer und Dateien sehen.
- Uploads müssen gegen aktive Inhalte und Pfadmanipulation gehärtet sein.
- Audit-Logs sollen administrative Aktionen nachvollziehbar machen.
- Deployment-Konfiguration muss ein ausreichend langes `JWT_SECRET` verwenden.

## 12. Abnahmekriterien

Die Software gilt für den aktuellen Umfang als abnahmefähig, wenn:

- Registrierung und Login für Nutzer, Partner und Admin funktionieren;
- Survey-spezifische URLs wie `/s/pflege` und `/s/pflege/register` den
  jeweiligen Survey korrekt verwenden;
- Nutzer nur Progress für den eigenen Survey erhalten;
- Partner nur berechtigte Nutzer und Dateien sehen;
- Admins Surveys und Steps survey-spezifisch verwalten können;
- Nutzergruppen und Berechtigungsprofile angelegt, zugewiesen und geprüft
  werden können;
- Upload-Sicherheitsregeln wirksam sind;
- zentrale Backend-Tests und gezielte Performance-/Security-Tests bestehen;
- der Baseline-Seed reproduzierbar verifiziert werden kann.

## 13. Prozessübersicht

![Prozessübersicht](docs/charts/lastenheft-prozessuebersicht.png)

## 14. Nichtfunktionale Anforderungen

| ID | Kategorie | Richtwert / Anforderung | Nachweis |
|---|---|---|---|
| NFA-001 | Verfügbarkeit | Zielwert im Regelbetrieb: 99,5 % monatlich, ausgenommen angekündigte Wartung | Betriebsmonitoring |
| NFA-002 | Antwortzeit | 95 % der Dashboard-API-Requests unter 1,0 s bei typischer Last | Last-/Performance-Test |
| NFA-003 | Gleichzeitige Nutzer | Auslegung für mindestens 100 gleichzeitige aktive Web-Sessions als Startwert | Lasttest |
| NFA-004 | Datenvolumen | Startauslegung für 10.000 Nutzer, 50 Surveys, 100 Steps je Survey, 100.000 Uploads | Architekturprüfung |
| NFA-005 | Uploadgröße | Standardlimit 20 MB pro Datei, anpassbar per Konfiguration | Upload-Test |
| NFA-006 | Browser | Aktuelle Versionen von Chrome, Edge, Firefox und Safari | Browser-Smoke-Test |
| NFA-007 | Responsivität | Nutzbar auf Desktop, Tablet und Smartphone ab 360 px Breite | UI-Test |
| NFA-008 | Barrierefreiheit | Zielkonformität WCAG 2.1 AA / EN 301 549 für ausschreibungsrelevante Oberflächen | Accessibility-Audit |
| NFA-009 | Wiederherstellung | RPO 24 h, RTO 8 h als Standardannahme für nichtkritischen Fachbetrieb | Restore-Test |
| NFA-010 | Protokollierung | Sicherheits- und Admin-Ereignisse müssen nachvollziehbar protokolliert werden | Audit-Log-Prüfung |
| NFA-011 | Zahlungsanbieter-Webhooks | Zahlungs- und Abo-Webhooks müssen idempotent verarbeitet werden | Wiederholte Webhook-Zustellung erzeugt keine Doppelabrechnung |
| NFA-012 | Abrechnungskonsistenz | Billing Events müssen revisionssicher nachvollziehbar sein | Abgleich Partnerübersicht, Adminübersicht und Payment-Provider-Status |
| NFA-013 | Rechteprüfung | Effektive Berechtigungen müssen konsistent und performant ermittelt werden | Rollen-/Gruppen-/Override-Test |

## 15. Datenschutz, Sicherheit und Compliance

| Bereich | Anforderung |
|---|---|
| Rechtsgrundlage | Der Auftraggeber benennt Zwecke, Rechtsgrundlagen und Löschfristen der Verarbeitung. |
| Datenminimierung | Surveys erfassen nur für den jeweiligen Prozess erforderliche Daten. |
| Zugriffsschutz | Rollen-, gruppen- und berechtigungsbasierte Rechteprüfung für User, Partner, Admins und Sondergruppen. |
| Mandantentrennung | Survey-Kontexte müssen bei Steps und Progress technisch getrennt berücksichtigt werden. |
| Auftragsverarbeitung | Bei Betrieb durch Dienstleister ist ein AV-Vertrag nach DSGVO vorzusehen. |
| Löschkonzept | Nutzer- und Uploaddaten müssen nach definierten Fristen löschbar sein. |
| Auskunft/Export | Personenbezogene Daten sollen für Auskunftsanfragen exportierbar sein. |
| Verschlüsselung Transport | Produktivbetrieb ausschließlich über TLS 1.2 oder höher. |
| Secret-Management | Secrets dürfen nicht im Quellcode gespeichert werden. |
| Passwortschutz | Mindestlänge 8 Zeichen; produktiv empfohlen: 12 Zeichen und Rate-Limiting. |
| Audit | Admin- und sicherheitsrelevante Aktionen werden protokolliert. |
| Rechteänderungen | Änderungen an Gruppen, Berechtigungen und Mitgliedschaften werden auditierbar gespeichert. |
| Zahlungsdaten | Kreditkarten- und Zahlungsinstrumentdaten werden nicht lokal gespeichert, sondern vom Zahlungsanbieter verarbeitet. |
| Abrechnungsdaten | Umsatz-, Abo- und Billing-Event-Daten gelten als geschäftsrelevante Daten und werden rollenbasiert geschützt. |

## 16. Liefergegenstände und Mitwirkung

### 16.1 Liefergegenstände

| Liefergegenstand | Beschreibung |
|---|---|
| Quellcode | Backend, Frontend, Tests, Skripte und Konfigurationen |
| Dokumentation | Lastenheft, Pflichtenheft, Betriebsnotizen, Exportskripte |
| Testkonzept | Automatisierte Backend-, Security-, Performance- und E2E-Testfälle |
| Deployment-Anleitung | Start, Konfiguration, Seed, Backup/Restore und Monitoring-Hinweise |
| Schulungsunterlagen | Kurzunterlagen für Admins und Partner |
| Abrechnungskonzept | Beschreibung von Partner-Abo, Milestone-Billing, Zahlungsanbieterintegration und Reporting |
| Abnahmeprotokoll | Liste der Anforderungen mit Nachweisstatus |

### 16.2 Mitwirkung des Auftraggebers

| Thema | Erforderliche Angabe |
|---|---|
| Auftraggeberdaten | Organisation, Ansprechpartner, Rechnungs-/Vergabestelle |
| Datenschutz | Zwecke, Rechtsgrundlagen, Aufbewahrungs- und Löschfristen |
| Hosting | Eigenbetrieb, Rechenzentrum, Cloudanbieter, Region |
| Barrierefreiheit | Gewünschte Prüfstelle und Zielstandard, sofern über WCAG 2.1 AA hinausgehend |
| Fachinhalte | Finale Survey-Texte, Step-Inhalte, E-Mail-Texte, Partnerlisten |
| Abrechnung | Preis je Abo, Preis je abgeschlossenem Meilenstein, Steuerlogik, Rechnungs-/Gutschriftsprozess |
| Zahlungsanbieter | Stripe-Konto oder alternativer Anbieter, API-Zugänge, Webhook-Konfiguration |
| Betrieb | Supportzeiten, Eskalationswege, Wartungsfenster |

## 17. Abnahme, Nachweise und Bewertung

### 17.1 Abnahmeverfahren

| Phase | Inhalt | Ergebnis |
|---|---|---|
| Vorabnahme | Installation, Smoke-Tests, Baseline-Seed, Rollenlogin | Vorabnahmeprotokoll |
| Fachabnahme | Durchlauf eines Ärzte- und Pflege-Beispielszenarios | Fachliche Freigabe oder Mängelliste |
| Sicherheitsabnahme | Upload-, Rechte-, Auth- und Audit-Prüfung | Sicherheitsnachweis |
| Abrechnungsabnahme | Partnerregistrierung, Aboabschluss, Milestone-Abrechnung und Reporting | Abrechnungsprotokoll |
| Performance-Abnahme | Messung zentraler Reload- und Listenendpunkte | Performance-Protokoll |
| Endabnahme | Prüfung aller Muss-Anforderungen | Abnahmeprotokoll |

### 17.2 Beispielhafte Bewertungsmatrix

| Kriterium | Gewichtung |
|---|---:|
| Fachliche Erfüllung der Muss-/Soll-Anforderungen | 35 % |
| Technische Qualität, Wartbarkeit und Testabdeckung | 25 % |
| Datenschutz, Sicherheit und Barrierefreiheit | 20 % |
| Betriebskonzept, Support und Dokumentation | 10 % |
| Preis / Wirtschaftlichkeit | 10 % |

## 18. Annahmen und offene Auftraggeberangaben

| Angabe | Aktuelle Annahme | Vom Auftraggeber zu bestätigen |
|---|---|---|
| Produktivhosting | Containerfähige Linux-Umgebung mit MongoDB und persistentem Storage | Ja |
| Zielnutzerzahl | Startauslegung 10.000 registrierte Nutzer | Ja |
| Gleichzeitige Nutzer | Startwert 100 aktive Sessions | Ja |
| Supportzeit | Werktags 09:00-17:00 Uhr | Ja |
| Wartungsfenster | Nach Ankündigung außerhalb Kernzeiten | Ja |
| Löschfristen | Noch offen | Ja |
| Barrierefreiheitsprüfung | WCAG 2.1 AA / EN 301 549 als Ziel | Ja |
| Zahlungsanbieter | Stripe als Beispielanbieter angenommen | Ja |
| Abrechnungsmodell | Abo plus nutzungsabhängige Abrechnung pro abgeschlossenem Partner-Meilenstein | Ja |

## 19. Partnerregistrierung, Abonnements und Abrechnung

### 19.1 Fachlicher Zielzustand

Partnerorganisationen sollen sich eigenständig registrieren, ein Abo über einen
Zahlungsanbieter buchen und danach im System als aktive Partner auftreten
können. Als Beispiel wird Stripe verwendet. Die Plattform soll dennoch so
beschrieben und umgesetzt werden, dass ein späterer Austausch des
Zahlungsanbieters möglich bleibt.

Die Abrechnung besteht aus zwei fachlichen Bestandteilen:

- einem Partner-Abo als Grundlage für die Nutzung der Plattform;
- einer nutzungsabhängigen Abrechnung pro abgeschlossenem Nutzer-Meilenstein,
  den der Partner bearbeitet oder freigibt.

### 19.2 Partnerregistrierung

| ID | Priorität | Anforderung | Akzeptanzkriterium |
|---|---|---|---|
| BILL-M-001 | Muss | Öffentliche Partnerregistrierung muss verfügbar sein. | Interessierte Partner können über eine eigene Seite Stammdaten erfassen. |
| BILL-M-002 | Muss | Partnerregistrierung muss einen Prüf- oder Freigabestatus besitzen. | Neue Partner sind bis Aktivierung nicht voll in Matching/Abrechnung nutzbar. |
| BILL-M-003 | Muss | Partner müssen ein Abo über den Zahlungsanbieter starten können. | Nach erfolgreichem Checkout wird der Partnerstatus auf zahlungsaktiv gesetzt. |
| BILL-M-004 | Muss | Abo-Statusänderungen müssen verarbeitet werden. | Kündigung, Zahlungsverzug oder ausbleibende Zahlung schränken Partnerfunktionen gemäß Regelwerk ein. |

### 19.3 Milestone-Abrechnung

| ID | Priorität | Anforderung | Akzeptanzkriterium |
|---|---|---|---|
| BILL-M-005 | Muss | Abrechnungsrelevante Meilensteine müssen je Survey/Step konfigurierbar sein. | Admin kann festlegen, welche Partner-Meilensteine abrechenbar sind. |
| BILL-M-006 | Muss | Jeder Partnerabschluss erzeugt ein Billing Event. | Ein abgeschlossener Partner-Meilenstein erzeugt ein eindeutiges, nachvollziehbares Event. |
| BILL-M-007 | Muss | Doppelte Abrechnung desselben Meilensteins muss verhindert werden. | Wiederholtes Speichern oder Webhook-Replay erzeugt kein zweites Billing Event. |
| BILL-M-008 | Muss | Billing Events müssen Partner, Nutzer, Survey, Step, Zeitpunkt und Betrag referenzieren. | Partner- und Adminübersicht können jeden Umsatz auf einen Abschluss zurückführen. |

### 19.4 Übersichten und Reporting

| Rolle | Übersicht | Inhalte |
|---|---|---|
| Partner | Eigene Umsatz-/Abschlussübersicht | Abrechnungsperiode, abgeschlossene Meilensteine, Nutzerreferenz, Betrag, Status, Zahlungs-/Rechnungsstatus |
| Admin | Gesamtübersicht aller Partnerabrechnungen | Partner, Perioden, Summen, Einzelereignisse, Zahlungsanbieter-IDs, Exportstatus, Fehlerfälle |
| Betreiber | Controlling- und Exportdaten | CSV/Excel-Export, Filter nach Zeitraum, Partner, Survey, Status |

### 19.5 Offene fachliche Entscheidungen

| Thema | Zu klären |
|---|---|
| Abo-Preis | Monatlicher oder jährlicher Grundpreis je Partner |
| Milestone-Preis | Betrag pro abgeschlossenem Partner-Meilenstein, ggf. je Survey/Step unterschiedlich |
| Steuerlogik | Brutto/Netto, Umsatzsteuer, Reverse Charge, internationale Partner |
| Rechnungsmodell | Rechnung durch Zahlungsanbieter, interne Gutschrift oder Export an Buchhaltung |
| Sperrlogik | Welche Partnerfunktionen bei inaktivem oder überfälligem Abo gesperrt werden |

## 20. Glossar

| Begriff | Bedeutung |
|---|---|
| Survey | Fachlich eigenständige Journey-Konfiguration mit Slug, Steps, Branding und Progress-Kontext |
| Step | Einzelner Prozessbaustein innerhalb eines Surveys |
| Decision-Step | Step, der anhand einer Nutzerauswahl Folgepfade steuert |
| Upload-Step | Step, der Dokumente oder Nachweise entgegennimmt |
| Partner-Step | Step zur Auswahl eines oder mehrerer externer Dienstleister |
| Meilenstein | Step, der den Abschluss einer Etappe markiert und Folgeblöcke freischaltet |
| Condition | Regel zur Sichtbarkeit, Sperrung oder automatischen Fertigstellung eines Steps |
| Progress | Nutzerbezogener Bearbeitungsstand eines Steps |
| Partner Submission | Einreichung eines Nutzers bei einer Partnerorganisation |
| Nutzergruppe | Zusammenfassung von Nutzern mit gemeinsamem Berechtigungsprofil |
| Berechtigung | Granulares Recht für eine Funktion oder Ressource, z. B. Lesen, Schreiben, Exportieren oder Verwalten |
| Berechtigungsprofil | Wiederverwendbare Sammlung von Berechtigungen für Gruppen oder Sonderrollen |
| Override | Explizite Abweichung von Gruppen- oder Rollenrechten für einen einzelnen Nutzer |
| Admin | Rolle für System- und Stammdatenverwaltung |

## 21. Anforderungskatalog

| ID | Priorität | Anforderung | Akzeptanzkriterium |
|---|---|---|---|
| LF-M-001 | Muss | Das System muss mehrere Surveys parallel betreiben können. | Mindestens `aerzte` und `pflege` sind getrennt aufrufbar und besitzen getrennte Steps. |
| LF-M-002 | Muss | Nutzer müssen über Survey-spezifische URLs registriert werden können. | Registrierung über `/s/:surveySlug/register` speichert den passenden Survey am Nutzer. |
| LF-M-003 | Muss | Steps müssen survey-spezifisch geladen und bearbeitet werden. | Ein Nutzer sieht nur Steps seines Surveys; Admin-Listen sind nach Survey filterbar. |
| LF-M-004 | Muss | Conditions müssen sichtbare, versteckte, blockierte und automatisch abgeschlossene Steps ermöglichen. | Testfälle zeigen korrekte Visibility-, Blocking- und Auto-Complete-Zustände. |
| LF-M-005 | Muss | Uploads müssen sichere Dateitypen und Größenbegrenzungen erzwingen. | Nicht erlaubte Dateitypen und aktive Inhalte werden abgelehnt. |
| LF-M-006 | Muss | Partner dürfen nur berechtigte Nutzer und Dateien sehen. | Zugriff auf fremde Dateien ohne Zuordnung führt zu Ablehnung. |
| LF-M-007 | Muss | Admins müssen Surveys, Steps, Nutzer, Partner und E-Mail-Vorlagen verwalten können. | Admin-Dashboard bietet die entsprechenden Verwaltungsfunktionen. |
| LF-M-008 | Muss | Fortschritt und ETA müssen aus sichtbaren relevanten Steps berechnet werden. | Hidden Steps beeinflussen Fortschritt und ETA nicht. |
| LF-M-009 | Muss | Partner müssen sich über eine eigene Registrierungsseite anmelden können. | `/partner/register` führt durch Partnerkontoanlage und speichert Partner-Stammdaten. |
| LF-M-010 | Muss | Partner müssen ein Abo über einen Zahlungsanbieter buchen können. | Nach erfolgreichem Checkout wird ein aktiver Subscription-Status am Partner gespeichert. |
| LF-M-011 | Muss | Abrechnung muss pro durch Partner abgeschlossenem Nutzer-Meilenstein erfolgen. | Jeder abrechnungsrelevante Partnerabschluss erzeugt genau ein Billing Event. |
| LF-M-012 | Muss | Partner müssen eigene Umsätze und Abschlüsse einsehen können. | Partner-Dashboard zeigt Abrechnungsperioden, abgeschlossene Milestones, Beträge und Status. |
| LF-M-013 | Muss | Admins müssen alle Partnerabrechnungen zentral einsehen können. | Admin-Dashboard zeigt Partner, Perioden, Summen, Billing Events und Zahlungsstatus. |
| LF-M-014 | Muss | Das System muss Nutzergruppen verwalten können. | Admins können Gruppen anlegen, bearbeiten, deaktivieren und Nutzer zuordnen. |
| LF-M-015 | Muss | Das System muss granulare Berechtigungen je Funktionsbereich unterstützen. | Zugriff auf Surveys, Steps, Nutzer, Partner, Billing, Dateien, CMS, E-Mails und Audit Logs ist einzeln steuerbar. |
| LF-M-016 | Muss | Effektive Nutzerrechte müssen aus Rolle, Gruppen und Overrides berechnet werden. | Ein Testnutzer erhält exakt die erwarteten Rechte aus kombinierten Gruppenmitgliedschaften. |
| LF-M-017 | Muss | Änderungen an Rechten und Gruppenmitgliedschaften müssen auditierbar sein. | Audit Log zeigt wer wann welche Berechtigung geändert hat. |
| LF-S-001 | Soll | Survey-spezifisches Branding soll unterstützt werden. | Landing/Auth können Logo, Farben und Texte je Survey verwenden. |
| LF-S-002 | Soll | E-Mail-Vorlagen sollen über Admin-Oberfläche bearbeitbar sein. | Admin kann Template speichern, zurücksetzen und Vorschau erzeugen. |
| LF-S-003 | Soll | Partner-Matching soll über Tags und Profilinformationen unterstützt werden. | Partnerlisten berücksichtigen fachliche Tags und Nutzerprofilfelder. |
| LF-S-004 | Soll | Zahlungsanbieterintegration soll anbieterneutral gekapselt sein. | Stripe-spezifische IDs und Webhooks sind technisch isoliert und austauschbar. |
| LF-K-001 | Kann | Step-Konfigurationen können exportiert und importiert werden. | JSON-Export/-Import ist als Erweiterung spezifiziert. |
| LF-K-002 | Kann | Webhooks können externe Systeme informieren. | Ereignisse wie neue Partneranfrage können später per Webhook ausgeleitet werden. |
