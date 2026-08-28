import { useEffect, useMemo, useState } from 'react';
import {
    ArrowDown, ArrowUp, Copy, FileText, Image as ImageIcon, MagnifyingGlass,
    Plus, TextT, Trash, UploadSimple,
} from '@phosphor-icons/react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { HelpLabel, HelpTooltip } from '../ui/help-tooltip';
import { asArray } from '../../lib/valueNormalization';
import {
    appendFieldOption, CHOICE_FIELD_TYPES, CONTENT_FIELD_TYPES, createField, duplicateField, moveField,
    optionLabel, optionValue, removeFieldOption, slugify, TYPE_LABELS, updateFieldOption,
} from './surveyFormDomain';

// Stryker disable all: survey-builder adapter; transformations live in surveyFormDomain.

export { createField, moveField, optionLabel, optionValue, slugify } from './surveyFormDomain';

const FIELD_GROUPS = [
    {
        label: 'Eingaben', icon: TextT,
        types: [
            ['text', 'Textfeld'], ['textarea', 'Textbereich'], ['email', 'E-Mail'], ['phone', 'Telefon'],
            ['number', 'Zahl'], ['date', 'Datum'], ['time', 'Uhrzeit'], ['checkbox', 'Checkbox'],
        ],
    },
    {
        label: 'Auswahl', icon: FileText,
        types: [
            ['selectbox', 'Auswahlliste'], ['radio', 'Einzelauswahl'], ['multiselect', 'Mehrfachauswahl'],
            ['decision', 'Entscheidungskarten'],
        ],
    },
    {
        label: 'Dateien', icon: UploadSimple,
        types: [['file', 'Datei-Upload'], ['multiupload', 'Dokumentenliste']],
    },
    {
        label: 'Inhalte', icon: ImageIcon,
        types: [
            ['heading', 'Überschrift'], ['paragraph', 'Textabsatz'], ['html', 'HTML-Inhalt'],
            ['image', 'Bild'], ['divider', 'Trennlinie'],
        ],
    },
];

const FIELD_TYPE_HELP = {
    text: 'Kurze einzeilige Texteingabe.', textarea: 'Mehrzeiliger Freitext mit Höhe und Zeichenbegrenzung.',
    email: 'E-Mail-Eingabe mit Formatprüfung.', phone: 'Eingabe für Telefonnummern.', number: 'Numerischer Wert mit Minimum, Maximum und Schrittweite.',
    date: 'Datumsauswahl.', time: 'Auswahl einer Uhrzeit.', checkbox: 'Einzelne Ja/Nein-Bestätigung.',
    selectbox: 'Kompakte Liste mit genau einer Auswahl.', radio: 'Alle Optionen sichtbar; genau eine Auswahl.', multiselect: 'Mehrere Werte aus einer Optionsliste.',
    decision: 'Große Entscheidungskarten; technische Werte werden von Conditions ausgewertet.', file: 'Einfacher Datei-Upload, optional mehrfach.',
    multiupload: 'Dokumentenliste; Optionen werden als Dokumenttypen für Requirements und Upload-Conditions genutzt.',
    heading: 'Reine Überschrift ohne Nutzereingabe.', paragraph: 'Erklärender Text ohne Nutzereingabe.', html: 'Formatierter HTML-Inhalt ohne Nutzereingabe.',
    image: 'Bild über URL mit Alternativtext und Bildunterschrift.', divider: 'Visuelle Trennlinie zwischen Bereichen.',
};


