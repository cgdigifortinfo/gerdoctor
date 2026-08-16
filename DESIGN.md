# FSPP UI/UX Redesign Specification

## Objective

Redesign the existing React application into a calm, modern and intuitive
professional SaaS interface.

The redesign must **NOT** change business logic, API contracts, routing,
permissions, validation, data structures or workflow behavior unless explicitly
requested.

The existing frontend stack must be retained:

- React 19
- Create React App / react-scripts 5
- CRACO 7
- React Router DOM 7
- Tailwind CSS 3.4
- Radix UI
- existing shadcn/ui-style component architecture
- class-variance-authority
- clsx
- tailwind-merge
- React Hook Form
- Zod
- React Flow
- Recharts
- Sonner
- Lucide / existing icons

Do not migrate to Next.js, Vue, Angular or TypeScript.

---

## Unit System

Use **rem for all sizes** in the application design system.

The root font size is based on the browser default of **16px = 1rem**.

Recommended root configuration:

```css
html {
  font-size: 100%;
}
```

Conversion reference:

| rem | Equivalent at 16px root |
|---:|---:|
| 0.25rem | 4px |
| 0.375rem | 6px |
| 0.5rem | 8px |
| 0.625rem | 10px |
| 0.75rem | 12px |
| 0.8125rem | 13px |
| 0.875rem | 14px |
| 1rem | 16px |
| 1.125rem | 18px |
| 1.25rem | 20px |
| 1.5rem | 24px |
| 1.75rem | 28px |
| 2rem | 32px |
| 2.25rem | 36px |
| 2.5rem | 40px |
| 3rem | 48px |

### Rules

- Do not introduce fixed pixel values for spacing, typography, widths, heights,
  border radii or control sizes.
- Prefer Tailwind utilities that resolve to rem values.
- If custom CSS is necessary, express dimensions in rem.
- Percentages, `vh`, `vw`, `fr`, `auto`, `min-content`, `max-content` and
  `clamp()` may be used where they are semantically appropriate.
- Hairline borders may use the framework's standard border utilities.
- Avoid absolute component heights unless they improve usability.
- Do not change the root font size below 100%; accessibility and browser zoom
  behavior must remain intact.

---

## Design Philosophy

The interface should feel calm, familiar and highly polished.

Use design principles inspired by:

- Apple: clarity, hierarchy, whitespace, restrained visual language
- Linear: professional SaaS density and interaction design
- Notion: progressive disclosure and understandable information architecture
- Stripe: forms, settings and admin workflows

Do not visually clone any of these products.

Primary goals:

1. Reduce cognitive load.
2. Create stronger information hierarchy.
3. Make primary actions immediately identifiable.
4. Hide infrequent actions until needed.
5. Create consistent interaction patterns.
6. Preserve efficient workflows for power users.
7. Improve accessibility and readable target sizes.

---

## Design Tokens

Create semantic Tailwind-compatible design tokens.

### Surfaces

```text
app background:  #F7F8F8
surface:         #FFFFFF
surface subtle:  #F4F5F5
surface hover:   #F0F2F2
```

### Text

```text
text primary:    #18181B
text secondary:  #71717A
text tertiary:   #A1A1AA
```

### Borders

```text
default:         #E4E4E7
strong:          #D4D4D8
```

### Brand

Use the existing FSPP petrol as the main primary action color.

Do not introduce additional decorative primary colors.

### Semantic States

Provide consistent semantic tokens for:

- success
- warning
- danger
- info

Use low-saturation background variants for status areas.

Do not communicate status solely through color.

---

## Typography

Use a modern sans-serif system stack.

Recommended:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

### Base typography

```text
Root / body base:       1rem
Regular UI text:        0.875rem–1rem
Secondary text:         0.8125rem–0.875rem
Small metadata:         0.75rem–0.8125rem
```

Avoid interface text below `0.75rem` except for exceptional,
non-essential metadata.

### Heading scale

