import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    EditorProvider,
    Editor, Toolbar, BtnBold, BtnItalic, BtnUnderline, BtnLink,
    BtnBulletList, BtnNumberedList, BtnClearFormatting, BtnStyles, Separator,
} from 'react-simple-wysiwyg';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { adminAPI } from '../../lib/api';
import { toast } from 'sonner';
import { FloppyDisk, ArrowClockwise, Eye, CopySimple, Code } from '@phosphor-icons/react';

const CATEGORY_LABELS = {
    layout: 'Layout (Header & Footer)',
    partner: 'Partner-Benachrichtigungen',
    user: 'User-Benachrichtigungen',
    step: 'Step-Benachrichtigungen',
};

const CATEGORY_COLOR = {
    layout: 'bg-slate-100 text-slate-700 border-slate-300',
    partner: 'bg-amber-100 text-amber-800 border-amber-300',
    user: 'bg-sky-100 text-sky-800 border-sky-300',
    step: 'bg-emerald-100 text-emerald-800 border-emerald-300',
};

// Sensible dummy fallbacks shown in the preview when no real user/step is picked
const DEFAULT_DUMMY = {
    user_name: 'Dr. Maria Mustermann',
    user_email: 'dr.mustermann@gerdoctor.de',
    partner_name: 'ILS Berlin',
    field_of_study: 'Innere Medizin',
    bundesland: 'Berlin',
    step_order: 4,
    step_title: 'Dokumente Antragstellung Approbation',
    step_description: 'Laden Sie die benötigten Nachweise für die Approbation hoch.',
    total_steps: 24,
    milestone_title: 'Antragstellung Approbation',
    open_user_link: 'https://gerdoctor.de/partner-dashboard?openUser=DEMO-USER-ID',
    reset_link: 'https://gerdoctor.de/reset-password?token=DEMO-TOKEN',
    app_url: 'https://gerdoctor.de',
};