export function FieldPreview({ field }) {
    const label = field.label || TYPE_LABELS[field.field_type] || field.name;
    if (field.field_type === 'divider') return <hr className="my-2 border-border" />;
    if (field.field_type === 'heading') {
        const Tag = `h${field.heading_level || 2}`;
        return <Tag className="font-semibold text-foreground">{field.content || label}</Tag>;
    }
    if (field.field_type === 'paragraph' || field.field_type === 'html') {
        return <p className="line-clamp-2 text-sm text-muted-foreground">{field.content?.replace(/<[^>]*>/g, '') || label}</p>;
    }
    if (field.field_type === 'image') {
        return field.image_url
            ? <img src={field.image_url} alt={field.alt_text || ''} className="h-20 max-w-full rounded border border-border object-cover" />
            : <div className="flex h-16 items-center justify-center rounded border border-dashed border-border text-xs text-muted-foreground">Bildvorschau</div>;
    }
    return (
        <div className="space-y-1.5">
            <span className="text-sm font-medium text-foreground">{label}{field.required && <span className="ml-1 text-red-500">*</span>}</span>
            {CHOICE_FIELD_TYPES.has(field.field_type) || field.field_type === 'multiupload' ? (
                <div className="rounded border border-border bg-card px-3 py-2 text-xs text-muted-foreground">
                    {asArray(field.options).map(optionLabel).filter(Boolean).slice(0, 3).join(' · ') || 'Optionen ergänzen'}
                </div>
            ) : field.field_type === 'textarea' ? (
                <div className="h-14 rounded border border-border bg-card px-3 py-2 text-xs text-muted-foreground">{field.placeholder || 'Mehrzeilige Eingabe'}</div>
            ) : field.field_type === 'checkbox' ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="h-4 w-4 rounded border border-border" /> Auswahl</div>
            ) : field.field_type === 'file' ? (
                <div className="rounded border border-dashed border-border px-3 py-2 text-center text-xs text-muted-foreground">Datei auswählen</div>
            ) : (
                <div className="rounded border border-border bg-card px-3 py-2 text-xs text-muted-foreground">{field.placeholder || TYPE_LABELS[field.field_type]}</div>
            )}
            {field.help_text && <p className="text-[11px] text-muted-foreground">{field.help_text}</p>}
        </div>
    );
}

export function OptionEditor({ field, updateField }) {
    const options = asArray(field.options);
    const updateOption = (index, key, value) => {
        updateField({ options: updateFieldOption(options, field.field_type, index, key, value) });
    };
    const addOption = () => {
        updateField({ options: appendFieldOption(options, field.field_type) });
    };
    return (
        <div className="space-y-2" data-testid="field-options-editor">
            <div className="flex items-center justify-between"><Label>Auswahlmöglichkeiten</Label><Button type="button" variant="outline" size="sm" onClick={addOption}><Plus size={14} className="mr-1" /> Option</Button></div>
            {options.map((option, index) => (
                <div key={`${index}-${optionValue(option)}`} className="flex gap-2">
                    {field.field_type === 'decision' && (
                        <Input aria-label={`Wert Option ${index + 1}`} value={optionValue(option)} onChange={(event) => updateOption(index, 'value', event.target.value)} placeholder="Wert" />
                    )}
                    <Input aria-label={`Bezeichnung Option ${index + 1}`} value={optionLabel(option)} onChange={(event) => updateOption(index, 'label', event.target.value)} placeholder="Bezeichnung" />
                    <Button type="button" variant="ghost" size="sm" className="shrink-0 text-red-500" aria-label={`Option ${index + 1} löschen`} onClick={() => updateField({ options: removeFieldOption(options, index) })}><Trash size={16} /></Button>
                </div>
            ))}
        </div>
    );
}