```text
Page title:             1.5rem–1.75rem / semibold
Section title:          1.125rem–1.25rem / semibold
Card title:             0.875rem–1rem / medium or semibold
Body:                   0.875rem–1rem / regular
Caption / metadata:     0.75rem–0.8125rem / regular
```

### Line height

Use relaxed, readable line heights:

```text
Headings:               1.2–1.3
Body:                   1.45–1.6
Secondary / metadata:   1.4–1.5
```

---

## Spacing

Use a consistent `0.25rem` base spacing scale.

Preferred spacing values:

```text
0.25rem
0.5rem
0.75rem
1rem
1.25rem
1.5rem
2rem
2.5rem
3rem
```

### Layout spacing

```text
Desktop page horizontal padding:  2rem
Card padding:                     1.25rem–1.5rem
Form vertical field gap:          1rem–1.25rem
Section gap:                      2rem–3rem
Compact control gap:              0.5rem
Normal control gap:               0.75rem–1rem
```

Prefer spacing and surface contrast over unnecessary container borders.

---

## Radius

Use a restrained radius system.

```text
Small controls:       0.375rem–0.5rem
Buttons / inputs:     0.5rem
Cards:                0.625rem–0.75rem
Dialogs / sheets:     0.875rem–1rem
```

Do not use excessive pill-shaped controls.

Pill shapes are appropriate only for items such as compact status badges,
filters or tags.

---

## Shadows

Use shadows sparingly.

Cards should normally use borders or subtle surface contrast.

Use shadows primarily for:

- dialogs
- dropdowns
- floating inspectors
- floating toolbars
- popovers

Avoid strong shadows on ordinary content cards.

---

## Buttons

Implement reusable variants:

- `primary`
- `secondary`
- `ghost`
- `destructive`
- `icon`

Primary actions use brand petrol.

Destructive actions should not appear permanently as red bordered buttons
inside repetitive rows.

Move low-frequency actions into overflow menus.

### Button sizing

```text
Minimum regular control height:   2.25rem
Preferred primary button height:  2.5rem
Compact icon button:              2.25rem × 2.25rem
Normal horizontal padding:        0.875rem–1rem
Compact horizontal padding:       0.625rem–0.75rem
```

Interactive targets should remain comfortably usable on touch devices.

---

## Inputs and Selects

Use consistent sizing across text inputs, selects, comboboxes and date controls.

```text
Default control height:      2.5rem
Compact control height:      2.25rem
Horizontal padding:          0.75rem
Label-to-control gap:        0.375rem–0.5rem
Helper-text gap:             0.375rem
```

Do not rely on placeholders as labels.

Use:

1. label
2. optional helper text
3. control
4. validation message

---

## Badges and Status Indicators

Badges should be visually subtle and should not compete with primary content.

Recommended sizing:

```text
Font size:               0.75rem
Height:                  1.5rem–1.75rem
Horizontal padding:      0.5rem
Radius:                  0.375rem–0.5rem
```

Prefer tinted backgrounds with readable text rather than highly saturated
solid fills.

---

## Global App Layout

Create a persistent application shell.

### Top Bar

Top bar contains:

- logo left
- product/context indication
- global user actions right
- subtle bottom border

Recommended dimensions:

```text
Top bar minimum height:      4rem
Horizontal padding:          2rem
Logo area gap:               0.75rem
```

### Main Navigation

Use one consistent navigation system.

Avoid multiple visually competing horizontal navigation rows.

Recommended navigation item sizing:

```text
Height:                  2.5rem
Horizontal padding:      0.75rem–1rem
Gap between items:       0.25rem
```

### Page Structure

Each page should use:

```text
AppShell
└── PageContainer
    ├── PageHeader
    └── PageContent
```

`PageHeader` contains:

- title
- short optional description
- primary action
- optional secondary actions

Recommended layout:

```text
Page content max width:      use responsive container, not a fixed pixel width
Page vertical padding:       2rem
Header bottom gap:           1.5rem–2rem
```

---

## Cards

Cards should represent meaningful content groups, not every possible wrapper.

