import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { stepsAPI, partnersAPI, filesAPI, notificationAPI, formatApiError } from '../lib/api';
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
    if (conditions.length === 0) return { allowed: true, blocked: false, message: '', redirectStep: null };
    for (const cond of conditions) {
        const result = evaluateCondition(cond, allStepData);
        if (result) {
            if (cond.action === 'block') return { allowed: false, blocked: true, message: cond.message || 'Dieser Schritt ist gesperrt.', redirectStep: null };
            if (cond.action === 'allow_next') return { allowed: true, blocked: false, message: cond.message || '', redirectStep: null };
            if (cond.action === 'redirect') return { allowed: true, blocked: false, message: cond.message || '', redirectStep: cond.target_step_order };
        }
    }
    return { allowed: true, blocked: false, message: '', redirectStep: null };
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

export default function UserDashboard() {
    const { user, logout, impersonating, stopImpersonation } = useAuth();
    const { t } = useLanguage();
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
    const stepRefs = useRef({});
    const containerRef = useRef(null);
    const desktopStepRefs = useRef({});

    const loadData = useCallback(async () => {
        try {
            const [stepsRes, progressRes, allDataRes, notifRes, historyRes, estRes] = await Promise.all([
                stepsAPI.getAll(), stepsAPI.getProgress(), stepsAPI.getAllData(),
                notificationAPI.getPreferences().catch(() => ({ data: { email_on_step_enter: true, email_on_step_edit: false, email_on_step_leave: true } })),
                stepsAPI.getHistory().catch(() => ({ data: [] })),
                stepsAPI.getEstimatedCompletion().catch(() => ({ data: { estimated_completion: null } }))
            ]);
            setSteps(stepsRes.data);
            setProgress(progressRes.data);
            setAllStepData(allDataRes.data);
            setNotifPrefs(notifRes.data);
            setHistory(historyRes.data);
            setEstimatedCompletion(estRes.data?.estimated_completion || null);

            const progressMap = {};
            progressRes.data.forEach(p => { progressMap[p.step_id] = p; });

            let currentIdx = 0;
            for (let i = 0; i < stepsRes.data.length; i++) {
                const sp = progressMap[stepsRes.data[i].id];
                if (!sp || sp.status !== 'completed') { currentIdx = i; break; }
                if (i === stepsRes.data.length - 1) currentIdx = i;
            }
            setCurrentStepIndex(currentIdx);
            setExpandedStep(currentIdx);

            const currentProgress = progressMap[stepsRes.data[currentIdx]?.id];
            if (currentProgress?.data && Object.keys(currentProgress.data).length > 0) {
                setFormData(currentProgress.data);
            } else {
                const prefilled = applyFieldMappings(stepsRes.data[currentIdx] || {}, allDataRes.data);
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
        const currentStep = steps[currentStepIndex];
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
    }, [currentStepIndex, steps, allStepData, progress]);

    const handleLogout = async () => { await logout(); navigate('/'); };
    const getProgressPercentage = () => {
        if (steps.length === 0) return 0;
        const countable = steps.filter(s => s.duration_value > 0);
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
        const currentStep = steps[currentStepIndex];
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

    const handleStepSubmit = async (markComplete = false) => {
        const currentStep = steps[currentStepIndex];
        if (!currentStep) return;
        if (markComplete && !validateStep()) { toast.error('Bitte füllen Sie alle Pflichtfelder aus'); return; }
        setSubmitting(true);
        try {
            const status = markComplete ? 'completed' : 'in_progress';
            await stepsAPI.updateProgress(currentStep.id, status, formData);
            if (markComplete) {
                toast.success('Schritt abgeschlossen!');
                if (currentStepIndex < steps.length - 1) {
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

    const handleSkipStep = async () => {
        const currentStep = steps[currentStepIndex];
        if (!currentStep) return;
        setSubmitting(true);
        try {
            await stepsAPI.updateProgress(currentStep.id, 'completed', { skipped: true });
            toast.success('Schritt übersprungen');
            if (currentStepIndex < steps.length - 1) {
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
        const step = steps[idx];
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
        const step = steps[idx];
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

        if (field.field_type === 'selectbox' || field.field_type === 'select') {
            return (
                <div key={field.name} className="space-y-2">
                    <Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label>
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
                    <Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label>
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
            return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label><Textarea value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} placeholder={field.placeholder} className={`border-border rounded-sm min-h-[100px] ${hasError ? 'border-red-500' : ''}`} data-testid={`form-field-${field.name}`} /></div>);
        }
        if (field.field_type === 'file') {
            return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label><div className="dropzone p-6 rounded-sm text-center cursor-pointer"><input type="file" id={field.name} className="hidden" onChange={(e) => e.target.files[0] && handleFileUpload(field.name, e.target.files[0])} data-testid={`form-field-${field.name}`} /><label htmlFor={field.name} className="cursor-pointer">{uploadedFiles[field.name] ? <div className="flex items-center justify-center gap-2 text-[#114f55]"><Check size={20} /><span>{uploadedFiles[field.name].filename}</span></div> : <div className="flex flex-col items-center gap-2 text-muted-foreground"><CloudArrowUp size={32} /><span>Klicken zum Hochladen</span></div>}</label></div></div>);
        }
        if (field.field_type === 'date') {
            return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label><Input type="date" value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} className={`border-border rounded-sm ${hasError ? 'border-red-500' : ''}`} data-testid={`form-field-${field.name}`} /></div>);
        }
        return (<div key={field.name} className="space-y-2"><Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label><Input type={field.field_type === 'phone' ? 'tel' : field.field_type === 'email' ? 'email' : 'text'} value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} placeholder={field.placeholder} className={`border-border rounded-sm ${hasError ? 'border-red-500' : ''}`} data-testid={`form-field-${field.name}`} /></div>);
    };

    const renderStepContent = () => {
        const currentStep = steps[currentStepIndex];
        if (!currentStep) return null;
        const stepStatus = getStepStatus(currentStep.id);
        const condResult = allStepData.length > 0 ? evaluateStepConditions(currentStep, allStepData) : { allowed: true, blocked: false, message: '' };
        if (condResult.blocked) {
            return (
                <div className="p-8 bg-muted border border-border rounded-sm text-center">
                    <Lock size={48} className="mx-auto text-muted-foreground mb-4" />
                    <p className="text-lg font-semibold text-foreground">{condResult.message}</p>
                </div>
            );
        }

        switch (currentStep.step_type) {
            case 'form':
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
                            <Button onClick={() => handleStepSubmit(true)} disabled={submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="complete-step-btn">{submitting ? t('dash_saving') : t('dash_complete_continue')} <ArrowRight className="ml-2" size={16} /></Button>
                        </div>
                    </div>
                );
            case 'partner_selection': {
                const partnerTags = [...new Set(partners.flatMap(p => p.tags || []))].sort();
                const filteredPartners = partnerTagFilter && partnerTagFilter !== 'all'
                    ? partners.filter(p => (p.tags || []).includes(partnerTagFilter) || p.category === partnerTagFilter)
                    : partners;
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
                                <div key={partner.id} onClick={() => handlePartnerSelect(partner)} className={`partner-card p-6 rounded-sm cursor-pointer transition-all ${selectedPartner?.id === partner.id ? 'border-[#114f55] border-2 bg-[#114f55]/5' : 'bg-card'}`} data-testid={`partner-select-${partner.id}`}>
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
                            {currentStep.skippable && <Button variant="outline" onClick={handleSkipStep} disabled={submitting} className="border-border text-muted-foreground" data-testid="skip-step-btn"><SkipForward size={16} className="mr-1" /> {currentStep.skip_label || 'Ueberspringen'}</Button>}
                        </div>
                    </div>
                );
            }
            case 'partner_multiselection': {
                const multiTags = [...new Set(partners.flatMap(p => p.tags || []).concat(partners.map(p => p.category).filter(Boolean)))].sort();
                const filteredMultiPartners = partnerTagFilter && partnerTagFilter !== 'all'
                    ? partners.filter(p => (p.tags || []).includes(partnerTagFilter) || p.category === partnerTagFilter)
                    : partners;
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
                                    <div key={partner.id} onClick={() => handleToggleMultiPartner(partner)} className={`partner-card p-6 rounded-sm cursor-pointer transition-all ${isSelected ? 'border-[#114f55] border-2 bg-[#114f55]/5' : 'bg-card'}`} data-testid={`partner-multiselect-${partner.id}`}>
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
                            {currentStep.skippable && <Button variant="outline" onClick={handleSkipStep} disabled={submitting} className="border-border text-muted-foreground" data-testid="skip-step-btn"><SkipForward size={16} className="mr-1" /> {currentStep.skip_label || 'Ueberspringen'}</Button>}
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
                                <p className="text-lg font-semibold text-green-800 dark:text-green-300">{currentStep.complete_message || 'Alles erledigt!'}</p>
                                <Button onClick={() => { if (currentStepIndex < steps.length - 1) { setCurrentStepIndex(currentStepIndex + 1); setExpandedStep(currentStepIndex + 1); } }} className="mt-6 bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="milestone-next-btn">Weiter <ArrowRight className="ml-2" size={16} /></Button>
                            </div>
                        ) : (
                            <div className="p-8 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-sm text-center">
                                <WarningCircle size={48} className="mx-auto text-yellow-600 mb-4" />
                                <p className="text-lg font-semibold text-yellow-800 dark:text-yellow-300">{currentStep.pending_message || 'Warten auf Abschluss...'}</p>
                                <p className="text-sm text-muted-foreground mt-2">Dieser Schritt wird von Ihrem Partner bearbeitet.</p>
                            </div>
                        )}
                    </div>
                );
            case 'display':
                return (
                    <div className="space-y-6">
                        {currentStep.pending_message && <div className="p-6 bg-muted rounded-sm border border-border"><p className="text-foreground">{currentStep.pending_message}</p></div>}
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
                            {currentStep.action_label ? (
                                <Button onClick={() => handleStepSubmit(true)} disabled={submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="display-action-btn">{currentStep.action_label} <ArrowRight className="ml-2" size={16} /></Button>
                            ) : (
                                <Button onClick={() => handleStepSubmit(true)} disabled={submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="display-next-btn">Weiter <ArrowRight className="ml-2" size={16} /></Button>
                            )}
                        </div>
                    </div>
                );
            default:
                return <p>Unbekannter Schritttyp</p>;
        }
    };

    if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><div className="text-muted-foreground">{t('loading')}</div></div>;

    const completedCount = progress.filter(p => p.status === 'completed').length;
    const mobileProgress = steps.length === 0 ? 0 : Math.round((completedCount / steps.length) * 100);

    return (
        <div className="min-h-screen bg-background">
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <Logo />
                        <div className="flex items-center gap-3">
                            {/* Estimated completion in header */}
                            {estimatedCompletion && (
                                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-[#114f55] text-white rounded-full" data-testid="estimated-completion-banner">
                                    <CalendarCheck size={16} weight="bold" />
                                    <div className="flex items-baseline gap-1.5">
                                        <span className="text-xs opacity-80">Abschluss</span>
                                        <span className="text-sm font-bold" data-testid="estimated-completion-date">
                                            {new Date(estimatedCompletion).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                                        </span>
                                    </div>
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
                    {/* Mobile estimated completion */}
                    {estimatedCompletion && (
                        <div className="sm:hidden flex items-center gap-2 pb-3 -mt-1" data-testid="estimated-completion-banner-mobile">
                            <CalendarCheck size={14} className="text-[#114f55]" />
                            <span className="text-xs text-muted-foreground">Abschluss</span>
                            <span className="text-xs font-bold text-[#114f55]" data-testid="estimated-completion-date-mobile">
                                {new Date(estimatedCompletion).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                            </span>
                        </div>
                    )}
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" ref={containerRef}>
                {/* ====== DESKTOP: Horizontal Step Cards in single row ====== */}
                <div className="hidden md:block mb-8">
                    <div className="rounded-lg overflow-hidden overflow-x-auto shadow-sm border border-border">
                        <div className="flex min-w-max">
                            {steps.map((step, index) => {
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
                                            ${index < steps.length - 1 ? 'border-r border-border' : ''}
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
                                            <span className={`text-sm font-semibold ${isActive ? 'text-[#114f55]' : 'text-foreground'}`}>{step.title}</span>
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
                            {steps.map((step, index) => {
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
                                                    {step.title}
                                                </p>
                                                {!isExpanded && (
                                                    <p className="text-xs text-muted-foreground truncate">{step.description}</p>
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
                                                    <p className="text-sm text-muted-foreground mb-4">{step.description}</p>
                                                    {isActive && renderStepContent()}
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
                        {steps[currentStepIndex] && (
                            <>
                                <div className="mb-6">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className="w-8 h-8 rounded-full bg-[#114f55] text-white flex items-center justify-center text-sm font-bold">
                                            {currentStepIndex + 1}
                                        </div>
                                        <h1 className="text-2xl font-bold tracking-tight text-foreground">{steps[currentStepIndex].title}</h1>
                                    </div>
                                    <p className="text-muted-foreground ml-11">{steps[currentStepIndex].description}</p>
                                </div>
                                {renderStepContent()}
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