export function FieldSettings({ field, onChange }) {
    if (!field) return <div className="flex min-h-64 items-center justify-center p-6 text-center text-sm text-muted-foreground">Wähle ein Feld in der Mitte aus, um seine Einstellungen zu bearbeiten.</div>;
    const update = (patch) => onChange({ ...field, ...patch });
    const isContent = CONTENT_FIELD_TYPES.has(field.field_type);
    return (
        <div className="space-y-4 p-4" data-testid="form-builder-settings">
            <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Feldeinstellungen</p>
                <h4 className="mt-1 inline-flex items-center gap-1.5 font-semibold text-foreground">{TYPE_LABELS[field.field_type] || field.field_type}<HelpTooltip content={FIELD_TYPE_HELP[field.field_type]} testId="builder-field-type-help" /></h4>
            </div>
            {!['divider'].includes(field.field_type) && (
                <div><Label><HelpLabel help={isContent ? 'Interne Bezeichnung zur Orientierung im Editor.' : 'Sichtbare Beschriftung des Felds in der Nutzeransicht.'}>{isContent ? 'Interner Titel' : 'Bezeichnung'}</HelpLabel></Label><Input className="mt-1" value={field.label || ''} onChange={(event) => update({ label: event.target.value })} data-testid="builder-field-label" /></div>
            )}
            {!isContent && (
                <>
                    <div><Label><HelpLabel help="Stabiler Schlüssel für gespeicherte Daten, Mappings und Conditions. Nach Produktivstart möglichst nicht umbenennen.">Technischer Feldname</HelpLabel></Label><Input className="mt-1 font-mono" value={field.name || ''} onChange={(event) => update({ name: slugify(event.target.value) })} data-testid="builder-field-name" /></div>
                    <div><Label><HelpLabel help="Optionaler erklärender Text, der Nutzern direkt unter dem Feld angezeigt wird.">Hilfetext</HelpLabel></Label><Input className="mt-1" value={field.help_text || ''} onChange={(event) => update({ help_text: event.target.value })} placeholder="Optionaler Hinweis unter dem Feld" /></div>
                    {!['checkbox', 'file', 'multiupload'].includes(field.field_type) && <div><Label><HelpLabel help="Beispiel oder Eingabehinweis im leeren Feld; wird nicht als Wert gespeichert.">Platzhalter</HelpLabel></Label><Input className="mt-1" value={field.placeholder || ''} onChange={(event) => update({ placeholder: event.target.value })} /></div>}
                    <div className="grid grid-cols-2 gap-3">
                        <div><Label>Breite</Label><Select value={field.width || 'full'} onValueChange={(width) => update({ width })}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="full">Ganze Zeile</SelectItem><SelectItem value="half">Halbe Zeile</SelectItem><SelectItem value="third">Drittel</SelectItem></SelectContent></Select></div>
                        <div className="flex items-end justify-between rounded border border-border px-3 pb-2.5"><Label>Pflichtfeld</Label><Switch checked={!!field.required} onCheckedChange={(required) => update({ required })} data-testid="builder-field-required" /></div>
                    </div>
                </>
            )}
            {(CHOICE_FIELD_TYPES.has(field.field_type) || field.field_type === 'multiupload') && <OptionEditor field={field} updateField={update} />}
            {field.field_type === 'textarea' && <div><Label>Sichtbare Zeilen</Label><Input className="mt-1" type="number" min="2" max="20" value={field.rows || 4} onChange={(event) => update({ rows: Number(event.target.value) })} /></div>}
            {['text', 'textarea'].includes(field.field_type) && <div className="grid grid-cols-2 gap-3"><div><Label>Min. Zeichen</Label><Input className="mt-1" type="number" min="0" value={field.min_length ?? ''} onChange={(event) => update({ min_length: event.target.value === '' ? null : Number(event.target.value) })} /></div><div><Label>Max. Zeichen</Label><Input className="mt-1" type="number" min="0" value={field.max_length ?? ''} onChange={(event) => update({ max_length: event.target.value === '' ? null : Number(event.target.value) })} /></div></div>}
            {field.field_type === 'number' && <div className="grid grid-cols-3 gap-2"><div><Label>Minimum</Label><Input className="mt-1" type="number" value={field.min ?? ''} onChange={(event) => update({ min: event.target.value === '' ? null : Number(event.target.value) })} /></div><div><Label>Maximum</Label><Input className="mt-1" type="number" value={field.max ?? ''} onChange={(event) => update({ max: event.target.value === '' ? null : Number(event.target.value) })} /></div><div><Label>Schritt</Label><Input className="mt-1" type="number" value={field.step ?? 1} onChange={(event) => update({ step: Number(event.target.value) })} /></div></div>}
            {['file', 'multiupload'].includes(field.field_type) && <div><Label>Erlaubte Dateitypen</Label><Input className="mt-1" value={field.accept || ''} onChange={(event) => update({ accept: event.target.value })} placeholder=".pdf,.png,.jpg" /><p className="mt-1 text-[11px] text-muted-foreground">Dateiendungen oder MIME-Typen, durch Komma getrennt.</p></div>}
            {field.field_type === 'file' && <div className="flex items-center justify-between rounded border border-border p-3"><Label>Mehrere Dateien</Label><Switch checked={!!field.multiple} onCheckedChange={(multiple) => update({ multiple })} /></div>}
            {['heading', 'paragraph', 'html'].includes(field.field_type) && <div><Label>{field.field_type === 'html' ? 'HTML-Inhalt' : 'Inhalt'}</Label><Textarea className="mt-1 min-h-32 font-mono" value={field.content || ''} onChange={(event) => update({ content: event.target.value })} data-testid="builder-field-content" /></div>}
            {field.field_type === 'heading' && <div><Label>Überschriftenebene</Label><Select value={String(field.heading_level || 2)} onValueChange={(value) => update({ heading_level: Number(value) })}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="2">H2</SelectItem><SelectItem value="3">H3</SelectItem><SelectItem value="4">H4</SelectItem></SelectContent></Select></div>}
            {field.field_type === 'image' && <><div><Label>Bild-URL</Label><Input className="mt-1" value={field.image_url || ''} onChange={(event) => update({ image_url: event.target.value })} placeholder="https://…" data-testid="builder-image-url" /></div><div><Label>Alternativtext</Label><Input className="mt-1" value={field.alt_text || ''} onChange={(event) => update({ alt_text: event.target.value })} /></div><div><Label>Bildunterschrift</Label><Input className="mt-1" value={field.caption || ''} onChange={(event) => update({ caption: event.target.value })} /></div></>}
        </div>
    );
}

