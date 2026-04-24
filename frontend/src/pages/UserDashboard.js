import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { stepsAPI, partnersAPI, filesAPI, notificationAPI, settingsAPI, formatApiError } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { Switch } from '../components/ui/switch';
import {
    SignOut, Check, ArrowRight, ArrowLeft, CloudArrowUp, X, CaretRight, CaretDown,
    Bell, GearSix, Plus, Trash, WarningCircle, CheckCircle, SkipForward, Lock,
    ClockCounterClockwise, CalendarCheck, UserSwitch
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { Logo } from '../components/Logo';
import { JourneyProgressIndicator } from '../components/JourneyProgressIndicator';

// Evaluate a single condition against all step data
function evaluateCondition(cond, allStepData) {
    const sourceStep = allStepData.find(s => s.order === cond.source_step_order);
    if (!sourceStep) return false;
    const fieldValue = sourceStep.data?.[cond.field] ?? sourceStep.status;
    const expected = cond.value;
    switch (cond.operator) {
        case 'equals': return String(fieldValue) === String(expected);
        case 'not_equals': return String(fieldValue) !== String(expected);
        case 'contains': return String(fieldValue).includes(String(expected));
        case 'not_empty': return !!fieldValue && fieldValue !== '';
        case 'empty': return !fieldValue || fieldValue === '';
        case 'status_is': return sourceStep.status === expected;
        case 'status_not': return sourceStep.status !== expected;
        case 'has_upload': {
            const uploads = sourceStep.data?.[cond.field] || [];
            return Array.isArray(uploads) && uploads.some(u => u.document_type === expected && u.file_id);
        }
        case 'missing_upload': {
            const uploads = sourceStep.data?.[cond.field] || [];
            return !Array.isArray(uploads) || !uploads.some(u => u.document_type === expected && u.file_id);
        }
        default: return false;
    }
}

function evaluateStepConditions(step, allStepData) {
    const conditions = step.conditions || [];
    if (conditions.length === 0) return { allowed: true, blocked: false, hidden: false, message: '', redirectStep: null };
    let result = { allowed: true, blocked: false, hidden: false, message: '', redirectStep: null };
    for (const cond of conditions) {
        const matches = evaluateCondition(cond, allStepData);
        if (matches) {
            if (cond.action === 'block') { result.allowed = false; result.blocked = true; result.message = cond.message || 'Dieser Schritt ist gesperrt.'; }
            else if (cond.action === 'hide') { result.hidden = true; }
            else if (cond.action === 'allow_next') { result.allowed = true; result.message = cond.message || ''; }
            else if (cond.action === 'redirect') { result.redirectStep = cond.target_step_order; }
            // auto_complete is handled server-side; here we just note it
        }
    }
    return result;
}

function isStepHidden(step, allStepData) {
    return evaluateStepConditions(step, allStepData).hidden;
}

function applyFieldMappings(step, allStepData) {
    const mappings = step.field_mappings || [];
    const prefilled = {};
    for (const m of mappings) {
        const sourceStep = allStepData.find(s => s.order === m.source_step_order);
        if (sourceStep?.data?.[m.source_field] !== undefined) {
            prefilled[m.target_field] = sourceStep.data[m.source_field];
        }
    }
    return prefilled;
}

// Score a partner against the user's Step-1 profile (Fachrichtung + Bundesland).
// >0 = recommended. Partners are sorted recommended-first + by score desc.
function scorePartner(partner, profile) {
    if (!profile) return 0;
    const fach = profile.fachrichtung_gewuenscht || profile.fachrichtung_praktiziert || profile.field_of_study;
    const bl = profile.anerkennungsverfahren_bundesland;
    const tags = partner.tags || [];
    let score = 0;
    if (fach) {
        if (partner.category === fach) score += 10;
        if (tags.includes(fach)) score += 10;
    }
    if (bl && tags.includes(bl)) score += 5;
    return score;
}

function sortPartnersByRecommendation(partners, profile) {
    return [...partners]
        .map(p => ({ ...p, _score: scorePartner(p, profile) }))
        .sort((a, b) => {
            if (b._score !== a._score) return b._score - a._score;
            return (a.name || '').localeCompare(b.name || '');
        });
}

export default function UserDashboard() {
    const { user, logout, impersonating, stopImpersonation } = useAuth();
    const { t, localize, lang } = useLanguage();
    const loc = (step, field) => localize(step, field);
    const navigate = useNavigate();
    const [steps, setSteps] = useState([]);
    const [progress, setProgress] = useState([]);
    const [allStepData, setAllStepData] = useState([]);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [partners, setPartners] = useState([]);
    const [selectedPartner, setSelectedPartner] = useState(null);
    const [selectedPartners, setSelectedPartners] = useState([]);
    const [partnerTagFilter, setPartnerTagFilter] = useState('all');
    const [formData, setFormData] = useState({});
    const [uploadedFiles, setUploadedFiles] = useState({});
    const [submitting, setSubmitting] = useState(false);
    const [validationErrors, setValidationErrors] = useState([]);
    const [showSettings, setShowSettings] = useState(false);
    const [showTimeline, setShowTimeline] = useState(false);
    const [history, setHistory] = useState([]);
    const [notifPrefs, setNotifPrefs] = useState({ email_on_step_enter: true, email_on_step_edit: false, email_on_step_leave: true });
    const [animateProgress, setAnimateProgress] = useState(false);
    const [expandedStep, setExpandedStep] = useState(null);
    const [estimatedCompletion, setEstimatedCompletion] = useState(null);
    // UI feature flags from site settings (admin-controlled). Defaults to true
    // so the app works unchanged if the settings have never been saved.
    const [uiFlags, setUiFlags] = useState({
        ui_show_journey_indicator: true,
        ui_show_eta_header: true,
        ui_show_progress_percentage: true,
    });
    const stepRefs = useRef({});
    const containerRef = useRef(null);
    const desktopStepRefs = useRef({});

    // Visible steps = all active steps except those whose hide-condition matches.
    // Memoised so its reference is stable and doesn't trigger effect loops.
    const visibleSteps = useMemo(
        () => steps.filter(s => !isStepHidden(s, allStepData)),
        [steps, allStepData]
    );

    const loadData = useCallback(async () => {
        try {
            const [stepsRes, progressRes, allDataRes, notifRes, historyRes, estRes, settingsRes] = await Promise.all([
                stepsAPI.getAll(), stepsAPI.getProgress(), stepsAPI.getAllData(),
                notificationAPI.getPreferences().catch(() => ({ data: { email_on_step_enter: true, email_on_step_edit: false, email_on_step_leave: true } })),
                stepsAPI.getHistory().catch(() => ({ data: [] })),
                stepsAPI.getEstimatedCompletion().catch(() => ({ data: { estimated_completion: null } })),
                settingsAPI.get().catch(() => ({ data: {} })),
            ]);
            setSteps(stepsRes.data);
            setProgress(progressRes.data);
            setAllStepData(allDataRes.data);
            setNotifPrefs(notifRes.data);
            setHistory(historyRes.data);
            setEstimatedCompletion(estRes.data?.estimated_completion || null);
            // UI feature-flags — only explicit `false` disables; unset/null keeps default ON
            const s = settingsRes.data || {};
            setUiFlags({
                ui_show_journey_indicator: s.ui_show_journey_indicator !== false,
                ui_show_eta_header: s.ui_show_eta_header !== false,
                ui_show_progress_percentage: s.ui_show_progress_percentage !== false,
            });

            const progressMap = {};
            progressRes.data.forEach(p => { progressMap[p.step_id] = p; });

            // Work on the visible subset
            const visible = stepsRes.data.filter(s => !isStepHidden(s, allDataRes.data));

            let currentIdx = 0;
            for (let i = 0; i < visible.length; i++) {
                const sp = progressMap[visible[i].id];
                if (!sp || sp.status !== 'completed') { currentIdx = i; break; }
                if (i === visible.length - 1) currentIdx = i;
            }
            setCurrentStepIndex(currentIdx);
            setExpandedStep(currentIdx);

            const currentProgress = progressMap[visible[currentIdx]?.id];
            if (currentProgress?.data && Object.keys(currentProgress.data).length > 0) {
                setFormData(currentProgress.data);
            } else {
                const prefilled = applyFieldMappings(visible[currentIdx] || {}, allDataRes.data);
                setFormData(prefilled);
            }

            // Trigger progress bar animation after data loads
            setTimeout(() => setAnimateProgress(true), 150);
        } catch (error) { console.error('Failed to load data:', error); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    // Auto-scroll to active step on mobile and desktop
    useEffect(() => {
        if (!loading && expandedStep !== null) {
            const isMobile = window.innerWidth < 768;
            if (isMobile && stepRefs.current[expandedStep]) {
                setTimeout(() => {
                    stepRefs.current[expandedStep]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 300);
            } else if (!isMobile && desktopStepRefs.current[expandedStep]) {
                setTimeout(() => {
                    desktopStepRefs.current[expandedStep]?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                }, 200);
            }
        }
    }, [loading, expandedStep]);

    useEffect(() => {
        const currentStep = visibleSteps[currentStepIndex];
        if (currentStep?.step_type === 'partner_selection' || currentStep?.step_type === 'partner_multiselection') {
            const existingProg = progress.find(p => p.step_id === currentStep.id);
            partnersAPI.getAll(currentStep.filter_tag || '').then(res => {
                setPartners(res.data);
                // Restore partner selection from saved progress
                if (existingProg?.data) {
                    if (currentStep.step_type === 'partner_selection' && existingProg.data.selected_partner_id) {
                        const found = res.data.find(p => p.id === existingProg.data.selected_partner_id);
                        if (found) setSelectedPartner(found);
                    } else if (currentStep.step_type === 'partner_multiselection' && existingProg.data.selected_partner_ids) {
                        const ids = existingProg.data.selected_partner_ids;
                        setSelectedPartners(res.data.filter(p => ids.includes(p.id)));
                    }
                }
            }).catch(() => {});
        }
        if (currentStep && allStepData.length > 0) {
            const existing = progress.find(p => p.step_id === currentStep.id);
            if (!existing?.data || Object.keys(existing.data).length === 0) {
                const prefilled = applyFieldMappings(currentStep, allStepData);
                if (Object.keys(prefilled).length > 0) setFormData(prev => ({ ...prefilled, ...prev }));
            }
        }
        setValidationErrors([]);
        setPartnerTagFilter('all');
    }, [currentStepIndex, visibleSteps, allStepData, progress]);

    const handleLogout = async () => { await logout(); navigate('/'); };
    const getProgressPercentage = () => {
        if (visibleSteps.length === 0) return 0;
        const countable = visibleSteps.filter(s => s.duration_value > 0);
        if (countable.length === 0) return 0;
        const completedCountable = countable.filter(s => getStepStatus(s.id) === 'completed').length;
        return Math.round((completedCountable / countable.length) * 100);
    };
    const getStepStatus = (stepId) => progress.find(p => p.step_id === stepId)?.status || 'pending';
    const handleInputChange = (fieldName, value) => { setFormData(prev => ({ ...prev, [fieldName]: value })); setValidationErrors([]); };

    const handleFileUpload = async (fieldName, file) => {
        try {
            const response = await filesAPI.upload(file);
            setUploadedFiles(prev => ({ ...prev, [fieldName]: response.data }));
            setFormData(prev => ({ ...prev, [fieldName]: response.data.id }));
            toast.success('Datei hochgeladen');
        } catch { toast.error('Fehler beim Hochladen'); }
    };

    const handleAddMultiuploadEntry = (fieldName) => {
        setFormData(prev => ({ ...prev, [fieldName]: [...(prev[fieldName] || []), { file_id: '', document_type: '' }] }));
    };
    const handleRemoveMultiuploadEntry = (fieldName, index) => {
        const c = [...(formData[fieldName] || [])]; c.splice(index, 1);
        setFormData(prev => ({ ...prev, [fieldName]: c }));
    };
    const handleMultiuploadFileChange = async (fieldName, index, file) => {
        try {
            const response = await filesAPI.upload(file);
            const c = [...(formData[fieldName] || [])];
            c[index] = { ...c[index], file_id: response.data.id, filename: response.data.filename };
            setFormData(prev => ({ ...prev, [fieldName]: c }));
            toast.success('Datei hochgeladen');
        } catch { toast.error('Fehler beim Hochladen'); }
    };
    const handleMultiuploadTypeChange = (fieldName, index, docType) => {
        const c = [...(formData[fieldName] || [])];
        c[index] = { ...c[index], document_type: docType };
        setFormData(prev => ({ ...prev, [fieldName]: c }));
    };

    const validateStep = () => {
        const currentStep = visibleSteps[currentStepIndex];
        if (!currentStep) return true;
        const errors = [];
        const reqFields = currentStep.required_fields || [];
        const reqUploads = currentStep.required_uploads || [];
        for (const rf of reqFields) {
            const val = formData[rf];
            if (!val || (typeof val === 'string' && !val.trim())) {
                const fieldDef = currentStep.fields?.find(f => f.name === rf);
                errors.push(`${fieldDef?.label || rf} ist ein Pflichtfeld`);
            }
        }
        if (reqUploads.length > 0) {
            const uploadedTypes = new Set();
            for (const field of (currentStep.fields || [])) {
                if (field.field_type === 'multiupload') {
                    for (const entry of (formData[field.name] || [])) {
                        if (entry?.file_id && entry?.document_type) uploadedTypes.add(entry.document_type);
                    }
                }
            }
            for (const ru of reqUploads) {
                if (!uploadedTypes.has(ru)) errors.push(`Dokument erforderlich: ${ru}`);
            }
        }
        setValidationErrors(errors);
        return errors.length === 0;
    };

    const handleStepSubmit = async (markComplete = false, overrideData = null) => {
        const currentStep = visibleSteps[currentStepIndex];
        if (!currentStep) return;
        const payload = overrideData !== null ? overrideData : formData;
        if (markComplete && overrideData === null && !validateStep()) { toast.error('Bitte füllen Sie alle Pflichtfelder aus'); return; }
        setSubmitting(true);
        try {
            const status = markComplete ? 'completed' : 'in_progress';
            await stepsAPI.updateProgress(currentStep.id, status, payload);
            if (markComplete) {
                toast.success('Schritt abgeschlossen!');
                if (currentStepIndex < visibleSteps.length - 1) {
                    const nextIdx = currentStepIndex + 1;
                    setCurrentStepIndex(nextIdx);
                    setExpandedStep(nextIdx);
                    setFormData({});
                    setSelectedPartner(null);
                    setSelectedPartners([]);
                }
            } else { toast.success('Fortschritt gespeichert'); }
            await loadData();
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSubmitting(false); }
    };

    const handleDecisionChoice = async (value) => {
        // A decision step is completed immediately when a choice is made
        await handleStepSubmit(true, { decision: value });
    };

    const handleSkipStep = async () => {
        const currentStep = visibleSteps[currentStepIndex];
        if (!currentStep) return;
        setSubmitting(true);
        try {
            await stepsAPI.updateProgress(currentStep.id, 'completed', { skipped: true });
            toast.success('Schritt übersprungen');
            if (currentStepIndex < visibleSteps.length - 1) {
                const nextIdx = currentStepIndex + 1;
                setCurrentStepIndex(nextIdx);
                setExpandedStep(nextIdx);
                setFormData({});
                setSelectedPartner(null);
            }
            await loadData();
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSubmitting(false); }
    };

    const handlePartnerSelect = (partner) => {
        setSelectedPartner(partner);
        setFormData(prev => ({ ...prev, selected_partner_id: partner.id, selected_partner_name: partner.name }));
    };

    const handleToggleMultiPartner = (partner) => {
        setSelectedPartners(prev => {
            const exists = prev.find(p => p.id === partner.id);
            const updated = exists ? prev.filter(p => p.id !== partner.id) : [...prev, partner];
            setFormData(fd => ({ ...fd, selected_partner_ids: updated.map(p => p.id), selected_partner_names: updated.map(p => p.name).join(', ') }));
            return updated;
        });
    };

    const handlePartnerSubmission = async () => {
        if (!selectedPartner) { toast.error('Bitte wählen Sie einen Partner'); return; }
        setSubmitting(true);
        try {
            await partnersAPI.submit(selectedPartner.id, formData);
            await handleStepSubmit(true);
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSubmitting(false); }
    };

    const handleMultiPartnerSubmission = async () => {
        if (selectedPartners.length === 0) { toast.error('Bitte wählen Sie mindestens einen Partner'); return; }
        setSubmitting(true);
        try {
            await partnersAPI.submitMulti(selectedPartners.map(p => p.id), formData);
            await handleStepSubmit(true);
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSubmitting(false); }
    };

    const canNavigateToStep = (idx) => {
        const step = visibleSteps[idx];
        if (!step) return false;
        const status = getStepStatus(step.id);
        if (status === 'completed') return true;
        if (idx <= currentStepIndex) return true;
        if (allStepData.length > 0) {
            const condResult = evaluateStepConditions(step, allStepData);
            if (condResult.blocked) return false;
        }
        return false;
    };

    const handleStepClick = (idx) => {
        if (!canNavigateToStep(idx)) return;
        setCurrentStepIndex(idx);
        setExpandedStep(expandedStep === idx ? null : idx);
        const step = visibleSteps[idx];
        const stepProgress = progress.find(p => p.step_id === step?.id);
        if (stepProgress?.data && Object.keys(stepProgress.data).length > 0) {
            setFormData(stepProgress.data);
            // Restore partner selection state from saved data
            if (step?.step_type === 'partner_selection' && stepProgress.data.selected_partner_id) {
                partnersAPI.getAll(step.filter_tag || '').then(res => {
                    setPartners(res.data);
                    const found = res.data.find(p => p.id === stepProgress.data.selected_partner_id);
                    setSelectedPartner(found || null);
                }).catch(() => {});
            } else if (step?.step_type === 'partner_multiselection' && stepProgress.data.selected_partner_ids) {
                partnersAPI.getAll(step.filter_tag || '').then(res => {
                    setPartners(res.data);
                    const ids = stepProgress.data.selected_partner_ids;
                    setSelectedPartners(res.data.filter(p => ids.includes(p.id)));
                }).catch(() => {});
            } else {
                setSelectedPartner(null);
                setSelectedPartners([]);
            }
        } else {
            const prefilled = applyFieldMappings(step || {}, allStepData);
            setFormData(prefilled);
            setSelectedPartner(null);
            setSelectedPartners([]);
        }
    };

    // Render form field
    const renderFormField = (field) => {
        const value = formData[field.name] || '';
        const hasError = validationErrors.some(e => e.includes(field.label || field.name));
        const currentStep = visibleSteps[currentStepIndex];
        const fieldLabel = (lang !== 'de' && currentStep?.translations?.[lang]?.field_labels?.[field.name]) || field.label;

        if (field.field_type === 'selectbox' || field.field_type === 'select') {
            return (
                <div key={field.name} className="space-y-2">
                    <Label className="text-foreground">{fieldLabel} {field.required && <span className="text-red-500">*</span>}</Label>
                    <Select value={value} onValueChange={(val) => handleInputChange(field.name, val)}>
                        <SelectTrigger className={`border-border rounded-sm ${hasError ? 'border-red-500' : ''}`} data-testid={`form-field-${field.name}`}>
                            <SelectValue placeholder="Bitte wählen..." />
                        </SelectTrigger>
                        <SelectContent>{field.options?.map(opt => <SelectItem key={opt} value={opt}>{opt}</SelectItem>)}</SelectContent>
                    </Select>
                </div>
            );
        }
        if (field.field_type === 'multiupload') {
            const entries = formData[field.name] || [];
            return (
                <div key={field.name} className="space-y-3">
                    <Label className="text-foreground">{fieldLabel} {field.required && <span className="text-red-500">*</span>}</Label>
                    {entries.map((entry, idx) => (
                        <div key={idx} className="flex flex-col sm:flex-row gap-2 p-3 bg-muted rounded-sm border border-border" data-testid={`multiupload-entry-${idx}`}>
                            <div className="flex-1">
                                <Select value={entry.document_type} onValueChange={(val) => handleMultiuploadTypeChange(field.name, idx, val)}>
                                    <SelectTrigger className="border-border rounded-sm text-sm h-9"><SelectValue placeholder="Dokumenttyp..." /></SelectTrigger>
                                    <SelectContent>{field.options?.map(opt => <SelectItem key={opt} value={opt}>{opt}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div className="flex-1">
                                {entry.file_id ? (
                                    <div className="flex items-center gap-2 h-9 px-3 bg-card border border-border rounded-sm text-sm"><Check size={14} className="text-green-600" /><span className="truncate">{entry.filename || 'Hochgeladen'}</span></div>
                                ) : (
                                    <div className="relative">
                                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => e.target.files[0] && handleMultiuploadFileChange(field.name, idx, e.target.files[0])} />
                                        <div className="flex items-center gap-2 h-9 px-3 border border-dashed border-border rounded-sm text-sm text-muted-foreground cursor-pointer hover:border-[#114f55]"><CloudArrowUp size={16} /> Datei auswählen</div>
                                    </div>
                                )}
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => handleRemoveMultiuploadEntry(field.name, idx)} className="text-red-500 h-9 w-9 p-0 flex-shrink-0"><Trash size={16} /></Button>
                        </div>
                    ))}
                    <Button type="button" variant="outline" size="sm" onClick={() => handleAddMultiuploadEntry(field.name)} className="border-border" data-testid={`add-multiupload-${field.name}`}><Plus size={16} className="mr-1" /> Dokument hinzufügen</Button>
                </div>
            );
        }
        if (field.field_type === 'textarea') {
            return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{fieldLabel} {field.required && <span className="text-red-500">*</span>}</Label><Textarea value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} placeholder={field.placeholder} className={`border-border rounded-sm min-h-[100px] ${hasError ? 'border-red-500' : ''}`} data-testid={`form-field-${field.name}`} /></div>);
        }
        if (field.field_type === 'file') {
            return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{fieldLabel} {field.required && <span className="text-red-500">*</span>}</Label><div className="dropzone p-6 rounded-sm text-center cursor-pointer"><input type="file" id={field.name} className="hidden" onChange={(e) => e.target.files[0] && handleFileUpload(field.name, e.target.files[0])} data-testid={`form-field-${field.name}`} /><label htmlFor={field.name} className="cursor-pointer">{uploadedFiles[field.name] ? <div className="flex items-center justify-center gap-2 text-[#114f55]"><Check size={20} /><span>{uploadedFiles[field.name].filename}</span></div> : <div className="flex flex-col items-center gap-2 text-muted-foreground"><CloudArrowUp size={32} /><span>Klicken zum Hochladen</span></div>}</label></div></div>);
        }
        if (field.field_type === 'date') {
            return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{fieldLabel} {field.required && <span className="text-red-500">*</span>}</Label><Input type="date" value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} className={`border-border rounded-sm ${hasError ? 'border-red-500' : ''}`} data-testid={`form-field-${field.name}`} /></div>);
        }
        return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{fieldLabel} {field.required && <span className="text-red-500">*</span>}</Label><Input type={field.field_type === 'phone' ? 'tel' : field.field_type === 'email' ? 'email' : 'text'} value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} placeholder={field.placeholder} className={`border-border rounded-sm ${hasError ? 'border-red-500' : ''}`} data-testid={`form-field-${field.name}`} /></div>);
    };

    const renderStepContent = (scope = 'desktop') => {
        const currentStep = visibleSteps[currentStepIndex];
        if (!currentStep) return null;
        const stepStatus = getStepStatus(currentStep.id);
        const condResult = allStepData.length > 0 ? evaluateStepConditions(currentStep, allStepData) : { allowed: true, blocked: false, message: '' };

        // Journey progress banner — shown above every active step card so the
        // user always knows "where am I + what's next". Rendered once and
        // composed with the step-specific content at the end. Can be toggled
        // off globally via Admin → Settings → UI-Elemente.
        const indicator = uiFlags.ui_show_journey_indicator ? (
            <JourneyProgressIndicator
                visibleSteps={visibleSteps}
                currentIndex={currentStepIndex}
                allSteps={steps}
            />
        ) : null;
        const withIndicator = (content) => (<>{indicator}{content}</>);

        if (condResult.blocked) {
            return withIndicator(
                <div className="p-8 bg-muted border border-border rounded-sm text-center">
                    <Lock size={48} className="mx-auto text-muted-foreground mb-4" />
                    <p className="text-lg font-semibold text-foreground">{condResult.message}</p>
                </div>
            );
        }

        const stepContent = (() => {
            switch (currentStep.step_type) {
            case 'decision': {
                const decField = (currentStep.fields || []).find(f => f.field_type === 'decision') || (currentStep.fields || [])[0];
                const options = decField?.options || [];
                const currentChoice = formData.decision;
                return (
                    <div className="space-y-6" data-testid="decision-step">
                        {(currentStep.content || currentStep.pending_message) && (
                            <div className="prose prose-sm dark:prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: currentStep.content || currentStep.pending_message }} />
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {options.map((opt, i) => {
                                const isActive = currentChoice === opt.value;
                                return (
                                    <button
                                        key={opt.value}
                                        onClick={() => handleDecisionChoice(opt.value)}
                                        disabled={submitting}
                                        className={`group relative text-left p-6 rounded-sm border-2 transition-all duration-200
                                            ${isActive
                                                ? 'border-[#114f55] bg-[#114f55]/5 shadow-md'
                                                : 'border-border bg-card hover:border-[#114f55]/40 hover:shadow-sm'}
                                            ${submitting ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                                        data-testid={`decision-option-${scope === 'desktop' ? i : `mobile-${i}`}`}
                                    >
                                        <div className="flex items-start gap-4">
                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors
                                                ${isActive ? 'bg-[#114f55] text-white' : 'bg-muted text-muted-foreground group-hover:bg-[#114f55]/10 group-hover:text-[#114f55]'}`}>
                                                {isActive ? <Check size={18} weight="bold" /> : <ArrowRight size={18} />}
                                            </div>
                                            <div className="flex-1">
                                                <p className={`font-semibold ${isActive ? 'text-[#114f55]' : 'text-foreground'}`}>{opt.label}</p>
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                );
            }
            case 'form': {
                // Upload step guard: if this form has a required multiupload field,
                // the Complete button must stay disabled until at least one file is present.
                const missingRequiredUpload = (currentStep.fields || []).some((f) =>
                    f.field_type === 'multiupload' && f.required
                    && !(Array.isArray(formData[f.name])
                         && formData[f.name].some((e) => e && e.file_id))
                );
                return (
                    <div className="space-y-6">
                        {currentStep.fields?.map(renderFormField)}
                        {validationErrors.length > 0 && (
                            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-sm" data-testid="validation-errors">
                                <p className="text-sm font-medium text-red-700 dark:text-red-300 mb-2">Bitte korrigieren Sie folgende Fehler:</p>
                                <ul className="text-sm text-red-600 dark:text-red-400 list-disc list-inside">
                                    {validationErrors.map((e, i) => <li key={i}>{e}</li>)}
                                </ul>
                            </div>
                        )}
                        <div className="flex flex-wrap gap-3 pt-4">
                            <Button variant="outline" onClick={() => handleStepSubmit(false)} disabled={submitting} className="border-border" data-testid="save-progress-btn">{t('dash_save_progress')}</Button>
                            <Button
                                onClick={() => handleStepSubmit(true)}
                                disabled={submitting || missingRequiredUpload}
                                className="bg-[#114f55] hover:bg-[#0d3d42] text-white disabled:opacity-50 disabled:cursor-not-allowed"
                                data-testid="complete-step-btn"
                                title={missingRequiredUpload ? 'Bitte laden Sie mindestens ein Dokument hoch' : undefined}
                            >
                                {submitting
                                    ? t('dash_saving')
                                    : missingRequiredUpload
                                        ? 'Upload erforderlich'
                                        : t('dash_complete_continue')}
                                {!missingRequiredUpload && !submitting && <ArrowRight className="ml-2" size={16} />}
                            </Button>
                        </div>
                    </div>
                );
            }
            case 'partner_selection': {
                const profile = allStepData.find(s => s.order === 1)?.data || {};
                const sortedPartners = sortPartnersByRecommendation(partners, profile);
                const partnerTags = [...new Set(sortedPartners.flatMap(p => p.tags || []))].sort();
                const filteredPartners = partnerTagFilter && partnerTagFilter !== 'all'
                    ? sortedPartners.filter(p => (p.tags || []).includes(partnerTagFilter) || p.category === partnerTagFilter)
                    : sortedPartners;
                return (
                    <div className="space-y-6">
                        {partnerTags.length > 1 && (
                            <div className="flex items-center gap-3">
                                <Label className="text-sm text-muted-foreground whitespace-nowrap">{t('filter')}:</Label>
                                <Select value={partnerTagFilter} onValueChange={setPartnerTagFilter}>
                                    <SelectTrigger className="h-9 w-48 text-sm" data-testid="partner-tag-filter">
                                        <SelectValue placeholder={t('partner_filter_all')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">{t('partner_filter_all')}</SelectItem>
                                        {partnerTags.map(tag => <SelectItem key={tag} value={tag}>{tag}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {filteredPartners.map(partner => (
                                <div key={partner.id} onClick={() => handlePartnerSelect(partner)} className={`partner-card relative p-6 rounded-sm cursor-pointer transition-all ${selectedPartner?.id === partner.id ? 'border-[#114f55] border-2 bg-[#114f55]/5' : 'bg-card'} ${partner._score > 0 ? 'ring-1 ring-[#114f55]/20' : ''}`} data-testid={`partner-select-${partner.id}`}>
                                    {partner._score > 0 && (
                                        <span className="absolute -top-2 right-3 px-2 py-0.5 text-[10px] font-semibold bg-[#114f55] text-white rounded-sm shadow-sm" data-testid={`recommended-badge-${partner.id}`}>
                                            ★ {t('recommended_for_you') || 'Empfohlen für dich'}
                                        </span>
                                    )}
                                    <div className="flex items-start gap-4">
                                        {partner.logo_url && <img src={partner.logo_url} alt={partner.name} className="w-12 h-12 object-cover rounded-sm" />}
                                        <div className="flex-1">
                                            <h3 className="font-semibold text-foreground">{partner.name}</h3>
                                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{partner.description}</p>
                                            {partner.tags?.map(tag => <span key={tag} className="inline-block mt-2 mr-1 px-2 py-1 text-xs bg-muted text-muted-foreground rounded-sm">{tag}</span>)}
                                        </div>
                                        {selectedPartner?.id === partner.id && <Check size={24} className="text-[#114f55]" />}
                                    </div>
                                </div>
                            ))}
                            {filteredPartners.length === 0 && <div className="col-span-2 text-center py-8 text-muted-foreground">Keine Partner verfuegbar</div>}
                        </div>
                        <div className="flex flex-wrap gap-3 pt-4">
                            <Button onClick={handlePartnerSubmission} disabled={!selectedPartner || submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="confirm-partner-btn">{submitting ? t('dash_saving') : t('dash_confirm_selection')} <ArrowRight className="ml-2" size={16} /></Button>
                            {currentStep.skippable && <Button variant="outline" onClick={handleSkipStep} disabled={submitting} className="border-border text-muted-foreground" data-testid="skip-step-btn"><SkipForward size={16} className="mr-1" /> {loc(currentStep, 'skip_label') || 'Ueberspringen'}</Button>}
                        </div>
                    </div>
                );
            }
            case 'partner_multiselection': {
                const profile = allStepData.find(s => s.order === 1)?.data || {};
                const sortedMulti = sortPartnersByRecommendation(partners, profile);
                const multiTags = [...new Set(sortedMulti.flatMap(p => p.tags || []).concat(sortedMulti.map(p => p.category).filter(Boolean)))].sort();
                const filteredMultiPartners = partnerTagFilter && partnerTagFilter !== 'all'
                    ? sortedMulti.filter(p => (p.tags || []).includes(partnerTagFilter) || p.category === partnerTagFilter)
                    : sortedMulti;
                return (
                    <div className="space-y-6">
                        {multiTags.length > 1 && (
                            <div className="flex items-center gap-3">
                                <Label className="text-sm text-muted-foreground whitespace-nowrap">{t('filter')}:</Label>
                                <Select value={partnerTagFilter} onValueChange={setPartnerTagFilter}>
                                    <SelectTrigger className="h-9 w-48 text-sm" data-testid="partner-tag-filter">
                                        <SelectValue placeholder={t('partner_filter_all')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">{t('partner_filter_all')}</SelectItem>
                                        {multiTags.map(tag => <SelectItem key={tag} value={tag}>{tag}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                        <p className="text-sm text-muted-foreground">Sie koennen mehrere Partner auswaehlen.</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {filteredMultiPartners.map(partner => {
                                const isSelected = selectedPartners.some(p => p.id === partner.id);
                                return (
                                    <div key={partner.id} onClick={() => handleToggleMultiPartner(partner)} className={`partner-card relative p-6 rounded-sm cursor-pointer transition-all ${isSelected ? 'border-[#114f55] border-2 bg-[#114f55]/5' : 'bg-card'} ${partner._score > 0 ? 'ring-1 ring-[#114f55]/20' : ''}`} data-testid={`partner-multiselect-${partner.id}`}>
                                        {partner._score > 0 && (
                                            <span className="absolute -top-2 right-3 px-2 py-0.5 text-[10px] font-semibold bg-[#114f55] text-white rounded-sm shadow-sm" data-testid={`recommended-badge-${partner.id}`}>
                                                ★ {t('recommended_for_you') || 'Empfohlen für dich'}
                                            </span>
                                        )}
                                        <div className="flex items-start gap-4">
                                            {partner.logo_url && <img src={partner.logo_url} alt={partner.name} className="w-12 h-12 object-cover rounded-sm" />}
                                            <div className="flex-1">
                                                <h3 className="font-semibold text-foreground">{partner.name}</h3>
                                                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{partner.description}</p>
                                                {partner.tags?.map(tag => <span key={tag} className="inline-block mt-2 mr-1 px-2 py-1 text-xs bg-muted text-muted-foreground rounded-sm">{tag}</span>)}
                                            </div>
                                            {isSelected && <Check size={24} className="text-[#114f55]" />}
                                        </div>
                                    </div>
                                );
                            })}
                            {filteredMultiPartners.length === 0 && <div className="col-span-2 text-center py-8 text-muted-foreground">Keine Partner verfuegbar</div>}
                        </div>
                        {selectedPartners.length > 0 && (
                            <div className="text-sm text-muted-foreground">{selectedPartners.length} Partner ausgewaehlt: {selectedPartners.map(p => p.name).join(', ')}</div>
                        )}
                        <div className="flex flex-wrap gap-3 pt-4">
                            <Button onClick={handleMultiPartnerSubmission} disabled={selectedPartners.length === 0 || submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="confirm-multipartner-btn">{submitting ? t('dash_saving') : t('dash_confirm_selection')} <ArrowRight className="ml-2" size={16} /></Button>
                            {currentStep.skippable && <Button variant="outline" onClick={handleSkipStep} disabled={submitting} className="border-border text-muted-foreground" data-testid="skip-step-btn"><SkipForward size={16} className="mr-1" /> {loc(currentStep, 'skip_label') || 'Ueberspringen'}</Button>}
                        </div>
                    </div>
                );
            }
            case 'milestone':
                return (
                    <div className="space-y-6">
                        {stepStatus === 'completed' ? (
                            <div className="p-8 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-sm text-center">
                                <CheckCircle size={48} className="mx-auto text-green-600 mb-4" />
                                <p className="text-lg font-semibold text-green-800 dark:text-green-300">{loc(currentStep, 'complete_message') || t('dash_all_done')}</p>
                                <Button onClick={() => { if (currentStepIndex < visibleSteps.length - 1) { setCurrentStepIndex(currentStepIndex + 1); setExpandedStep(currentStepIndex + 1); } }} className="mt-6 bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="milestone-next-btn">Weiter <ArrowRight className="ml-2" size={16} /></Button>
                            </div>
                        ) : (
                            <div className="p-8 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-sm text-center">
                                <WarningCircle size={48} className="mx-auto text-yellow-600 mb-4" />
                                <p className="text-lg font-semibold text-yellow-800 dark:text-yellow-300">{loc(currentStep, 'pending_message') || t('dash_waiting')}</p>
                                <p className="text-sm text-muted-foreground mt-2">Dieser Schritt wird von Ihrem Partner bearbeitet.</p>
                            </div>
                        )}
                    </div>
                );
            case 'display':
                return (
                    <div className="space-y-6">
                        {loc(currentStep, 'content') && (
                            <div className="prose prose-sm dark:prose-invert max-w-none p-6 bg-muted rounded-sm border border-border" dangerouslySetInnerHTML={{ __html: loc(currentStep, 'content') }} />
                        )}
                        {loc(currentStep, 'pending_message') && !loc(currentStep, 'content') && <div className="p-6 bg-muted rounded-sm border border-border"><p className="text-foreground">{loc(currentStep, 'pending_message')}</p></div>}
                        {currentStep.link_url && (
                            <a href={currentStep.link_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-4 py-2 bg-[#114f55]/10 text-[#114f55] rounded-sm hover:bg-[#114f55]/20 transition-colors font-medium text-sm" data-testid="step-external-link">
                                {loc(currentStep, 'link_label') || currentStep.link_url}
                                <ArrowRight size={14} />
                            </a>
                        )}
                        {currentStep.field_mappings?.length > 0 && (
                            <div className="p-4 bg-muted rounded-sm border border-border space-y-2">
                                <p className="text-sm font-semibold text-muted-foreground">Ihre Daten:</p>
                                {currentStep.field_mappings.map((m, i) => {
                                    const src = allStepData.find(s => s.order === m.source_step_order);
                                    const val = src?.data?.[m.source_field];
                                    return val ? <div key={i} className="text-sm"><span className="text-muted-foreground">{m.target_field}: </span><span className="font-medium text-foreground">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span></div> : null;
                                })}
                            </div>
                        )}
                        <div className="flex flex-wrap gap-3">
                            {loc(currentStep, 'action_label') ? (
                                <Button onClick={() => handleStepSubmit(true)} disabled={submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="display-action-btn">{loc(currentStep, 'action_label')} <ArrowRight className="ml-2" size={16} /></Button>
                            ) : (
                                <Button onClick={() => handleStepSubmit(true)} disabled={submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="display-next-btn">Weiter <ArrowRight className="ml-2" size={16} /></Button>
                            )}
                        </div>
                    </div>
                );
            default:
                return <p>Unbekannter Schritttyp</p>;
            }
        })();

        return withIndicator(stepContent);
    };

    if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><div className="text-muted-foreground">{t('loading')}</div></div>;

    const completedCount = visibleSteps.filter(s => getStepStatus(s.id) === 'completed').length;
    const mobileProgress = visibleSteps.length === 0 ? 0 : Math.round((completedCount / visibleSteps.length) * 100);

    return (
        <div className="min-h-screen bg-background">
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <Logo />
                        <div className="flex items-center gap-3">
                            {/* Completion % + estimated completion in header */}
                            {(estimatedCompletion && (uiFlags.ui_show_eta_header || uiFlags.ui_show_progress_percentage)) && (
                                <div className="hidden sm:flex items-center gap-2" data-testid="header-progress-wrapper">
                                    {uiFlags.ui_show_eta_header && (
                                        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#114f55] text-white rounded-full cursor-default" data-testid="estimated-completion-banner" title="Voraussichtliche Approbation">
                                            <CalendarCheck size={16} weight="bold" />
                                            <span className="text-sm font-bold" data-testid="estimated-completion-date">
                                                {new Date(estimatedCompletion).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                                            </span>
                                        </div>
                                    )}
                                    {uiFlags.ui_show_progress_percentage && (
                                        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#114f55]/10 text-[#114f55] rounded-full cursor-default" data-testid="header-completion-pct-wrapper" title={t('progress_title') || 'Fortschritt'}>
                                            <div className="w-14 h-1.5 bg-[#114f55]/20 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-[#114f55] rounded-full transition-all"
                                                    style={{ width: `${getProgressPercentage()}%` }}
                                                />
                                            </div>
                                            <span className="text-sm font-bold tabular-nums" data-testid="header-completion-pct">
                                                {getProgressPercentage()}%
                                            </span>
                                        </div>
                                    )}
                                </div>
                            )}
                            <span className="text-sm text-muted-foreground hidden lg:block">{t('dash_welcome')}, {user?.name}</span>
                            <ThemeLangToggle />
                            <Button variant="ghost" size="sm" onClick={() => { setShowTimeline(!showTimeline); setShowSettings(false); }} className={`text-muted-foreground ${showTimeline ? 'bg-muted' : ''}`} data-testid="timeline-btn" title="Verlauf"><ClockCounterClockwise size={20} /></Button>
                            <Button variant="ghost" size="sm" onClick={() => { setShowSettings(!showSettings); setShowTimeline(false); }} className={`text-muted-foreground ${showSettings ? 'bg-muted' : ''}`} data-testid="settings-btn"><GearSix size={20} /></Button>
                            {impersonating && (
                                <Button size="sm" onClick={() => { stopImpersonation(); navigate('/admin'); }} className="bg-red-600 hover:bg-red-700 text-white" data-testid="stop-impersonation-btn">
                                    <UserSwitch size={16} className="mr-1" /> Beenden
                                </Button>
                            )}
                            {!impersonating && <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground" data-testid="logout-btn"><SignOut size={20} /></Button>}
                        </div>
                    </div>
                    {/* Mobile estimated completion + progress */}
                    {(estimatedCompletion && (uiFlags.ui_show_eta_header || uiFlags.ui_show_progress_percentage)) && (
                        <div className="sm:hidden flex items-center gap-3 pb-3 -mt-1">
                            {uiFlags.ui_show_eta_header && (
                                <div className="flex items-center gap-2" data-testid="estimated-completion-banner-mobile" title="Voraussichtliche Approbation">
                                    <CalendarCheck size={14} className="text-[#114f55]" />
                                    <span className="text-xs font-bold text-[#114f55]" data-testid="estimated-completion-date-mobile">
                                        {new Date(estimatedCompletion).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                                    </span>
                                </div>
                            )}
                            {uiFlags.ui_show_progress_percentage && (
                                <div className="flex items-center gap-2" data-testid="header-completion-pct-mobile-wrapper">
                                    <div className="w-10 h-1.5 bg-[#114f55]/20 rounded-full overflow-hidden">
                                        <div className="h-full bg-[#114f55] rounded-full transition-all" style={{ width: `${getProgressPercentage()}%` }} />
                                    </div>
                                    <span className="text-xs font-bold text-[#114f55] tabular-nums" data-testid="header-completion-pct-mobile">
                                        {getProgressPercentage()}%
                                    </span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" ref={containerRef}>
                {/* ====== DESKTOP: Horizontal Step Cards in single row ====== */}
                <div className="hidden md:block mb-8">
                    <div className="rounded-lg overflow-hidden overflow-x-auto shadow-sm border border-border">
                        <div className="flex min-w-max">
                            {visibleSteps.map((step, index) => {
                                const status = getStepStatus(step.id);
                                const isActive = index === currentStepIndex;
                                const isCompleted = status === 'completed';
                                const navigable = canNavigateToStep(index);
                                const condResult = allStepData.length > 0 ? evaluateStepConditions(step, allStepData) : { blocked: false };
                                const isBlocked = condResult.blocked && !isCompleted;

                                let stepProg = 0;
                                if (isCompleted) stepProg = 100;
                                else if (status === 'in_progress') stepProg = 50;
                                else if (isActive) stepProg = 15;

                                return (
                                    <button
                                        key={step.id}
                                        ref={el => desktopStepRefs.current[index] = el}
                                        onClick={() => navigable && handleStepClick(index)}
                                        disabled={!navigable}
                                        className={`relative text-left transition-all duration-200
                                            ${index < visibleSteps.length - 1 ? 'border-r border-border' : ''}
                                            ${isBlocked ? 'opacity-40 cursor-not-allowed bg-card' :
                                            isActive ? 'bg-[#114f55]/5' :
                                            isCompleted ? 'bg-green-50/50 dark:bg-green-900/10' :
                                            'bg-card hover:bg-muted/50'}
                                            ${navigable ? 'cursor-pointer' : 'cursor-not-allowed'}`}
                                        data-testid={`step-card-${index}`}
                                    >
                                        {/* Progress bar inside each tile */}
                                        <div className="h-[5px] bg-muted" data-testid={`step-progress-${index}`}>
                                            <div
                                                className="h-full transition-all ease-out"
                                                style={{
                                                    width: animateProgress ? `${stepProg}%` : '0%',
                                                    transitionDuration: '0.35s',
                                                    transitionDelay: `${index * 0.35}s`,
                                                    backgroundColor: isCompleted ? '#22c55e' : '#114f55',
                                                }}
                                            />
                                        </div>
                                        <div className="flex items-center gap-2.5 px-4 py-3 whitespace-nowrap">
                                            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors duration-300
                                                ${isBlocked ? 'bg-muted text-muted-foreground' :
                                                isCompleted ? 'bg-green-500 text-white' :
                                                isActive ? 'bg-[#114f55] text-white' :
                                                'bg-muted text-muted-foreground'}`}>
                                                {isBlocked ? <Lock size={11} /> : isCompleted ? <Check size={11} weight="bold" /> : index + 1}
                                            </div>
                                            <span className={`text-sm font-semibold ${isActive ? 'text-[#114f55]' : 'text-foreground'}`}>{loc(step, 'title')}</span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* ====== MOBILE: Vertical Accordion with Progress Line ====== */}
                <div className="md:hidden mb-6">
                    <div className="relative">
                        {/* Vertical progress line */}
                        <div className="absolute left-[19px] top-4 bottom-4 w-[3px] bg-border rounded-full overflow-hidden">
                            <div
                                className="w-full bg-[#114f55] rounded-full transition-all ease-out"
                                style={{
                                    height: animateProgress ? `${mobileProgress}%` : '0%',
                                    transitionDuration: '1.4s',
                                }}
                                data-testid="mobile-vertical-progress"
                            />
                        </div>

                        <div className="space-y-0">
                            {visibleSteps.map((step, index) => {
                                const status = getStepStatus(step.id);
                                const isActive = index === currentStepIndex;
                                const isCompleted = status === 'completed';
                                const isExpanded = expandedStep === index;
                                const navigable = canNavigateToStep(index);
                                const condResult = allStepData.length > 0 ? evaluateStepConditions(step, allStepData) : { blocked: false };
                                const isBlocked = condResult.blocked && !isCompleted;

                                return (
                                    <div
                                        key={step.id}
                                        ref={el => stepRefs.current[index] = el}
                                        className="relative"
                                        data-testid={`mobile-step-${index}`}
                                    >
                                        {/* Step header (accordion trigger) */}
                                        <button
                                            onClick={() => navigable && handleStepClick(index)}
                                            disabled={!navigable}
                                            className={`relative z-10 flex items-center gap-3 w-full text-left py-4 pl-1 pr-3 transition-all duration-200
                                                ${!navigable ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
                                            data-testid={`step-nav-${index}`}
                                        >
                                            {/* Circle on the progress line */}
                                            <div className={`relative z-20 w-[38px] h-[38px] rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 border-[3px] transition-all duration-300
                                                ${isBlocked ? 'border-border bg-muted text-muted-foreground' :
                                                isCompleted ? 'border-green-500 bg-green-500 text-white' :
                                                isActive ? 'border-[#114f55] bg-[#114f55] text-white ring-4 ring-[#114f55]/20' :
                                                'border-border bg-card text-muted-foreground'}`}
                                            >
                                                {isBlocked ? <Lock size={12} /> : isCompleted ? <Check size={14} weight="bold" /> : index + 1}
                                            </div>

                                            <div className="flex-1 min-w-0">
                                                <p className={`text-sm font-semibold truncate ${isActive ? 'text-[#114f55]' : isCompleted ? 'text-green-700 dark:text-green-400' : 'text-foreground'}`}>
                                                    {loc(step, 'title')}
                                                </p>
                                                {!isExpanded && (
                                                    <p className="text-xs text-muted-foreground truncate">{loc(step, 'description')}</p>
                                                )}
                                            </div>

                                            <CaretDown
                                                size={16}
                                                className={`text-muted-foreground flex-shrink-0 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                                            />
                                        </button>

                                        {/* Accordion content */}
                                        <div
                                            className={`overflow-hidden transition-all duration-400 ease-in-out ${isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}
                                        >
                                            <div className="ml-[50px] pb-6 pr-2">
                                                <div className="bg-card border border-border rounded-lg p-5 shadow-sm">
                                                    <p className="text-sm text-muted-foreground mb-4">{loc(step, 'description')}</p>
                                                    {isActive && renderStepContent('mobile')}
                                                    {!isActive && isCompleted && (
                                                        <div className="flex items-center gap-2 text-green-600 text-sm">
                                                            <CheckCircle size={16} /> Abgeschlossen
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* ====== DESKTOP: Active step content ====== */}
                <div className="hidden md:block">
                    <div className="bg-card border border-border rounded-lg p-6 sm:p-8 shadow-sm animate-fadeIn">
                        {visibleSteps[currentStepIndex] && (
                            <>
                                <div className="mb-6">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="w-8 h-8 rounded-full bg-[#114f55] text-white flex items-center justify-center text-sm font-bold">
                                            {currentStepIndex + 1}
                                        </div>
                                        <h1 className="text-2xl font-bold tracking-tight text-foreground">{loc(visibleSteps[currentStepIndex], 'title')}</h1>
                                    </div>
                                    <p className="text-muted-foreground ml-11">{loc(visibleSteps[currentStepIndex], 'description')}</p>
                                </div>
                                {renderStepContent('desktop')}
                            </>
                        )}
                        {currentStepIndex > 0 && (
                            <div className="mt-8 pt-6 border-t border-border">
                                <Button variant="ghost" onClick={() => { setCurrentStepIndex(currentStepIndex - 1); setExpandedStep(currentStepIndex - 1); }} className="text-muted-foreground" data-testid="prev-step-btn"><ArrowLeft className="mr-2" size={16} /> {t('dash_prev_step')}</Button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Settings panel */}
                {showSettings && (
                    <div className="mt-6 bg-card border border-border rounded-lg p-6 sm:p-8 animate-fadeIn">
                        <div className="flex items-center gap-3 mb-6"><Bell size={24} className="text-[#114f55]" /><h2 className="text-xl font-bold tracking-tight text-foreground">{t('notif_title')}</h2></div>
                        <p className="text-sm text-muted-foreground mb-6">{t('notif_desc')}</p>
                        <div className="space-y-4">
                            {[['email_on_step_enter', 'notif_step_enter', 'notif_step_enter_desc'], ['email_on_step_edit', 'notif_step_edit', 'notif_step_edit_desc'], ['email_on_step_leave', 'notif_step_leave', 'notif_step_leave_desc']].map(([key, tKey, dKey]) => (
                                <div key={key} className="flex items-center justify-between p-4 bg-muted rounded-sm">
                                    <div><p className="font-medium text-foreground">{t(tKey)}</p><p className="text-sm text-muted-foreground">{t(dKey)}</p></div>
                                    <Switch checked={notifPrefs[key]} onCheckedChange={(val) => setNotifPrefs(prev => ({ ...prev, [key]: val }))} />
                                </div>
                            ))}
                        </div>
                        <div className="mt-6"><Button onClick={async () => { try { await notificationAPI.updatePreferences(notifPrefs); toast.success('Gespeichert'); } catch { toast.error('Fehler'); } }} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-notif-prefs-btn">{t('notif_save')}</Button></div>
                    </div>
                )}

                {/* Timeline / History */}
                {showTimeline && (
                    <div className="mt-6 bg-card border border-border rounded-lg p-6 sm:p-8 animate-fadeIn" data-testid="timeline-panel">
                        <div className="flex items-center gap-3 mb-6">
                            <ClockCounterClockwise size={24} className="text-[#114f55]" />
                            <h2 className="text-xl font-bold tracking-tight text-foreground">Verlauf</h2>
                        </div>
                        {history.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-6">Noch keine Aktivitäten vorhanden. Starten Sie mit dem ersten Schritt!</p>
                        ) : (
                            <div className="relative">
                                <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
                                <div className="space-y-0">
                                    {history.map((entry, idx) => {
                                        const isCompleted = entry.action === 'completed';
                                        const isInProgress = entry.action === 'in_progress';
                                        return (
                                            <div key={idx} className="relative flex items-start gap-4 py-3" data-testid={`timeline-entry-${idx}`}>
                                                <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                                                    isCompleted ? 'bg-green-500 text-white' : isInProgress ? 'bg-[#114f55] text-white' : 'bg-muted text-muted-foreground'
                                                }`}>
                                                    {isCompleted ? <Check size={14} /> : isInProgress ? <ArrowRight size={14} /> : <ClockCounterClockwise size={14} />}
                                                </div>
                                                <div className="flex-1 min-w-0 pt-1">
                                                    <div className="flex items-center gap-2 flex-wrap">
                                                        <span className="font-medium text-sm text-foreground">{entry.step_title}</span>
                                                        <span className={`px-2 py-0.5 text-xs rounded-sm font-medium ${
                                                            isCompleted ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                                                            isInProgress ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                                                            'bg-muted text-muted-foreground'
                                                        }`}>
                                                            {isCompleted ? 'Abgeschlossen' : isInProgress ? 'In Bearbeitung' : entry.action}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        Schritt {entry.step_order} &middot; {new Date(entry.timestamp).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                                    </p>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
