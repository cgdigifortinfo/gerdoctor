import { useState, useEffect,  useMemo } from 'react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';



import { Plus, Trash } from '@phosphor-icons/react';




// Stryker disable all: declarative CMS field adapter; persistence rules are tested in CMS commands.
export function LandingPagesSection({ content, onChange, translations, onTransChange, surveys, onSave, saving }) {
    const [selectedId, setSelectedId] = useState('');
    const [cmsLang, setCmsLang] = useState('de');
    const pages = useMemo(() => content?.pages || [], [content]);
    const selectedPage = pages.find(p => p.id === selectedId) || pages[0] || null;
    const activeId = selectedPage?.id || '';

    useEffect(() => {
        if (!selectedId && pages[0]?.id) setSelectedId(pages[0].id);
        if (selectedId && pages.length && !pages.some(p => p.id === selectedId)) {
            setSelectedId(pages[0].id);
        }
    }, [pages, selectedId]);

    const fields = [
        { key: 'title', label: 'Interner Name', type: 'text', placeholder: 'FSP Pflege' },
        { key: 'path', label: 'URL-Pfad', type: 'text', placeholder: '/pflege' },
        { key: 'survey_slug', label: 'Survey-Slug', type: 'text', placeholder: 'pflege' },
        { key: 'partner_tags', label: 'Partner-Tags', type: 'text', placeholder: 'Pflege Sprachschulung,Pflege Arbeitgeber' },
        { key: 'eyebrow', label: 'Hero Eyebrow', type: 'text', placeholder: 'Pflege in Deutschland' },
        { key: 'hero_title', label: 'Hero Titel', type: 'text', placeholder: 'Anerkennung als Pflegefachkraft in Deutschland' },
        { key: 'hero_subtitle', label: 'Hero Text', type: 'textarea', placeholder: 'Kurzbeschreibung der Landingpage' },
        { key: 'hero_cta', label: 'CTA Text', type: 'text', placeholder: 'Jetzt registrieren' },
        { key: 'learn_more_label', label: 'Sekundärbutton', type: 'text', placeholder: 'Mehr erfahren' },
        { key: 'hero_image_url', label: 'Hero Bild URL', type: 'text', placeholder: 'https://...' },
        { key: 'stat_value', label: 'Stat Wert', type: 'text', placeholder: '100%' },
        { key: 'stat_label', label: 'Stat Label', type: 'text', placeholder: 'Von der Anerkennung bis zum Pflegejob' },
        { key: 'box1_title', label: 'Feature 1 Titel', type: 'text', placeholder: 'Geführte Anerkennung' },
        { key: 'box1_description', label: 'Feature 1 Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'box2_title', label: 'Feature 2 Titel', type: 'text', placeholder: 'Partner-Netzwerk' },
        { key: 'box2_description', label: 'Feature 2 Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'box3_title', label: 'Feature 3 Titel', type: 'text', placeholder: 'Fortschritt' },
        { key: 'box3_description', label: 'Feature 3 Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'about_eyebrow', label: 'About Eyebrow', type: 'text', placeholder: 'Für internationale Pflegekräfte' },
        { key: 'about_title', label: 'About Titel', type: 'text', placeholder: 'Ihr Weg in Deutschland' },
        { key: 'about_description', label: 'About Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'about_mission', label: 'About Mission', type: 'textarea', placeholder: 'Mission' },
        { key: 'partners_eyebrow', label: 'Partner Eyebrow', type: 'text', placeholder: 'Partner & Vorbereitung' },
        { key: 'partners_title', label: 'Partner Titel', type: 'text', placeholder: 'Unterstützung' },
        { key: 'partners_description', label: 'Partner Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'cta_title', label: 'CTA Titel', type: 'text', placeholder: 'Bereit?' },
        { key: 'cta_description', label: 'CTA Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'footer_logo_url', label: 'Footer Logo URL', type: 'text', placeholder: 'https://...' },
        { key: 'footer_text', label: 'Footer Text', type: 'text', placeholder: '© 2026 ...' },
    ];

    const updatePages = (nextPages) => onChange({ ...(content || {}), pages: nextPages });
    const updatePage = (patch) => {
        updatePages(pages.map(page => page.id === selectedPage.id ? { ...page, ...patch } : page));
    };
    const updateTrans = (key, value) => {
        onTransChange(prev => ({
            ...prev,
            en: {
                ...(prev?.en || {}),
                [activeId]: {
                    ...(prev?.en?.[activeId] || {}),
                    [key]: value,
                },
            },
        }));
    };
    const addPage = () => {
        const id = `landing-${Date.now()}`;
        const next = {
            id,
            title: 'Neue Landingpage',
            path: '/neue-seite',
            survey_slug: surveys[0]?.slug || '',
            partner_tags: '',
            hero_title: 'Neue Landingpage',
            hero_cta: 'Jetzt starten',
        };
        updatePages([...pages, next]);
        setSelectedId(id);
    };
    const removePage = () => {
        const nextPages = pages.filter(page => page.id !== selectedPage.id);
        updatePages(nextPages);
        setSelectedId(nextPages[0]?.id || '');
    };

    return (
        <div className="bg-card border border-border rounded-sm">
            <div className="p-4 border-b border-border flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                <div>
                    <h3 className="font-semibold text-foreground">Landingpages</h3>
                    <p className="text-xs text-muted-foreground mt-1">Pflege hier mehrere öffentliche Seiten mit eigener URL und Survey-Verknüpfung.</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    <Select value={activeId} onValueChange={setSelectedId}>
                        <SelectTrigger className="w-56 border-border rounded-sm">
                            <SelectValue placeholder="Landingpage wählen" />
                        </SelectTrigger>
                        <SelectContent>
                            {pages.map(page => (
                                <SelectItem key={page.id} value={page.id}>{page.title || page.path} {page.path}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <div className="flex border border-border rounded-sm overflow-hidden">
                        <button type="button" onClick={() => setCmsLang('de')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'de' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>DE</button>
                        <button type="button" onClick={() => setCmsLang('en')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'en' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>EN</button>
                    </div>
                    <Button type="button" variant="outline" onClick={addPage} className="border-border rounded-sm">
                        <Plus size={16} className="mr-2" /> Neu
                    </Button>
                    <Button type="button" variant="outline" onClick={removePage} disabled={!selectedPage || selectedPage.path === '/'} className="border-border rounded-sm">
                        <Trash size={16} className="mr-2" /> Entfernen
                    </Button>
                    <Button onClick={onSave} disabled={saving} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="cms-save-landingpages">
                        {saving ? 'Saving...' : 'Save'}
                    </Button>
                </div>
            </div>
            {selectedPage ? (
                <div className="p-4 grid md:grid-cols-2 gap-4">
                    {fields.map((field) => {
                        const value = cmsLang === 'de'
                            ? selectedPage[field.key] || ''
                            : translations?.en?.[activeId]?.[field.key] || '';
                        const onFieldChange = (nextValue) => {
                            if (cmsLang === 'de') updatePage({ [field.key]: nextValue });
                            else updateTrans(field.key, nextValue);
                        };
                        return (
                            <div key={field.key} className={field.type === 'textarea' ? 'md:col-span-2' : ''}>
                                <Label className="text-foreground">{field.label} <span className="text-xs text-muted-foreground">({cmsLang.toUpperCase()})</span></Label>
                                {field.type === 'textarea' ? (
                                    <Textarea value={value} onChange={(e) => onFieldChange(e.target.value)} placeholder={cmsLang === 'en' ? selectedPage[field.key] || field.placeholder : field.placeholder} className="mt-1 border-border rounded-sm min-h-[80px]" />
                                ) : field.key === 'survey_slug' ? (
                                    <Select value={value || '__none'} onValueChange={(next) => onFieldChange(next === '__none' ? '' : next)}>
                                        <SelectTrigger className="mt-1 border-border rounded-sm">
                                            <SelectValue placeholder="Survey wählen" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none">Kein Survey</SelectItem>
                                            {surveys.map(survey => (
                                                <SelectItem key={survey.id} value={survey.slug}>{survey.name} /s/{survey.slug}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                ) : (
                                    <Input value={value} onChange={(e) => onFieldChange(e.target.value)} placeholder={cmsLang === 'en' ? selectedPage[field.key] || field.placeholder : field.placeholder} className="mt-1 border-border rounded-sm" />
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="p-8 text-center text-muted-foreground">
                    Noch keine Landingpages angelegt.
                </div>
            )}
        </div>
    );
}

export function CmsSection({ title, fields, content, onChange, translations, onTransChange, onSave, saving }) {
    const [cmsLang, setCmsLang] = useState('de');

    const setTrans = (lang, key, value) => {
        onTransChange(prev => ({ ...prev, [lang]: { ...(prev?.[lang] || {}), [key]: value } }));
    };

    return (
        <div className="bg-card border border-border rounded-sm">
            <div className="p-4 border-b border-border flex justify-between items-center">
                <h3 className="font-semibold text-foreground">{title}</h3>
                <div className="flex items-center gap-2">
                    <div className="flex border border-border rounded-sm overflow-hidden">
                        <button type="button" onClick={() => setCmsLang('de')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'de' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>DE</button>
                        <button type="button" onClick={() => setCmsLang('en')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'en' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>EN</button>
                    </div>
                    <Button onClick={onSave} disabled={saving} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid={`cms-save-${title.toLowerCase().replace(/\s+/g, '-')}`}>
                        {saving ? 'Saving...' : 'Save'}
                    </Button>
                </div>
            </div>
            <div className="p-4 space-y-4">
                {cmsLang === 'de' ? (
                    fields.map((field) => (
                        <div key={field.key}>
                            <Label className="text-foreground">{field.label} <span className="text-xs text-muted-foreground">(DE)</span></Label>
                            {field.type === 'textarea' ? (
                                <Textarea value={content[field.key] || ''} onChange={(e) => onChange({ ...content, [field.key]: e.target.value })} placeholder={field.placeholder} className="mt-1 border-border rounded-sm min-h-[80px]" data-testid={`cms-field-${field.key}`} />
                            ) : (
                                <Input value={content[field.key] || ''} onChange={(e) => onChange({ ...content, [field.key]: e.target.value })} placeholder={field.placeholder} className="mt-1 border-border rounded-sm" data-testid={`cms-field-${field.key}`} />
                            )}
                        </div>
                    ))
                ) : (
                    fields.map((field) => (
                        <div key={field.key}>
                            <Label className="text-foreground">{field.label} <span className="text-xs font-bold text-blue-600">EN</span></Label>
                            {field.type === 'textarea' ? (
                                <Textarea value={translations?.en?.[field.key] || ''} onChange={(e) => setTrans('en', field.key, e.target.value)} placeholder={content[field.key] || field.placeholder} className="mt-1 border-border rounded-sm min-h-[80px]" data-testid={`cms-field-en-${field.key}`} />
                            ) : (
                                <Input value={translations?.en?.[field.key] || ''} onChange={(e) => setTrans('en', field.key, e.target.value)} placeholder={content[field.key] || field.placeholder} className="mt-1 border-border rounded-sm" data-testid={`cms-field-en-${field.key}`} />
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