Recommended values:

```text
Padding:                 1.25rem–1.5rem
Radius:                  0.625rem–0.75rem
Header/content gap:      1rem
Internal row gap:        0.75rem–1rem
```

Avoid nested cards when spacing and headings are enough to create hierarchy.

---

## Flow Editor

The Flow Editor is the primary complex workspace.

### Workspace

The flow canvas should receive most of the available viewport.

Avoid placing the entire editor inside multiple nested bordered cards.

Use a lightweight canvas workspace.

Recommended sizing:

```text
Minimum practical editor height:  40rem
Toolbar height:                   2.5rem
Toolbar gap:                      0.5rem
Canvas internal padding:          1.5rem
```

When viewport space permits, the editor should expand with available height
instead of being constrained to a small fixed canvas.

---

## Flow Editor Left Palette

Provide a collapsible left palette for step types.

Each type contains:

- icon
- label
- small semantic color marker

Support drag and drop.

Also support creation through a primary `+ Schritt` action.

Recommended sizing:

```text
Expanded width:           13rem–15rem
Collapsed width:          3.5rem
Section padding:          1rem
Palette item height:      2.5rem
Palette item gap:         0.375rem
```

Do not require drag and drop as the only discoverable creation mechanism.

---

## Flow Node Design

Nodes must be visually calm.

Default node displays:

- order
- title
- type

Do not display excessive metadata by default.

Use neutral white surfaces with a small colored type indicator.

Recommended sizing:

```text
Default node width:       12rem–14rem
Minimum node height:      4rem
Node padding:             0.75rem
Node radius:              0.625rem
Header/body gap:          0.5rem
Type indicator width:     0.25rem
```

Selected nodes receive:

- stronger border
- subtle brand-tinted background or focus ring
- visible handles

Hover may reveal quick actions.

Node text hierarchy:

```text
Type / order:             0.75rem
Title:                    0.875rem
Secondary metadata:       0.75rem
```

---

## Flow Node Inspector

Clicking a node should open a right-side inspector.

Use the inspector for common edits:

- title
- type
- active
- skippable
- duration
- key metadata

Keep the canvas visible while editing.

Provide `Weitere Einstellungen` to access complex editor sections.

Recommended sizing:

```text
Inspector width:          20rem–24rem
Inspector padding:        1.25rem
Section gap:              1.5rem
Field gap:                1rem
```

On narrower layouts, use the existing Radix Sheet pattern instead of permanently
reserving the right side.

---

## Advanced Step Editor

Complex step settings may use a larger Sheet or Dialog:

- Fields
- Requirements
- Mappings
- Conditions
- Notifications
- language content

Avoid tiny horizontal tabs when possible.

For large configuration sets, prefer side navigation inside the editor.

Recommended sizing:

```text
Dialog width:             min(52rem, calc(100vw - 3rem))
Dialog max height:        calc(100vh - 3rem)
Dialog padding:           1.5rem
Footer top gap:           1.5rem
```

Use internal scrolling for long forms rather than allowing the dialog to grow
beyond the viewport.

---

## Flow Connections

Connection conditions must be displayed in human-readable language.

Example:

```text
Wenn
[decision] [ist nicht] [upload]

Dann
[Dokumente Anerkennung ausblenden]
```

Intern the existing data model may remain unchanged.

Connection labels should be hidden by default when they create visual noise and
shown on hover, selection or suitable zoom level.

---

## Flow Toolbar

Simplify the toolbar.

Primary actions:

```text
+ Schritt
Auto-Layout
```

Utility group:

```text
Undo
Redo
Zoom
Fit View
Fullscreen
```

Recommended sizing:

```text
Control height:           2.5rem
Icon-only control:        2.5rem × 2.5rem
Toolbar gap:              0.5rem
Toolbar group gap:        1rem
```

Move legends and infrequent settings into menus or popovers.

---

## Flow Modes

Separate:

```text
Bearbeiten
Simulation
```

When simulation mode is active:

- hide or disable editing controls
- emphasize current simulated node
- dim irrelevant nodes
- show simulation progress in a dedicated floating panel

Recommended floating simulation panel:

```text
Minimum height:           2.75rem
Horizontal padding:       1rem
Radius:                   0.75rem
```

---

## Mini-map

Retain the React Flow mini-map.

Use reduced visual emphasis.

Recommended sizing:

```text
Width:                    10rem–12rem
Height:                   6rem–8rem
Outer offset:             1rem
Radius:                   0.5rem
```

It may be hidden automatically for small/simple flows.

---

## Lists and Tables

Reduce permanent action buttons.

Example row:

```text
[03]  Anerkennung beantragen                     Aktiv
      Antrag zur Anerkennung
      Entscheidung · Sofort              Bearbeiten   ···
```

Move:

- duplicate
- template
- delete
- deactivate

into overflow menus when practical.

Deletion should require explicit confirmation.

Recommended row sizing:

```text
Row vertical padding:       0.875rem–1rem
Row horizontal padding:     1rem
Primary row gap:            0.375rem
Metadata gap:               0.5rem
Action gap:                 0.5rem
```

Avoid putting every row inside a strongly outlined card if the list itself
already provides sufficient structure.

---

## Forms

Use clear, readable grouping.

Recommended:

```text
Field vertical gap:         1rem
Group gap:                  1.5rem–2rem
Label font size:            0.875rem
Helper font size:           0.8125rem
Validation font size:       0.8125rem
Textarea min height:        6rem
```

Use consistent input height.

Group related fields using whitespace rather than drawing boxes around every
group.

Switches should show clear labels.

---

## Dialogs

Use Radix Dialog / Sheet consistently.

Use:

- small confirmation → Dialog
- complex editing → large Dialog or Sheet
- context-preserving editing → right-side Sheet / Inspector

Recommended sizing:

```text
Small dialog width:         min(28rem, calc(100vw - 2rem))
Medium dialog width:        min(38rem, calc(100vw - 2rem))
Large dialog width:         min(52rem, calc(100vw - 3rem))
Dialog padding:             1.5rem
Header/content gap:         1rem
Content/footer gap:         1.5rem
```

Footer order:

1. secondary action
2. primary action

Never make `Abbrechen` look destructive.

---

## Dropdowns and Popovers

Use progressive disclosure for low-frequency actions.

Recommended sizing:

```text
Minimum menu item height:   2.25rem
Menu padding:               0.375rem
Menu item horizontal pad:   0.75rem
Menu radius:                0.625rem
```

Destructive menu items may use danger text but should remain visually secondary
until selected.

---

## Toasts

Use Sonner consistently.

Success:

- short confirmation

Error:

- clear cause
- useful next action where known

Do not use a toast for information that requires user acknowledgement.

Recommended toast dimensions:

```text
Minimum height:             3rem
Padding:                    0.875rem–1rem
Radius:                     0.75rem
Gap between icon/text:      0.75rem
```

---

## Accessibility

All interactive controls require:

- keyboard support
- visible focus state
- appropriate aria labels
- comfortable click/touch targets
- sufficient contrast

Do not communicate status solely through color.

Recommended focus ring:

```text
Ring width:                 0.125rem
Ring offset:                0.125rem
```

Recommended minimum interactive target:

```text
2.5rem × 2.5rem
```

Smaller visible icons may sit inside a larger invisible interaction target.

---

## Responsive Behavior

### Admin Workspace

Desktop-first, but usable down to tablet width.

Flow editor behavior:

- collapse palette when space is limited
- inspector becomes Sheet
- group toolbar actions into overflow menus
- preserve canvas space as highest priority

### Public / User-facing Application

Mobile-first.

Recommended page padding:

```text
Small screens:              1rem
Medium screens:             1.5rem
Large screens:              2rem
```

Use fluid layouts and `clamp()` where appropriate.

Avoid hardcoded fixed widths that cause horizontal overflow.

---

## Public Landing Pages

