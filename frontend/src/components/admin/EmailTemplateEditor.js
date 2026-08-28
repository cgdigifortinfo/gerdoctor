import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useLocation } from 'react-router-dom';
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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { adminAPI } from '../../lib/api';
import { toast } from 'sonner';
import { asArray } from '../../lib/valueNormalization';
import { buildPreviewVariables, copyTextSafely, invalidRecipients, parseRecipients, readCookie, renderLayoutPreview, writeCookie } from '../../features/admin/emailTemplateDomain';
import { Browser, DeviceMobile, EnvelopeSimple, FloppyDisk, ArrowClockwise, Eye, CopySimple, Code, PaperPlaneTilt } from '@phosphor-icons/react';

// Stryker disable all: declarative React adapter; all behavioral transformations live in emailTemplateDomain.
const COOKIE_NAME = 'email_tpl_test_recipients';

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


export function EmailTemplateEditor() {
    const location = useLocation();
    const [templates, setTemplates] = useState([]);
    const [variablesByCategory, setVariablesByCategory] = useState({});
    const [selectedKey, setSelectedKey] = useState('');
    const [subject, setSubject] = useState('');
    const [bodyHtml, setBodyHtml] = useState('');
    const [notificationTitle, setNotificationTitle] = useState('');
    const [notificationBody, setNotificationBody] = useState('');
    const [notificationPreview, setNotificationPreview] = useState({ title: '', body: '' });
    const [activeChannel, setActiveChannel] = useState('email');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [previewHtml, setPreviewHtml] = useState('');
    const [showSource, setShowSource] = useState(false);

    // User & Step pickers for live preview data
    const [allUsers, setAllUsers] = useState([]);
    const [allSteps, setAllSteps] = useState([]);
    const [previewUserId, setPreviewUserId] = useState('');
    const [previewStepId, setPreviewStepId] = useState('');

    // Test-email dialog state
    const [testDialogOpen, setTestDialogOpen] = useState(false);
    const [testRecipients, setTestRecipients] = useState('');
    const [testSending, setTestSending] = useState(false);

    const selected = useMemo(() => templates.find((t) => t.key === selectedKey), [templates, selectedKey]);
    const category = selected?.category || 'user';
    const availableVariables = variablesByCategory[category] || [];
    const requestedTemplate = useMemo(() => new URLSearchParams(location.search).get('template') || '', [location.search]);
    const requestedChannel = useMemo(() => new URLSearchParams(location.search).get('channel') || '', [location.search]);

    const loadTemplates = useCallback(async () => {
        setLoading(true);
        try {
            const res = await adminAPI.listEmailTemplates();
            setTemplates(res.data.templates || []);
            setVariablesByCategory(res.data.variables || {});
            setSelectedKey(current => {
                if (requestedTemplate && res.data.templates?.some(template => template.key === requestedTemplate)) {
                    return requestedTemplate;
                }
                return current || res.data.templates?.[0]?.key || '';
            });
        } catch (e) {
            toast.error('Vorlagen konnten nicht geladen werden');
        } finally {
            setLoading(false);
        }
    }, [requestedTemplate]);

    useEffect(() => { loadTemplates(); }, [loadTemplates]);

    useEffect(() => {
        if (requestedTemplate && templates.some(template => template.key === requestedTemplate)) {
            setSelectedKey(requestedTemplate);
        }
        if (requestedChannel === 'notification' || requestedChannel === 'email') {
            setActiveChannel(requestedChannel);
        }
    }, [requestedTemplate, requestedChannel, templates]);

    // Load reference lists (users, steps) once for the preview pickers
    useEffect(() => {
        (async () => {
            try {
                const [u, s] = await Promise.all([
                    adminAPI.getUsers(),
                    adminAPI.getSteps(),
                ]);
                setAllUsers(asArray(u.data).filter((x) => x.role === 'user'));
                setAllSteps([...asArray(s.data)].sort((a, b) => a.order - b.order));
            } catch (e) { /* non-fatal */ }
        })();
    }, []);

    // When the selected template changes, pull its current subject/body into the editor
    useEffect(() => {
        if (!selected) return;
        setSubject(selected.subject || '');
        setBodyHtml(selected.body_html || '');
        setNotificationTitle(selected.notification_title || '');
        setNotificationBody(selected.notification_body || '');
        if (selected.category === 'layout') setActiveChannel('email');
    }, [selected]);

    // Build the dummy variables used for the live preview, optionally augmented
    // with data from the picked user/step.
    const previewVariables = useMemo(
        () => buildPreviewVariables(allUsers, allSteps, previewUserId, previewStepId),
        [allUsers, allSteps, previewUserId, previewStepId],
    );

    // Debounced preview rendering (subject + body + header/footer)
    const previewTimer = useRef(null);
    const notificationPreviewTimer = useRef(null);
    useEffect(() => {
        if (!selectedKey || !selected) return;
        // Don't call the preview endpoint for layout blocks (header/footer) since
        // they render *within* every other email — instead just render them raw.
        if (category === 'layout') {
            setPreviewHtml(renderLayoutPreview(bodyHtml, previewVariables));
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

    useEffect(() => {
        if (!selectedKey || !selected || category === 'layout') return;
        clearTimeout(notificationPreviewTimer.current);
        notificationPreviewTimer.current = setTimeout(async () => {
            try {
                const response = await adminAPI.previewNotificationTemplate(selectedKey, {
                    title: notificationTitle,
                    body: notificationBody,
                    variables: previewVariables,
                });
                setNotificationPreview(response.data || { title: '', body: '' });
            } catch (e) {
                setNotificationPreview({ title: '', body: '' });
            }
        }, 250);
        return () => clearTimeout(notificationPreviewTimer.current);
    }, [selectedKey, selected, category, notificationTitle, notificationBody, previewVariables]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await adminAPI.updateEmailTemplate(selectedKey, {
                subject,
                body_html: bodyHtml,
                notification_title: notificationTitle,
                notification_body: notificationBody,
            });
            toast.success('Vorlage gespeichert');
            await loadTemplates();
        } catch (e) {
            toast.error('Speichern fehlgeschlagen');
        } finally { setSaving(false); }
    };

    const handleReset = async () => {
        if (!window.confirm('Vorlage auf Standardwerte zurücksetzen? Ihre Änderungen gehen verloren.')) return;
        setSaving(true);
        try {
            const res = await adminAPI.resetEmailTemplate(selectedKey);
            setSubject(res.data.subject || '');
            setBodyHtml(res.data.body_html || '');
            setNotificationTitle(res.data.notification_title || '');
            setNotificationBody(res.data.notification_body || '');
            toast.success('Vorlage zurückgesetzt');
            await loadTemplates();
        } catch (e) {
            toast.error('Zurücksetzen fehlgeschlagen');
        } finally { setSaving(false); }
    };

    const openTestDialog = () => {
        // Pre-fill from cookie so the admin doesn't have to re-type recipients
        setTestRecipients(readCookie(COOKIE_NAME));
        setTestDialogOpen(true);
    };

    const handleSendTest = async () => {
        // Persist the current textbox value in the cookie for next time
        writeCookie(COOKIE_NAME, testRecipients);
        // Split comma/semicolon/whitespace-separated list, strip, filter empties.
        const list = parseRecipients(testRecipients);
        const invalid = invalidRecipients(list);
        if (invalid.length) {
            toast.error(`Ungültige Adressen: ${invalid.join(', ')}`);
            return;
        }
        setTestSending(true);
        try {
            const res = await adminAPI.sendTestEmail(selectedKey, {
                subject, body_html: bodyHtml, variables: previewVariables,
                recipients: list,
            });
            const { sent, failed, skipped, recipients } = res.data || {};
            if (sent > 0) {
                toast.success(`Test-Mail an ${sent} Empfänger versendet: ${recipients.join(', ')}`);
            } else if (skipped > 0) {
                toast.warning('SMTP nicht konfiguriert — Mail wurde übersprungen (Preview-Umgebung).');
            } else if (failed?.length) {
                toast.error(`Versand fehlgeschlagen: ${failed.map((f) => f.email).join(', ')}`);
            }
            setTestDialogOpen(false);
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Versand fehlgeschlagen');
        } finally { setTestSending(false); }
    };

    const insertVariable = (v) => {
        const token = `{{${v}}}`;
        void copyTextSafely(navigator.clipboard, token);
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
        <div className="space-y-4" data-testid="email-template-editor">
            {/* Compact selector — replaces the old 300px sidebar so the editor
                 and preview get the full width. Templates grouped by category
                 via <SelectGroup>. */}
            <div className="bg-card border border-border rounded-lg p-3 flex flex-col sm:flex-row sm:items-center gap-3">
                <Label className="text-sm font-medium text-foreground shrink-0">Vorlage</Label>
                <Select value={selectedKey} onValueChange={setSelectedKey}>
                    <SelectTrigger className="flex-1" data-testid="email-template-select">
                        <SelectValue placeholder={loading ? 'Lade Vorlagen...' : 'Vorlage auswählen'} />
                    </SelectTrigger>
                    <SelectContent className="max-h-[70vh]">
                        {categoryOrder.map((cat) => (grouped[cat] || []).length > 0 && (
                            <div key={cat}>
                                <div className="px-2 py-1.5 text-[11px] uppercase tracking-wider text-muted-foreground bg-muted/50 sticky top-0">
                                    {CATEGORY_LABELS[cat]}
                                </div>
                                {grouped[cat].map((t) => (
                                    <SelectItem
                                        key={t.key}
                                        value={t.key}
                                        data-testid={`email-template-item-${t.key}`}
                                    >
                                        <span className="font-mono text-xs">{t.key}</span>
                                    </SelectItem>
                                ))}
                            </div>
                        ))}
                    </SelectContent>
                </Select>
                {selected && (
                    <Badge variant="outline" className={`${CATEGORY_COLOR[category]} shrink-0`}>
                        {CATEGORY_LABELS[category]}
                    </Badge>
                )}
            </div>

            {/* Editor + Preview */}
            <div className="space-y-4">
                {!selected ? (
                    <div className="bg-card border border-border rounded-lg p-8 text-center text-muted-foreground">
                        {loading ? 'Lade Vorlagen...' : 'Wählen Sie oben eine Vorlage aus.'}
                    </div>
                ) : (
                    <>
                        <div className="bg-card border border-border rounded-lg p-4">
                            <div className="flex items-start justify-between gap-3 mb-3">
                                <p className="text-sm text-muted-foreground flex-1">{selected.description}</p>
                                <div className="flex gap-2 shrink-0">
                                    {activeChannel === 'email' && (
                                        <Button variant="outline" size="sm" onClick={openTestDialog} disabled={saving} data-testid="email-template-test-btn">
                                            <PaperPlaneTilt size={14} className="mr-1" /> Test-Mail senden
                                        </Button>
                                    )}
                                    <Button variant="outline" size="sm" onClick={handleReset} disabled={saving} data-testid="email-template-reset-btn">
                                        <ArrowClockwise size={14} className="mr-1" /> Zurücksetzen
                                    </Button>
                                    <Button onClick={handleSave} disabled={saving} size="sm" className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)]" data-testid="email-template-save-btn">
                                        <FloppyDisk size={14} className="mr-1" /> Speichern
                                    </Button>
                                </div>
                            </div>

                            {category !== 'layout' && (
                                <div className="mb-5 inline-flex overflow-hidden rounded-sm border border-border" data-testid="message-channel-toggle">
                                    <button
                                        type="button"
                                        onClick={() => setActiveChannel('email')}
                                        className={`flex items-center gap-2 px-4 py-2 text-sm ${activeChannel === 'email' ? 'bg-[var(--brand-primary)] text-white' : 'bg-card text-muted-foreground'}`}
                                        data-testid="message-channel-email"
                                    >
                                        <EnvelopeSimple size={16} /> E-Mail
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setActiveChannel('notification')}
                                        className={`flex items-center gap-2 border-l border-border px-4 py-2 text-sm ${activeChannel === 'notification' ? 'bg-[var(--brand-primary)] text-white' : 'bg-card text-muted-foreground'}`}
                                        data-testid="message-channel-notification"
                                    >
                                        <DeviceMobile size={16} /> Browser & App
                                    </button>
                                </div>
                            )}

                            {(category === 'layout' || activeChannel === 'email') ? (
                                <div data-testid="email-message-editor">
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
                                    <div>
                                        <div className="flex items-center justify-between mb-1">
                                            <Label>{category === 'layout' ? 'HTML-Block' : 'E-Mail-Nachricht'}</Label>
                                            <button
                                                type="button"
                                                onClick={() => setShowSource((s) => !s)}
                                                className="text-xs text-[var(--brand-primary)] hover:underline flex items-center gap-1"
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
                                </div>
                            ) : (
                                <div className="space-y-4" data-testid="notification-message-editor">
                                    <div>
                                        <Label>Notification-Titel</Label>
                                        <Input
                                            value={notificationTitle}
                                            onChange={(event) => setNotificationTitle(event.target.value)}
                                            placeholder="Kurzer Titel für Browser und App"
                                            maxLength={120}
                                            data-testid="notification-title-input"
                                        />
                                        <p className="mt-1 text-right text-[11px] text-muted-foreground">{notificationTitle.length}/120</p>
                                    </div>
                                    <div>
                                        <Label>Notification-Text</Label>
                                        <Textarea
                                            value={notificationBody}
                                            onChange={(event) => setNotificationBody(event.target.value)}
                                            placeholder="Kompakte Nachricht für Push-Notifications"
                                            maxLength={320}
                                            rows={5}
                                            data-testid="notification-body-input"
                                        />
                                        <p className="mt-1 text-right text-[11px] text-muted-foreground">{notificationBody.length}/320</p>
                                    </div>
                                    <div className="rounded-sm border border-dashed border-border bg-muted/30 p-3 text-xs text-muted-foreground">
                                        Die Inhalte sind providerneutral gespeichert. Event-Handler legen daraus Outbox-Einträge für Browser und/oder App an; konkrete Push-Provider werden später angebunden.
                                    </div>
                                </div>
                            )}

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
                                                className="text-xs bg-muted hover:bg-[var(--brand-primary)] hover:text-white border border-border px-2 py-0.5 rounded font-mono transition-colors inline-flex items-center gap-1"
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
                                    <Eye size={16} className="text-[var(--brand-primary)]" />
                                    <h3 className="font-semibold text-foreground">
                                        {activeChannel === 'notification' && category !== 'layout' ? 'Notification-Vorschau' : 'E-Mail-Vorschau'}
                                    </h3>
                                    {category !== 'layout' && activeChannel === 'email' && (
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

                            {(category === 'layout' || activeChannel === 'email') ? (
                                <>
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
                                </>
                            ) : (
                                <div className="grid gap-6 lg:grid-cols-2" data-testid="notification-preview">
                                    <section data-testid="notification-browser-preview">
                                        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                                            <Browser size={17} className="text-[var(--brand-primary)]" /> Browser
                                        </div>
                                        <div className="rounded-lg bg-slate-100 p-4 sm:p-6">
                                            <div className="ml-auto max-w-sm rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
                                                <div className="mb-3 flex items-center gap-2">
                                                    <div className="grid h-8 w-8 place-items-center rounded-full bg-[var(--brand-primary)] text-xs font-bold text-white">G</div>
                                                    <div>
                                                        <p className="text-xs font-semibold text-slate-900">GerDoctor</p>
                                                        <p className="text-[10px] text-slate-500">ihca.de · jetzt</p>
                                                    </div>
                                                </div>
                                                <p className="text-sm font-semibold text-slate-950" data-testid="notification-preview-title">
                                                    {notificationPreview.title || 'Notification-Titel'}
                                                </p>
                                                <p className="mt-1 whitespace-pre-wrap text-sm leading-5 text-slate-700" data-testid="notification-preview-body">
                                                    {notificationPreview.body || 'Notification-Text'}
                                                </p>
                                            </div>
                                        </div>
                                    </section>

                                    <section data-testid="notification-app-preview">
                                        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                                            <DeviceMobile size={17} className="text-[var(--brand-primary)]" /> App
                                        </div>
                                        <div className="mx-auto max-w-[330px] rounded-[2rem] border-[6px] border-slate-800 bg-slate-50 p-3 shadow-lg">
                                            <div className="mb-3 flex items-center justify-between px-2 text-[10px] font-semibold text-slate-700">
                                                <span>09:41</span><span>● ● ●</span>
                                            </div>
                                            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                                                <div className="flex items-start gap-3">
                                                    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--brand-primary)] text-sm font-bold text-white">G</div>
                                                    <div className="min-w-0">
                                                        <div className="flex items-center justify-between gap-3">
                                                            <p className="text-xs font-semibold text-slate-950">GerDoctor</p>
                                                            <span className="text-[10px] text-slate-500">jetzt</span>
                                                        </div>
                                                        <p className="mt-1 text-sm font-semibold text-slate-950">
                                                            {notificationPreview.title || 'Notification-Titel'}
                                                        </p>
                                                        <p className="mt-1 whitespace-pre-wrap text-xs leading-4 text-slate-700">
                                                            {notificationPreview.body || 'Notification-Text'}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="h-24" />
                                            <div className="mx-auto h-1 w-24 rounded-full bg-slate-800" />
                                        </div>
                                    </section>
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>

            {/* Test-Mail Dialog */}
            <Dialog open={testDialogOpen} onOpenChange={setTestDialogOpen}>
                <DialogContent data-testid="email-test-dialog">
                    <DialogHeader>
                        <DialogTitle>Test-Mail senden</DialogTitle>
                        <DialogDescription>
                            Die aktuelle Vorlage wird an deine eigene E-Mail-Adresse und
                            optional an weitere Empfänger verschickt — inklusive aller
                            ungespeicherten Änderungen (Subject + Body).
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label htmlFor="test-recipients-input">
                                Weitere Empfänger <span className="text-xs text-muted-foreground">(Komma-getrennt, optional)</span>
                            </Label>
                            <Textarea
                                id="test-recipients-input"
                                data-testid="email-test-recipients-input"
                                value={testRecipients}
                                onChange={(e) => setTestRecipients(e.target.value)}
                                placeholder="qa@chrizz1001.de, test@chrizz1001.de"
                                rows={3}
                                className="font-mono text-sm"
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                                Deine Eingabe wird in einem Cookie gespeichert und beim nächsten Öffnen automatisch vorausgefüllt.
                            </p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setTestDialogOpen(false)} disabled={testSending} data-testid="email-test-cancel-btn">
                            Abbrechen
                        </Button>
                        <Button onClick={handleSendTest} disabled={testSending} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)]" data-testid="email-test-send-btn">
                            <PaperPlaneTilt size={14} className="mr-1" />
                            {testSending ? 'Sende…' : 'Jetzt senden'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

export default EmailTemplateEditor;