export default function SurveyFormBuilder({ fields = [], onChange }) {
    const [selectedId, setSelectedId] = useState(fields[0]?.id || fields[0]?.name || null);
    const [search, setSearch] = useState('');
    useEffect(() => {
        if (!fields.length) setSelectedId(null);
        else if (!fields.some((field) => (field.id || field.name) === selectedId)) setSelectedId(fields[0].id || fields[0].name);
    }, [fields, selectedId]);
    const selectedIndex = fields.findIndex((field) => (field.id || field.name) === selectedId);
    const filteredGroups = useMemo(() => FIELD_GROUPS.map((group) => ({
        ...group,
        types: group.types.filter(([type, label]) => `${type} ${label}`.toLowerCase().includes(search.toLowerCase())),
    })).filter((group) => group.types.length), [search]);
    const addField = (type) => {
        const field = createField(type, fields.length);
        onChange([...fields, field]);
        setSelectedId(field.id);
    };
    const replaceAt = (index, field) => onChange(fields.map((item, itemIndex) => itemIndex === index ? field : item));
    const removeAt = (index) => onChange(fields.filter((_, itemIndex) => itemIndex !== index));
    const move = (index, direction) => onChange(moveField(fields, index, direction));
    const duplicate = (index) => {
        const result = duplicateField(fields, index);
        onChange(result.fields);
        setSelectedId(result.selectedId);
    };
    return (
        <div className="overflow-hidden rounded-xl border border-border bg-card" data-testid="survey-form-builder">
            <div className="border-b border-border px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-semibold text-foreground">Form Builder</h3><p className="text-xs text-muted-foreground">Felder hinzufügen, anordnen und direkt konfigurieren.</p></div><span className="rounded-full bg-muted px-3 py-1 text-xs font-medium">{fields.length} {fields.length === 1 ? 'Element' : 'Elemente'}</span></div>
            </div>
            <div className="grid min-h-[520px] lg:grid-cols-[210px_minmax(300px,1fr)_330px]">
                <aside className="border-b border-border bg-muted/25 p-3 lg:border-b-0 lg:border-r">
                    <Label className="text-xs">Elemente</Label>
                    <div className="relative mt-2"><MagnifyingGlass size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" /><Input className="h-9 pl-8" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Feldtyp suchen …" data-testid="form-builder-search" /></div>
                    <div className="mt-3 space-y-4">
                        {filteredGroups.map((group) => (
                            <div key={group.label}>
                                <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"><group.icon size={14} />{group.label}</div>
                                <div className="grid grid-cols-2 gap-1.5 lg:grid-cols-1">
                                    {group.types.map(([type, label]) => (
                                        <div key={type} className="flex items-center rounded-md border border-border bg-card pr-1 transition hover:border-[var(--brand-primary)]">
                                            <button type="button" onClick={() => addField(type)} className="flex min-w-0 flex-1 items-center justify-between px-2.5 py-2 text-left text-xs font-medium text-foreground hover:text-[var(--brand-primary)]" data-testid={`add-field-${type}`}><span>{label}</span><Plus size={13} /></button>
                                            <HelpTooltip content={FIELD_TYPE_HELP[type]} side="right" testId={`field-type-help-${type}`} />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </aside>
                <main className="border-b border-border bg-muted/10 p-4 lg:border-b-0 lg:border-r" data-testid="form-builder-canvas">
                    <div className="mb-3 flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Formular</p><p className="text-[11px] text-muted-foreground">Die Reihenfolge entspricht der späteren Ansicht.</p></div></div>
                    {!fields.length ? <div className="flex min-h-72 flex-col items-center justify-center rounded-lg border-2 border-dashed border-border bg-card p-8 text-center"><Plus size={28} className="mb-3 text-muted-foreground" /><p className="font-medium text-foreground">Noch keine Formularfelder</p><p className="mt-1 max-w-xs text-sm text-muted-foreground">Wähle links einen Feld- oder Inhaltstyp aus. Die Einstellungen erscheinen anschließend rechts.</p></div> : <div className="space-y-2">{fields.map((field, index) => { const id = field.id || field.name; const selected = id === selectedId; return <div key={`${id}-${index}`} role="button" tabIndex={0} onClick={() => setSelectedId(id)} onKeyDown={(event) => event.key === 'Enter' && setSelectedId(id)} className={`group rounded-lg border bg-card p-3 transition ${selected ? 'border-[var(--brand-primary)] ring-2 ring-[var(--brand-primary)]/15' : 'border-border hover:border-[var(--brand-primary)]/50'}`} data-testid={`builder-field-${index}`}><div className="mb-2 flex items-center justify-between gap-2"><div className="flex min-w-0 items-center gap-2"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-muted text-[11px] font-semibold text-muted-foreground">{index + 1}</span><span className="truncate text-xs font-medium text-muted-foreground">{TYPE_LABELS[field.field_type] || field.field_type}</span><span className="truncate font-mono text-[10px] text-muted-foreground">{field.name}</span></div><div className="flex shrink-0 opacity-70 transition group-hover:opacity-100"><Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0" disabled={index === 0} aria-label="Nach oben" onClick={(event) => { event.stopPropagation(); move(index, -1); }}><ArrowUp size={14} /></Button><Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0" disabled={index === fields.length - 1} aria-label="Nach unten" onClick={(event) => { event.stopPropagation(); move(index, 1); }}><ArrowDown size={14} /></Button><Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0" aria-label="Duplizieren" onClick={(event) => { event.stopPropagation(); duplicate(index); }}><Copy size={14} /></Button><Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-500" aria-label="Löschen" onClick={(event) => { event.stopPropagation(); removeAt(index); }}><Trash size={14} /></Button></div></div><FieldPreview field={field} /></div>; })}</div>}
                </main>
                <aside className="bg-card"><FieldSettings field={selectedIndex >= 0 ? fields[selectedIndex] : null} onChange={(field) => replaceAt(selectedIndex, field)} /></aside>
            </div>
        </div>
    );
}
