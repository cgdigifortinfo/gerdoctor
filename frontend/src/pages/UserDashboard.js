import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { stepsAPI, profileAPI, partnersAPI, filesAPI, notificationAPI, formatApiError } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { Switch } from '../components/ui/switch';
import { 
    SignOut, Check, ArrowRight, ArrowLeft, User, Buildings, 
    FileText, CloudArrowUp, X, CaretRight, Bell, GearSix,
    Plus, Trash, WarningCircle, CheckCircle, SkipForward
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { ThemeLangToggle } from '../components/ThemeLangToggle';

export default function UserDashboard() {
    const { user, logout } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const [steps, setSteps] = useState([]);
    const [progress, setProgress] = useState([]);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [partners, setPartners] = useState([]);
    const [selectedPartner, setSelectedPartner] = useState(null);
    const [formData, setFormData] = useState({});
    const [uploadedFiles, setUploadedFiles] = useState({});
    const [submitting, setSubmitting] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [notifPrefs, setNotifPrefs] = useState({
        email_on_step_enter: true, email_on_step_edit: false, email_on_step_leave: true
    });

    const loadData = useCallback(async () => {
        try {
            const [stepsRes, progressRes, notifRes] = await Promise.all([
                stepsAPI.getAll(),
                stepsAPI.getProgress(),
                notificationAPI.getPreferences().catch(() => ({ data: { email_on_step_enter: true, email_on_step_edit: false, email_on_step_leave: true } }))
            ]);
            setSteps(stepsRes.data);
            setProgress(progressRes.data);
            setNotifPrefs(notifRes.data);

            const progressMap = {};
            progressRes.data.forEach(p => { progressMap[p.step_id] = p; });

            let currentIdx = 0;
            for (let i = 0; i < stepsRes.data.length; i++) {
                const sp = progressMap[stepsRes.data[i].id];
                if (!sp || sp.status !== 'completed') { currentIdx = i; break; }
                currentIdx = i;
            }
            setCurrentStepIndex(currentIdx);

            const currentProgress = progressMap[stepsRes.data[currentIdx]?.id];
            if (currentProgress?.data) setFormData(currentProgress.data);

            // Load partners for partner_selection steps
            const currentStep = stepsRes.data[currentIdx];
            if (currentStep?.step_type === 'partner_selection') {
                const tag = currentStep.filter_tag || '';
                const pRes = await partnersAPI.getAll(tag);
                setPartners(pRes.data);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    // Load partners when step changes to partner_selection
    useEffect(() => {
        const currentStep = steps[currentStepIndex];
        if (currentStep?.step_type === 'partner_selection') {
            const tag = currentStep.filter_tag || '';
            partnersAPI.getAll(tag).then(res => setPartners(res.data)).catch(() => {});
        }
    }, [currentStepIndex, steps]);

    const handleLogout = async () => { await logout(); navigate('/'); };

    const getProgressPercentage = () => {
        if (steps.length === 0) return 0;
        return Math.round((progress.filter(p => p.status === 'completed').length / steps.length) * 100);
    };

    const getStepStatus = (stepId) => {
        return progress.find(p => p.step_id === stepId)?.status || 'pending';
    };

    const handleInputChange = (fieldName, value) => {
        setFormData(prev => ({ ...prev, [fieldName]: value }));
    };

    const handleFileUpload = async (fieldName, file) => {
        try {
            const response = await filesAPI.upload(file);
            setUploadedFiles(prev => ({ ...prev, [fieldName]: response.data }));
            setFormData(prev => ({ ...prev, [fieldName]: response.data.id }));
            toast.success('Datei hochgeladen');
        } catch { toast.error('Fehler beim Hochladen'); }
    };

    // Multiupload handlers
    const handleAddMultiuploadEntry = (fieldName) => {
        const current = formData[fieldName] || [];
        setFormData(prev => ({ ...prev, [fieldName]: [...current, { file_id: '', document_type: '' }] }));
    };

    const handleRemoveMultiuploadEntry = (fieldName, index) => {
        const current = [...(formData[fieldName] || [])];
        current.splice(index, 1);
        setFormData(prev => ({ ...prev, [fieldName]: current }));
    };

    const handleMultiuploadFileChange = async (fieldName, index, file) => {
        try {
            const response = await filesAPI.upload(file);
            const current = [...(formData[fieldName] || [])];
            current[index] = { ...current[index], file_id: response.data.id, filename: response.data.filename };
            setFormData(prev => ({ ...prev, [fieldName]: current }));
            toast.success('Datei hochgeladen');
        } catch { toast.error('Fehler beim Hochladen'); }
    };

    const handleMultiuploadTypeChange = (fieldName, index, docType) => {
        const current = [...(formData[fieldName] || [])];
        current[index] = { ...current[index], document_type: docType };
        setFormData(prev => ({ ...prev, [fieldName]: current }));
    };

    const handleStepSubmit = async (markComplete = false) => {
        const currentStep = steps[currentStepIndex];
        if (!currentStep) return;
        setSubmitting(true);
        try {
            const status = markComplete ? 'completed' : 'in_progress';
            await stepsAPI.updateProgress(currentStep.id, status, formData);
            if (markComplete) {
                toast.success('Schritt abgeschlossen!');
                if (currentStepIndex < steps.length - 1) {
                    setCurrentStepIndex(currentStepIndex + 1);
                    setFormData({});
                    setSelectedPartner(null);
                }
            } else {
                toast.success('Fortschritt gespeichert');
            }
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
                setCurrentStepIndex(currentStepIndex + 1);
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

    const handlePartnerSubmission = async () => {
        if (!selectedPartner) { toast.error('Bitte wählen Sie einen Partner'); return; }
        setSubmitting(true);
        try {
            await partnersAPI.submit(selectedPartner.id, formData);
            toast.success('An Partner übermittelt!');
            await handleStepSubmit(true);
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSubmitting(false); }
    };

    // Render form fields
    const renderFormField = (field) => {
        const value = formData[field.name] || '';

        if (field.field_type === 'selectbox' || field.field_type === 'select') {
            return (
                <div key={field.name} className="space-y-2">
                    <Label className="text-foreground">
                        {field.label} {field.required && <span className="text-red-500">*</span>}
                    </Label>
                    <Select value={value} onValueChange={(val) => handleInputChange(field.name, val)}>
                        <SelectTrigger className="border-border rounded-sm" data-testid={`form-field-${field.name}`}>
                            <SelectValue placeholder={field.placeholder || 'Bitte wählen...'} />
                        </SelectTrigger>
                        <SelectContent>
                            {field.options?.map(opt => (
                                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            );
        }

        if (field.field_type === 'multiupload') {
            const entries = formData[field.name] || [];
            return (
                <div key={field.name} className="space-y-3">
                    <Label className="text-foreground">
                        {field.label} {field.required && <span className="text-red-500">*</span>}
                    </Label>
                    {entries.map((entry, idx) => (
                        <div key={idx} className="flex flex-col sm:flex-row gap-2 p-3 bg-muted rounded-sm border border-border" data-testid={`multiupload-entry-${idx}`}>
                            <div className="flex-1">
                                <Select value={entry.document_type} onValueChange={(val) => handleMultiuploadTypeChange(field.name, idx, val)}>
                                    <SelectTrigger className="border-border rounded-sm text-sm h-9">
                                        <SelectValue placeholder="Dokumenttyp wählen..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {field.options?.map(opt => (
                                            <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="flex-1">
                                {entry.file_id ? (
                                    <div className="flex items-center gap-2 h-9 px-3 bg-card border border-border rounded-sm text-sm">
                                        <Check size={14} className="text-green-600" />
                                        <span className="truncate">{entry.filename || 'Hochgeladen'}</span>
                                    </div>
                                ) : (
                                    <div className="relative">
                                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => e.target.files[0] && handleMultiuploadFileChange(field.name, idx, e.target.files[0])} />
                                        <div className="flex items-center gap-2 h-9 px-3 border border-dashed border-border rounded-sm text-sm text-muted-foreground cursor-pointer hover:border-[#114f55]">
                                            <CloudArrowUp size={16} /> Datei auswählen
                                        </div>
                                    </div>
                                )}
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => handleRemoveMultiuploadEntry(field.name, idx)} className="text-red-500 h-9 w-9 p-0 flex-shrink-0">
                                <Trash size={16} />
                            </Button>
                        </div>
                    ))}
                    <Button type="button" variant="outline" size="sm" onClick={() => handleAddMultiuploadEntry(field.name)} className="border-border" data-testid={`add-multiupload-${field.name}`}>
                        <Plus size={16} className="mr-1" /> Dokument hinzufügen
                    </Button>
                </div>
            );
        }

        if (field.field_type === 'textarea') {
            return (
                <div key={field.name} className="space-y-2">
                    <Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label>
                    <Textarea value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} placeholder={field.placeholder} className="border-border rounded-sm min-h-[100px]" required={field.required} data-testid={`form-field-${field.name}`} />
                </div>
            );
        }

        if (field.field_type === 'file') {
            return (
                <div key={field.name} className="space-y-2">
                    <Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label>
                    <div className="dropzone p-6 rounded-sm text-center cursor-pointer">
                        <input type="file" id={field.name} className="hidden" onChange={(e) => e.target.files[0] && handleFileUpload(field.name, e.target.files[0])} data-testid={`form-field-${field.name}`} />
                        <label htmlFor={field.name} className="cursor-pointer">
                            {uploadedFiles[field.name] ? (
                                <div className="flex items-center justify-center gap-2 text-[#114f55]"><Check size={20} /><span>{uploadedFiles[field.name].filename}</span></div>
                            ) : (
                                <div className="flex flex-col items-center gap-2 text-muted-foreground"><CloudArrowUp size={32} /><span>Klicken zum Hochladen</span></div>
                            )}
                        </label>
                    </div>
                </div>
            );
        }

        if (field.field_type === 'date') {
            return (
                <div key={field.name} className="space-y-2">
                    <Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label>
                    <Input type="date" value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} className="border-border rounded-sm" required={field.required} data-testid={`form-field-${field.name}`} />
                </div>
            );
        }

        // Default: text, email, phone
        return (
            <div key={field.name} className="space-y-2">
                <Label className="text-foreground">{field.label} {field.required && <span className="text-red-500">*</span>}</Label>
                <Input type={field.field_type === 'phone' ? 'tel' : field.field_type === 'email' ? 'email' : 'text'} value={value} onChange={(e) => handleInputChange(field.name, e.target.value)} placeholder={field.placeholder} className="border-border rounded-sm" required={field.required} data-testid={`form-field-${field.name}`} />
            </div>
        );
    };

    // Render step content based on type
    const renderStepContent = () => {
        const currentStep = steps[currentStepIndex];
        if (!currentStep) return null;
        const stepStatus = getStepStatus(currentStep.id);

        switch (currentStep.step_type) {
            case 'form':
                return (
                    <div className="space-y-6">
                        {currentStep.fields?.map(renderFormField)}
                        <div className="flex flex-wrap gap-3 pt-4">
                            <Button variant="outline" onClick={() => handleStepSubmit(false)} disabled={submitting} className="border-border" data-testid="save-progress-btn">
                                {t('dash_save_progress')}
                            </Button>
                            <Button onClick={() => handleStepSubmit(true)} disabled={submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="complete-step-btn">
                                {submitting ? t('dash_saving') : t('dash_complete_continue')} <ArrowRight className="ml-2" size={16} />
                            </Button>
                        </div>
                    </div>
                );

            case 'partner_selection':
                return (
                    <div className="space-y-6">
                        {currentStep.filter_tag && (
                            <div className="inline-block px-3 py-1 text-xs font-medium bg-[#114f55]/10 text-[#114f55] rounded-sm">
                                Filter: {currentStep.filter_tag}
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {partners.map(partner => (
                                <div key={partner.id} onClick={() => handlePartnerSelect(partner)}
                                    className={`partner-card p-6 rounded-sm cursor-pointer transition-all ${selectedPartner?.id === partner.id ? 'border-[#114f55] border-2 bg-[#114f55]/5' : 'bg-card'}`}
                                    data-testid={`partner-select-${partner.id}`}>
                                    <div className="flex items-start gap-4">
                                        {partner.logo_url && <img src={partner.logo_url} alt={partner.name} className="w-12 h-12 object-cover rounded-sm" />}
                                        <div className="flex-1">
                                            <h3 className="font-semibold text-foreground">{partner.name}</h3>
                                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{partner.description}</p>
                                            {partner.tags?.map(tag => (
                                                <span key={tag} className="inline-block mt-2 mr-1 px-2 py-1 text-xs bg-muted text-muted-foreground rounded-sm">{tag}</span>
                                            ))}
                                        </div>
                                        {selectedPartner?.id === partner.id && <Check size={24} className="text-[#114f55]" />}
                                    </div>
                                </div>
                            ))}
                            {partners.length === 0 && (
                                <div className="col-span-2 text-center py-8 text-muted-foreground">Keine Partner für diese Kategorie verfügbar</div>
                            )}
                        </div>
                        <div className="flex flex-wrap gap-3 pt-4">
                            <Button onClick={handlePartnerSubmission} disabled={!selectedPartner || submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="confirm-partner-btn">
                                {submitting ? t('dash_saving') : t('dash_confirm_selection')} <ArrowRight className="ml-2" size={16} />
                            </Button>
                            {currentStep.skippable && (
                                <Button variant="outline" onClick={handleSkipStep} disabled={submitting} className="border-border text-muted-foreground" data-testid="skip-step-btn">
                                    <SkipForward size={16} className="mr-1" /> {currentStep.skip_label || 'Überspringen'}
                                </Button>
                            )}
                        </div>
                    </div>
                );

            case 'milestone':
                return (
                    <div className="space-y-6">
                        {stepStatus === 'completed' ? (
                            <div className="p-8 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-sm text-center">
                                <CheckCircle size={48} className="mx-auto text-green-600 mb-4" />
                                <p className="text-lg font-semibold text-green-800 dark:text-green-300">
                                    {currentStep.complete_message || 'Alles erledigt!'}
                                </p>
                                <Button onClick={() => { if (currentStepIndex < steps.length - 1) setCurrentStepIndex(currentStepIndex + 1); }}
                                    className="mt-6 bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="milestone-next-btn">
                                    Weiter <ArrowRight className="ml-2" size={16} />
                                </Button>
                            </div>
                        ) : (
                            <div className="p-8 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-sm text-center">
                                <WarningCircle size={48} className="mx-auto text-yellow-600 mb-4" />
                                <p className="text-lg font-semibold text-yellow-800 dark:text-yellow-300">
                                    {currentStep.pending_message || 'Warten auf Abschluss...'}
                                </p>
                                <p className="text-sm text-muted-foreground mt-2">Dieser Schritt wird von Ihrem Partner bearbeitet.</p>
                            </div>
                        )}
                    </div>
                );

            case 'display':
                return (
                    <div className="space-y-6">
                        {currentStep.pending_message && (
                            <div className="p-6 bg-muted rounded-sm border border-border">
                                <p className="text-foreground">{currentStep.pending_message}</p>
                            </div>
                        )}
                        <div className="flex flex-wrap gap-3">
                            {currentStep.action_label && (
                                <Button onClick={() => handleStepSubmit(true)} disabled={submitting}
                                    className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="display-action-btn">
                                    {currentStep.action_label} <ArrowRight className="ml-2" size={16} />
                                </Button>
                            )}
                            {!currentStep.action_label && (
                                <Button onClick={() => handleStepSubmit(true)} disabled={submitting}
                                    className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="display-next-btn">
                                    Weiter <ArrowRight className="ml-2" size={16} />
                                </Button>
                            )}
                        </div>
                    </div>
                );

            case 'info':
                return (
                    <div className="space-y-6">
                        <div className="p-6 bg-muted rounded-sm border border-border">
                            <p className="text-muted-foreground">{currentStep.description}</p>
                        </div>
                        <Button onClick={() => handleStepSubmit(true)} disabled={submitting} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="finalize-btn">
                            {submitting ? t('dash_finalizing') : t('dash_finalize')} <Check className="ml-2" size={16} />
                        </Button>
                    </div>
                );

            default:
                return <p>Unbekannter Schritttyp</p>;
        }
    };

    if (loading) {
        return <div className="min-h-screen bg-background flex items-center justify-center"><div className="text-muted-foreground">{t('loading')}</div></div>;
    }

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <Link to="/" className="font-black text-xl tracking-tight text-foreground">GuidedJourney</Link>
                        <div className="flex items-center gap-3">
                            <span className="text-sm text-muted-foreground hidden sm:block">{t('dash_welcome')}, {user?.name}</span>
                            <ThemeLangToggle />
                            <Button variant="ghost" size="sm" onClick={() => setShowSettings(!showSettings)} className="text-muted-foreground" data-testid="settings-btn"><GearSix size={20} /></Button>
                            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground" data-testid="logout-btn"><SignOut size={20} /></Button>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Progress Bar */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-2">
                        <h2 className="text-lg font-semibold text-foreground">{t('dash_your_progress')}</h2>
                        <span className="text-sm text-muted-foreground">{getProgressPercentage()}% {t('dash_complete')}</span>
                    </div>
                    <Progress value={getProgressPercentage()} className="h-2" />
                </div>

                {/* Steps Navigation */}
                <div className="mb-6 overflow-x-auto">
                    <div className="flex items-center gap-2 pb-2 min-w-max">
                        {steps.map((step, index) => {
                            const status = getStepStatus(step.id);
                            const isActive = index === currentStepIndex;
                            const isCompleted = status === 'completed';
                            const canNavigate = isCompleted || index <= currentStepIndex;
                            return (
                                <div key={step.id} className="flex items-center">
                                    <button onClick={() => canNavigate && setCurrentStepIndex(index)} disabled={!canNavigate}
                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-sm transition-colors text-sm ${
                                            isActive ? 'bg-[#114f55] text-white' : isCompleted ? 'bg-green-500 text-white' : 'bg-muted text-muted-foreground'
                                        } ${canNavigate ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
                                        data-testid={`step-nav-${index}`}>
                                        <span className="w-5 h-5 rounded-full border-2 border-current flex items-center justify-center text-xs font-bold">
                                            {isCompleted ? <Check size={10} /> : index + 1}
                                        </span>
                                        <span className="hidden lg:block">{step.title}</span>
                                    </button>
                                    {index < steps.length - 1 && <CaretRight size={16} className="mx-1 text-muted-foreground" />}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Current Step Content */}
                <div className="bg-card border border-border rounded-sm p-6 sm:p-8">
                    {steps[currentStepIndex] && (
                        <>
                            <div className="mb-6">
                                <h1 className="text-2xl font-bold tracking-tight text-foreground mb-2">{steps[currentStepIndex].title}</h1>
                                <p className="text-muted-foreground">{steps[currentStepIndex].description}</p>
                            </div>
                            {renderStepContent()}
                        </>
                    )}
                    {currentStepIndex > 0 && (
                        <div className="mt-8 pt-6 border-t border-border">
                            <Button variant="ghost" onClick={() => setCurrentStepIndex(currentStepIndex - 1)} className="text-muted-foreground" data-testid="prev-step-btn">
                                <ArrowLeft className="mr-2" size={16} /> {t('dash_prev_step')}
                            </Button>
                        </div>
                    )}
                </div>

                {/* Notification Settings */}
                {showSettings && (
                    <div className="mt-6 bg-card border border-border rounded-sm p-6 sm:p-8 animate-fadeIn">
                        <div className="flex items-center gap-3 mb-6"><Bell size={24} className="text-[#114f55]" /><h2 className="text-xl font-bold tracking-tight text-foreground">{t('notif_title')}</h2></div>
                        <p className="text-sm text-muted-foreground mb-6">{t('notif_desc')}</p>
                        <div className="space-y-4">
                            {[['email_on_step_enter', 'notif_step_enter', 'notif_step_enter_desc'], ['email_on_step_edit', 'notif_step_edit', 'notif_step_edit_desc'], ['email_on_step_leave', 'notif_step_leave', 'notif_step_leave_desc']].map(([key, titleKey, descKey]) => (
                                <div key={key} className="flex items-center justify-between p-4 bg-muted rounded-sm">
                                    <div><p className="font-medium text-foreground">{t(titleKey)}</p><p className="text-sm text-muted-foreground">{t(descKey)}</p></div>
                                    <Switch checked={notifPrefs[key]} onCheckedChange={(val) => setNotifPrefs(prev => ({ ...prev, [key]: val }))} data-testid={`notif-${key}`} />
                                </div>
                            ))}
                        </div>
                        <div className="mt-6">
                            <Button onClick={async () => { try { await notificationAPI.updatePreferences(notifPrefs); toast.success(t('notif_save') + ' ✓'); } catch { toast.error('Fehler'); } }}
                                className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-notif-prefs-btn">{t('notif_save')}</Button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