The current public landing pages are already calmer than the admin interface.
Do not radically redesign them.

Instead:

- align typography with the application design system
- use the same brand color tokens
- use consistent buttons, radius and spacing
- keep generous whitespace
- reduce unnecessary card borders
- preserve strong hero hierarchy
- make the transition from public website to logged-in application feel like
  the same product family

Recommended content widths should use responsive max-width containers rather
than fixed absolute dimensions.

---

## Component Architecture

Create or normalize reusable primitives before migrating individual pages.

Recommended core components:

```text
AppShell
TopBar
MainNavigation
PageContainer
PageHeader
PageActions

Button
IconButton
Input
Textarea
Select
Combobox
Checkbox
Switch
Badge
StatusBadge

Card
Section
Divider

Tabs
SegmentedControl

DropdownMenu
Popover
Tooltip

Dialog
Sheet
ConfirmDialog

DataTable
ListRow
EmptyState
LoadingState

FlowToolbar
FlowPalette
FlowNode
FlowInspector
FlowMiniMap
SimulationPanel
```

Do not duplicate large Tailwind class strings across many feature components
when a reusable component or CVA variant can represent the same UI.

---

## Tailwind Guidance

Prefer the standard Tailwind spacing scale whenever it resolves to the intended
rem value.

Examples:

```text
p-1   → 0.25rem
p-2   → 0.5rem
p-3   → 0.75rem
p-4   → 1rem
p-5   → 1.25rem
p-6   → 1.5rem
p-8   → 2rem
p-10  → 2.5rem
p-12  → 3rem
```

For values not represented in the default project scale, use semantic theme
extensions instead of scattered arbitrary values.

Example:

```js
// tailwind.config.js
theme: {
  extend: {
    borderRadius: {
      card: '0.75rem',
      dialog: '1rem',
    },
    spacing: {
      '18': '4.5rem',
    },
  },
}
```

Prefer semantic component classes and CVA variants over repeated arbitrary
utility strings.

---

## Implementation Order

Do **not** redesign the whole application in one uncontrolled pass.

### Phase 1 — Foundation

Create and normalize:

- design tokens
- typography
- Button
- IconButton
- Input
- Textarea
- Select
- Badge
- StatusBadge
- Tabs
- DropdownMenu
- Dialog
- Sheet
- PageHeader
- AppShell

### Phase 2 — Reference Screen

Redesign the Flow Editor first.

This is the reference implementation for:

- spacing
- hierarchy
- controls
- inspector patterns
- overlays
- status states

### Phase 3 — Step Management

Redesign:

- step list
- step create/edit flows
- condition editor
- template actions
- simulation controls

### Phase 4 — Admin Areas

Migrate:

- users
- partners
- CMS
- email templates
- audit log
- settings

### Phase 5 — Public/User-facing Experience

Align:

- public landing pages
- login/registration
- user dashboard
- guided journey
- partner-facing views

---

## Implementation Safety Rules

1. Do not alter business logic during visual refactoring.
2. Do not alter API request/response structures.
3. Do not alter route semantics.
4. Do not alter authorization or role checks.
5. Do not alter Zod schemas unless explicitly required.
6. Preserve React Hook Form behavior.
7. Preserve React Flow graph semantics.
8. Preserve all existing workflow conditions and mappings.
9. Preserve existing automated tests.
10. Add tests when interaction behavior is moved between components.
11. Avoid page-specific CSS when a reusable component can solve the same need.
12. All newly introduced dimensions must use rem-based sizing or fluid CSS
    units where appropriate.

---

## Definition of Done

A migrated screen is complete only when:

- visual hierarchy is clear
- primary action is immediately identifiable
- unnecessary actions are progressively disclosed
- spacing follows the rem-based token system
- typography follows the shared scale
- keyboard interaction works
- focus states are visible
- responsive behavior works
- no business functionality has changed unintentionally
- no new arbitrary pixel dimensions have been introduced
- reusable components are used where appropriate
- the screen visually belongs to the same design system as the rest of the app