export function EmailTemplateEditor() {
    const [templates, setTemplates] = useState([]);
    const [variablesByCategory, setVariablesByCategory] = useState({});
    const [selectedKey, setSelectedKey] = useState('');
    const [subject, setSubject] = useState('');
    const [bodyHtml, setBodyHtml] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [previewHtml, setPreviewHtml] = useState('');
    const [showSource, setShowSource] = useState(false);

    // User & Step pickers for live preview data
    const [allUsers, setAllUsers] = useState([]);
    const [allSteps, setAllSteps] = useState([]);
    const [previewUserId, setPreviewUserId] = useState('');
    const [previewStepId, setPreviewStepId] = useState('');

    const selected = useMemo(() => templates.find((t) => t.key === selectedKey), [templates, selectedKey]);
    const category = selected?.category || 'user';
    const availableVariables = variablesByCategory[category] || [];

    const loadTemplates = useCallback(async () => {
        setLoading(true);
        try {
            const res = await adminAPI.listEmailTemplates();
            setTemplates(res.data.templates || []);
            setVariablesByCategory(res.data.variables || {});
            if (!selectedKey && res.data.templates?.length) {
                setSelectedKey(res.data.templates[0].key);
            }
        } catch (e) {
            toast.error('Vorlagen konnten nicht geladen werden');
        } finally {
            setLoading(false);
        }
    }, [selectedKey]);

    useEffect(() => { loadTemplates(); }, [loadTemplates]);

    // Load reference lists (users, steps) once for the preview pickers
    useEffect(() => {
        (async () => {
            try {
                const [u, s] = await Promise.all([
                    adminAPI.getUsers(),
                    adminAPI.getSteps(),
                ]);
                setAllUsers((u.data || []).filter((x) => x.role === 'user'));
                setAllSteps((s.data || []).sort((a, b) => a.order - b.order));
            } catch (e) { /* non-fatal */ }
        })();
    }, []);

    // When the selected template changes, pull its current subject/body into the editor
    useEffect(() => {
        if (!selected) return;
        setSubject(selected.subject || '');
        setBodyHtml(selected.body_html || '');
    }, [selected]);

    // Build the dummy variables used for the live preview, optionally augmented
    // with data from the picked user/step.
    const previewVariables = useMemo(() => {
        const vars = { ...DEFAULT_DUMMY };
        const u = allUsers.find((x) => x.id === previewUserId);
        if (u) {
            vars.user_name = u.name || u.email;
            vars.user_email = u.email;
            const partnerName = u.selected_partner_names?.[0] || u.partner_name || vars.partner_name;
            if (partnerName) vars.partner_name = partnerName;
            vars.open_user_link = `${window.location.origin}/partner-dashboard?openUser=${u.id}`;
        }
        const s = allSteps.find((x) => x.id === previewStepId);
        if (s) {
            vars.step_title = s.title;
            vars.step_order = s.order;
            vars.step_description = s.description || '';
        }
        return vars;
    }, [allUsers, allSteps, previewUserId, previewStepId]);

    // Debounced preview rendering (subject + body + header/footer)
    const previewTimer = useRef(null);
    useEffect(() => {
        if (!selectedKey || !selected) return;
        // Don't call the preview endpoint for layout blocks (header/footer) since
        // they render *within* every other email — instead just render them raw.
        if (category === 'layout') {
            const replaced = (bodyHtml || '').replace(/{{\s*([\w.]+)\s*}}/g, (_, k) =>
                previewVariables[k] != null ? String(previewVariables[k]) : ''
            );
            setPreviewHtml(`<div style="padding:16px;background:#f8fafc;">${replaced}</div>`);
            return;
        }
        clearTimeout(previewTimer.current);
        previewTimer.current = setTimeout(async () => {
            try {
                const res = await adminAPI.previewEmailTemplate(selectedKey, {
                    subject, body_html: bodyHtml, variables: previewVariables,
                });
                setPreviewHtml(res.data.html || '');
            } catch (e) { /* silent */ }
        }, 300);
        return () => clearTimeout(previewTimer.current);
    }, [selectedKey, selected, category, subject, bodyHtml, previewVariables]);

    const handleSave = async () => {
        if (!selectedKey) return;
        setSaving(true);
        try {
            await adminAPI.updateEmailTemplate(selectedKey, { subject, body_html: bodyHtml });
            toast.success('Vorlage gespeichert');
            await loadTemplates();
        } catch (e) {
            toast.error('Speichern fehlgeschlagen');
        } finally { setSaving(false); }
    };

    const handleReset = async () => {
        if (!selectedKey) return;
        if (!window.confirm('Vorlage auf Standardwerte zurücksetzen? Ihre Änderungen gehen verloren.')) return;
        setSaving(true);
        try {
            const res = await adminAPI.resetEmailTemplate(selectedKey);
            setSubject(res.data.subject || '');
            setBodyHtml(res.data.body_html || '');
            toast.success('Vorlage zurückgesetzt');
            await loadTemplates();
        } catch (e) {
            toast.error('Zurücksetzen fehlgeschlagen');
        } finally { setSaving(false); }
    };

    const insertVariable = (v) => {
        const token = `{{${v}}}`;
        // navigator.clipboard can reject in insecure/headless contexts; swallow the
        // rejection so it doesn't surface as a React error overlay that blocks
        // interaction elsewhere in the editor.
        try {
            const p = navigator.clipboard?.writeText(token);
            if (p && typeof p.catch === 'function') p.catch(() => {});
        } catch (_e) { /* clipboard unavailable — silently ignore */ }
        toast.success(`${token} in die Zwischenablage kopiert`);
    };

    // Group templates by category for the sidebar
    const grouped = useMemo(() => {
        const g = {};
        templates.forEach((t) => { (g[t.category] = g[t.category] || []).push(t); });
        return g;
    }, [templates]);

    const categoryOrder = ['layout', 'partner', 'user', 'step'];

    return (
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6" data-testid="email-template-editor">
            {/* Sidebar — template list grouped by category */}
            <aside className="bg-card border border-border rounded-lg p-3 h-fit sticky top-4">
                <h3 className="text-sm font-semibold text-foreground mb-3 px-1">E-Mail-Vorlagen</h3>
                {categoryOrder.map((cat) => (grouped[cat] || []).length > 0 && (
                    <div key={cat} className="mb-4">
                        <div className="text-[11px] uppercase tracking-wider text-muted-foreground px-1 mb-1.5">
                            {CATEGORY_LABELS[cat]}
                        </div>
                        <div className="space-y-0.5">
                            {grouped[cat].map((t) => (
                                <button
                                    key={t.key}
                                    onClick={() => setSelectedKey(t.key)}
                                    data-testid={`email-template-item-${t.key}`}
                                    className={`w-full text-left px-2 py-1.5 rounded text-sm transition-colors ${
                                        t.key === selectedKey
                                            ? 'bg-[#114f55] text-white'
                                            : 'hover:bg-muted text-foreground'
                                    }`}
                                >
                                    {t.key}
                                </button>
                            ))}
                        </div>
                    </div>
                ))}
            </aside>

            {/* Editor + Preview split */}
            <div className="space-y-4">
                {!selected ? (
                    <div className="bg-card border border-border rounded-lg p-8 text-center text-muted-foreground">
                        {loading ? 'Lade Vorlagen...' : 'Wählen Sie links eine Vorlage aus.'}
                    </div>
                ) : (
                    <>
                        <div className="bg-card border border-border rounded-lg p-4">
                            <div className="flex items-center justify-between mb-3">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-lg font-semibold text-foreground">{selected.key}</h3>
                                        <Badge variant="outline" className={CATEGORY_COLOR[category]}>{CATEGORY_LABELS[category]}</Badge>
                                    </div>
                                    <p className="text-sm text-muted-foreground mt-1">{selected.description}</p>
                                </div>
                                <div className="flex gap-2">
                                    <Button variant="outline" size="sm" onClick={handleReset} disabled={saving} data-testid="email-template-reset-btn">
                                        <ArrowClockwise size={14} className="mr-1" /> Zurücksetzen
                                    </Button>
                                    <Button onClick={handleSave} disabled={saving} className="bg-[#114f55] hover:bg-[#0e4248]" data-testid="email-template-save-btn">
                                        <FloppyDisk size={14} className="mr-1" /> Speichern
                                    </Button>
                                </div>
                            </div>

                            {/* Subject (hidden for layout blocks) */}
                            {category !== 'layout' && (
                                <div className="mb-3">
                                    <Label>Betreff</Label>
                                    <Input
                                        value={subject}
                                        onChange={(e) => setSubject(e.target.value)}
                                        placeholder="E-Mail-Betreff"
                                        data-testid="email-template-subject-input"
                                    />
                                </div>
                            )}

                            {/* WYSIWYG or raw HTML textarea */}
                            <div>
                                <div className="flex items-center justify-between mb-1">
                                    <Label>{category === 'layout' ? 'HTML-Block' : 'Nachricht'}</Label>
                                    <button
                                        type="button"
                                        onClick={() => setShowSource((s) => !s)}
                                        className="text-xs text-[#114f55] hover:underline flex items-center gap-1"
                                        data-testid="email-template-toggle-source"
                                    >
                                        <Code size={12} /> {showSource ? 'WYSIWYG' : 'HTML-Code'}
                                    </button>
                                </div>
                                {showSource || category === 'layout' ? (
                                    <Textarea
                                        value={bodyHtml}
                                        onChange={(e) => setBodyHtml(e.target.value)}
                                        rows={category === 'layout' ? 10 : 16}
                                        className="font-mono text-xs"
                                        data-testid="email-template-body-textarea"
                                    />
                                ) : (
                                    <div className="border border-border rounded bg-white" data-testid="email-template-wysiwyg">
                                        <EditorProvider>
                                            <Editor value={bodyHtml} onChange={(e) => setBodyHtml(e.target.value)} style={{ minHeight: 300 }}>
                                                <Toolbar>
                                                    <BtnBold /> <BtnItalic /> <BtnUnderline />
                                                    <Separator />
                                                    <BtnBulletList /> <BtnNumberedList />
                                                    <Separator />
                                                    <BtnLink />
                                                    <BtnClearFormatting />
                                                    <Separator />
                                                    <BtnStyles />
                                                </Toolbar>
                                            </Editor>
                                        </EditorProvider>
                                    </div>
                                )}
                            </div>

                            {/* Variable chips */}
                            {availableVariables.length > 0 && (
                                <div className="mt-3">
                                    <Label className="text-xs text-muted-foreground">Verfügbare Variablen (Klick = in Zwischenablage)</Label>
                                    <div className="flex flex-wrap gap-1 mt-1">
                                        {availableVariables.map((v) => (
                                            <button
                                                key={v}
                                                type="button"
                                                onClick={() => insertVariable(v)}
                                                data-testid={`email-template-var-${v}`}
                                                className="text-xs bg-muted hover:bg-[#114f55] hover:text-white border border-border px-2 py-0.5 rounded font-mono transition-colors inline-flex items-center gap-1"
                                            >
                                                <CopySimple size={10} /> {`{{${v}}}`}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Preview panel */}
                        <div className="bg-card border border-border rounded-lg p-4" data-testid="email-template-preview">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <Eye size={16} className="text-[#114f55]" />
                                    <h3 className="font-semibold text-foreground">Live-Vorschau</h3>
                                    {category !== 'layout' && (
                                        <span className="text-xs text-muted-foreground">(Header + Body + Footer)</span>
                                    )}
                                </div>
                            </div>

                            {/* Preview context pickers — user & step */}
                            {category !== 'layout' && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                                    <div>
                                        <Label className="text-xs">Vorschau-User</Label>
                                        <Select value={previewUserId || 'default'} onValueChange={(v) => setPreviewUserId(v === 'default' ? '' : v)}>
                                            <SelectTrigger data-testid="email-preview-user-select"><SelectValue placeholder="Dummy-User" /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="default">Dummy-User (Dr. Maria Mustermann)</SelectItem>
                                                {allUsers.slice(0, 50).map((u) => (
                                                    <SelectItem key={u.id} value={u.id}>{u.name || u.email}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <Label className="text-xs">Vorschau-Step</Label>
                                        <Select value={previewStepId || 'default'} onValueChange={(v) => setPreviewStepId(v === 'default' ? '' : v)}>
                                            <SelectTrigger data-testid="email-preview-step-select"><SelectValue placeholder="Dummy-Step" /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="default">Dummy-Step (#4 Dokumente)</SelectItem>
                                                {allSteps.map((s) => (
                                                    <SelectItem key={s.id} value={s.id}>#{s.order} — {s.title}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            )}

                            {category !== 'layout' && (
                                <div className="mb-3 bg-slate-50 dark:bg-slate-900/40 border border-border rounded px-3 py-2">
                                    <span className="text-xs text-muted-foreground uppercase tracking-wider">Betreff:</span>
                                    <div className="text-sm font-medium text-foreground" data-testid="email-preview-subject">
                                        {(subject || '').replace(/{{\s*([\w.]+)\s*}}/g, (_, k) => previewVariables[k] != null ? String(previewVariables[k]) : '')}
                                    </div>
                                </div>
                            )}
                            <iframe
                                title="Email Preview"
                                srcDoc={previewHtml}
                                className="w-full rounded border border-border bg-white"
                                style={{ minHeight: 560 }}
                                data-testid="email-preview-iframe"
                            />
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

export default EmailTemplateEditor;
