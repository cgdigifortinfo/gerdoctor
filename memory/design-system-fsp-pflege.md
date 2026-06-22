# Design-System FSP Pflege

Stand: 2026-06-22

Referenz: `https://fsp-pflege.de/`

Diese Notiz beschreibt die aus der Referenzseite uebernommenen Design-Grundlagen und was im Frontend bereits umgesetzt wurde.

## Brand-Kontext

Die aktuelle Version soll nicht mehr primär Aerzte aus dem Ausland ansprechen, sondern Pflegekraefte aus dem Ausland, die in Deutschland arbeiten wollen, z. B. Altenpflege, Gesundheits- und Krankenpflege oder Pflegefachkraft.

Der Ton der UI soll deshalb nicht nach medizinischer Approbation fuer Aerzte klingen, sondern nach Anerkennung, Sprachpruefung, Registrierung und Orientierung fuer internationale Pflegekraefte.

## Farben

Aus der Referenzseite uebernommen:

- Dunkles Petrol: `#004856`
- Mint: `#7ed9c6`
- Coral/CTA: `#ff6b6b`
- Petrol Hover: `#003845`
- Heller Mint-Hintergrund: `#e6faf6`

Im Frontend liegen diese Werte in `frontend/src/index.css` als CSS-Variablen:

- `--brand-primary`
- `--brand-secondary`
- `--brand-accent`
- `--brand-primary-hover`
- `--brand-soft`

Tailwind/HSL-Basisvariablen wurden ebenfalls auf diese Markenfarben angepasst:

- `--primary`
- `--secondary`
- `--accent`
- `--ring`
- `--sidebar-primary`

## Fonts

Die Referenzseite nutzt:

- `Montserrat` fuer normalen Text
- `Varela Round` fuer Headings/Brand-Wirkung

Im Frontend wird das in `frontend/src/index.css` importiert und gesetzt:

- `body`: `Montserrat`
- `h1` bis `h6`, `.brand-heading`: `Varela Round`

Wichtig: Letter-Spacing soll nicht negativ gesetzt werden. Hero-Typografie nur fuer echte Hero-Bereiche verwenden, nicht fuer kompakte Admin-/Dashboard-Panels.

## Logo und Icon

Referenz-Assets:

- Logo: `https://fsp-pflege.de/wp-content/uploads/2025/02/FSPP-Logo-Final.png`
- Icon: `https://fsp-pflege.de/wp-content/uploads/2025/03/FSPP-Icon-Vektor.svg`

Aktuelle Umsetzung:

- `frontend/src/components/Logo.js` rendert das FSP-Pflege-Logo.
- Der vorbereitete Survey `pflege` speichert Logo/Icon im `theme`-Objekt.
- Landing- und Auth-Seiten nutzen das neue Branding.

Hinweis: Wenn spaeter Offline-/Deployment-Unabhaengigkeit wichtig ist, sollten Logo und Icon als lokale Assets eingecheckt und nicht remote von `fsp-pflege.de` geladen werden.

## UX- und Layout-Regeln

Fuer die Pflege-Version gelten diese Regeln:

- Keine reine Marketing-Landingpage als Hauptprodukt; die erste Ansicht soll direkt zu Registrierung/Login und Survey fuehren.
- Admin- und Dashboard-Oberflaechen bleiben arbeitsorientiert, dicht und gut scannbar.
- Karten nur fuer einzelne wiederholte Elemente, Modals und echte Tool-Bereiche verwenden.
- Keine verschachtelten Cards.
- Buttons und interaktive Elemente nutzen Petrol/Mint/Coral konsistent.
- Texte duerfen in Buttons, Tabs und kompakten Panels nicht ueberlaufen.
- Mobile und Desktop muessen ohne Textueberlappung funktionieren.

## Bereits angepasste Frontend-Dateien

Branding/Global:

- `frontend/src/index.css`
- `frontend/src/App.css`
- `frontend/src/components/Logo.js`

Routing und Survey-Landing:

- `frontend/src/App.js`
- `frontend/src/pages/Landing.js`
- `frontend/src/pages/Auth.js`

Admin und Workflows:

- `frontend/src/pages/AdminDashboard.js`
- `frontend/src/pages/UserDashboard.js`
- `frontend/src/pages/PartnerDashboard.js`
- `frontend/src/components/FlowSimulatorPanel.js`
- `frontend/src/components/JourneyProgressIndicator.js`
- `frontend/src/components/StepsFlowBuilder.js`
- `frontend/src/components/admin/EmailTemplateEditor.js`

## Gepruefter Browser-Smoke

Geprueft wurde lokal:

- `/s/pflege` zeigt Pflege-spezifische Landing-Copy.
- Hero enthaelt `Anerkennung als Pflegefachkraft`.
- CTA `Jetzt registrieren` ist sichtbar.
- Logo wird gerendert.
- Admin-Step-Tab zeigt Survey-Auswahl und `FSP Pflege`.

## Offene Design-Aufgaben

- Pflege-spezifische Texte fuer Dashboard, E-Mails und Step-Beschreibungen finalisieren.
- Entscheiden, ob FSP-Pflege-Assets lokal gespeichert werden sollen.
- Spaetere Multi-Survey-Brandings pro Survey pruefen: Logo, Farben, Name, Slug, Landing-Copy.
- Browser-Screenshots fuer Desktop und Mobile nach dem finalen Pflege-Flow erneut pruefen.
