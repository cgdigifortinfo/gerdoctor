import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
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
    FileText, CloudArrowUp, X, CaretRight, Bell, GearSix
} from '@phosphor-icons/react';
import { toast } from 'sonner';

export default function UserDashboard() {
    const { user, logout } = useAuth();
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
        email_on_step_enter: true,
        email_on_step_edit: false,
        email_on_step_leave: true
    });

    const loadData = useCallback(async () => {
        try {
            const [stepsRes, progressRes, partnersRes, notifRes] = await Promise.all([
                stepsAPI.getAll(),
                stepsAPI.getProgress(),
                partnersAPI.getAll(),
                notificationAPI.getPreferences().catch(() => ({ data: { email_on_step_enter: true, email_on_step_edit: false, email_on_step_leave: true } }))
            ]);
            setSteps(stepsRes.data);
            setProgress(progressRes.data);
            setPartners(partnersRes.data);
            setNotifPrefs(notifRes.data);
            
            // Find current step based on progress
            const progressMap = {};
            progressRes.data.forEach(p => {
                progressMap[p.step_id] = p;
            });
            
            // Find first incomplete step
            let currentIdx = 0;
            for (let i = 0; i < stepsRes.data.length; i++) {
                const stepProgress = progressMap[stepsRes.data[i].id];
                if (!stepProgress || stepProgress.status !== 'completed') {
                    currentIdx = i;
                    break;
                }
                currentIdx = i;
            }
            setCurrentStepIndex(currentIdx);
            
            // Load existing form data for current step
            const currentProgress = progressMap[stepsRes.data[currentIdx]?.id];
            if (currentProgress?.data) {
                setFormData(currentProgress.data);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load progress data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const getProgressPercentage = () => {
        if (steps.length === 0) return 0;
        const completedCount = progress.filter(p => p.status === 'completed').length;
        return Math.round((completedCount / steps.length) * 100);
    };

    const getStepStatus = (stepId) => {
        const stepProgress = progress.find(p => p.step_id === stepId);
        return stepProgress?.status || 'pending';
    };

    const handleInputChange = (fieldName, value) => {
        setFormData(prev => ({ ...prev, [fieldName]: value }));
    };

    const handleFileUpload = async (fieldName, file) => {
        try {
            const response = await filesAPI.upload(file);
            setUploadedFiles(prev => ({ ...prev, [fieldName]: response.data }));
            setFormData(prev => ({ ...prev, [fieldName]: response.data.id }));
            toast.success('File uploaded successfully');
        } catch (error) {
            toast.error('Failed to upload file');
        }
    };

    const handleStepSubmit = async (markComplete = false) => {
        const currentStep = steps[currentStepIndex];
        if (!currentStep) return;

        setSubmitting(true);
        try {
            const status = markComplete ? 'completed' : 'in_progress';
            await stepsAPI.updateProgress(currentStep.id, status, formData);
            
            if (markComplete) {
                toast.success('Step completed!');
                if (currentStepIndex < steps.length - 1) {
                    setCurrentStepIndex(currentStepIndex + 1);
                    setFormData({});
                }
            } else {
                toast.success('Progress saved');
            }
            
            await loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        } finally {
            setSubmitting(false);
        }
    };

    const handlePartnerSelect = (partner) => {
        setSelectedPartner(partner);
        setFormData(prev => ({ ...prev, selected_partner_id: partner.id }));
    };

    const handlePartnerSubmission = async () => {
        if (!selectedPartner) {
            toast.error('Please select a partner');
            return;
        }

        setSubmitting(true);
        try {
            await partnersAPI.submit(selectedPartner.id, formData);
            toast.success('Submitted to partner successfully!');
            await handleStepSubmit(true);
        } catch (error) {
            toast.error(formatApiError(error));
        } finally {
            setSubmitting(false);
        }
    };

    const renderFormField = (field) => {
        const value = formData[field.name] || '';
        
        switch (field.field_type) {
            case 'text':
            case 'email':
            case 'phone':
                return (
                    <div key={field.name} className="space-y-2">
                        <Label htmlFor={field.name} className="text-[#0A0A0A]">
                            {field.label} {field.required && <span className="text-red-500">*</span>}
                        </Label>
                        <Input
                            id={field.name}
                            type={field.field_type === 'phone' ? 'tel' : field.field_type}
                            value={value}
                            onChange={(e) => handleInputChange(field.name, e.target.value)}
                            placeholder={field.placeholder}
                            className="border-[#E4E4E7] rounded-sm"
                            required={field.required}
                            data-testid={`form-field-${field.name}`}
                        />
                    </div>
                );
            case 'textarea':
                return (
                    <div key={field.name} className="space-y-2">
                        <Label htmlFor={field.name} className="text-[#0A0A0A]">
                            {field.label} {field.required && <span className="text-red-500">*</span>}
                        </Label>
                        <Textarea
                            id={field.name}
                            value={value}
                            onChange={(e) => handleInputChange(field.name, e.target.value)}
                            placeholder={field.placeholder}
                            className="border-[#E4E4E7] rounded-sm min-h-[100px]"
                            required={field.required}
                            data-testid={`form-field-${field.name}`}
                        />
                    </div>
                );
            case 'select':
                return (
                    <div key={field.name} className="space-y-2">
                        <Label htmlFor={field.name} className="text-[#0A0A0A]">
                            {field.label} {field.required && <span className="text-red-500">*</span>}
                        </Label>
                        <Select value={value} onValueChange={(val) => handleInputChange(field.name, val)}>
                            <SelectTrigger className="border-[#E4E4E7] rounded-sm" data-testid={`form-field-${field.name}`}>
                                <SelectValue placeholder={field.placeholder || 'Select an option'} />
                            </SelectTrigger>
                            <SelectContent>
                                {field.options?.map((opt) => (
                                    <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                );
            case 'date':
                return (
                    <div key={field.name} className="space-y-2">
                        <Label htmlFor={field.name} className="text-[#0A0A0A]">
                            {field.label} {field.required && <span className="text-red-500">*</span>}
                        </Label>
                        <Input
                            id={field.name}
                            type="date"
                            value={value}
                            onChange={(e) => handleInputChange(field.name, e.target.value)}
                            className="border-[#E4E4E7] rounded-sm"
                            required={field.required}
                            data-testid={`form-field-${field.name}`}
                        />
                    </div>
                );
            case 'file':
                return (
                    <div key={field.name} className="space-y-2">
                        <Label htmlFor={field.name} className="text-[#0A0A0A]">
                            {field.label} {field.required && <span className="text-red-500">*</span>}
                        </Label>
                        <div className="dropzone p-6 rounded-sm text-center cursor-pointer hover:bg-gray-50 transition-colors">
                            <input
                                type="file"
                                id={field.name}
                                className="hidden"
                                onChange={(e) => e.target.files[0] && handleFileUpload(field.name, e.target.files[0])}
                                data-testid={`form-field-${field.name}`}
                            />
                            <label htmlFor={field.name} className="cursor-pointer">
                                {uploadedFiles[field.name] ? (
                                    <div className="flex items-center justify-center gap-2 text-[#114f55]">
                                        <Check size={20} />
                                        <span>{uploadedFiles[field.name].filename}</span>
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center gap-2 text-[#52525B]">
                                        <CloudArrowUp size={32} />
                                        <span>Click to upload or drag and drop</span>
                                    </div>
                                )}
                            </label>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    const renderStepContent = () => {
        const currentStep = steps[currentStepIndex];
        if (!currentStep) return null;

        switch (currentStep.step_type) {
            case 'form':
                return (
                    <div className="space-y-6">
                        {currentStep.fields?.map(renderFormField)}
                        <div className="flex gap-4 pt-4">
                            <Button
                                variant="outline"
                                onClick={() => handleStepSubmit(false)}
                                disabled={submitting}
                                className="border-[#E4E4E7] text-[#0A0A0A]"
                                data-testid="save-progress-btn"
                            >
                                Save Progress
                            </Button>
                            <Button
                                onClick={() => handleStepSubmit(true)}
                                disabled={submitting}
                                className="bg-[#114f55] hover:bg-[#0d3d42] text-white"
                                data-testid="complete-step-btn"
                            >
                                {submitting ? 'Saving...' : 'Complete & Continue'}
                                <ArrowRight className="ml-2" size={16} />
                            </Button>
                        </div>
                    </div>
                );
            
            case 'partner_selection':
                return (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {partners.map((partner) => (
                                <div
                                    key={partner.id}
                                    onClick={() => handlePartnerSelect(partner)}
                                    className={`partner-card p-6 rounded-sm cursor-pointer transition-all ${
                                        selectedPartner?.id === partner.id 
                                            ? 'border-[#114f55] border-2 bg-teal-50' 
                                            : 'bg-white'
                                    }`}
                                    data-testid={`partner-select-${partner.id}`}
                                >
                                    <div className="flex items-start gap-4">
                                        {partner.logo_url && (
                                            <img 
                                                src={partner.logo_url} 
                                                alt={partner.name}
                                                className="w-12 h-12 object-cover rounded-sm"
                                            />
                                        )}
                                        <div className="flex-1">
                                            <h3 className="font-semibold text-[#0A0A0A]">{partner.name}</h3>
                                            <p className="text-sm text-[#52525B] mt-1 line-clamp-2">{partner.description}</p>
                                            {partner.category && (
                                                <span className="inline-block mt-2 px-2 py-1 text-xs bg-[#FAFAFA] text-[#52525B] rounded-sm">
                                                    {partner.category}
                                                </span>
                                            )}
                                        </div>
                                        {selectedPartner?.id === partner.id && (
                                            <Check size={24} className="text-[#114f55]" />
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                        
                        {selectedPartner && (
                            <div className="bg-[#FAFAFA] p-6 rounded-sm border border-[#E4E4E7]">
                                <h4 className="font-semibold text-[#0A0A0A] mb-2">Selected Partner: {selectedPartner.name}</h4>
                                <p className="text-sm text-[#52525B] mb-4">{selectedPartner.description}</p>
                                {selectedPartner.website && (
                                    <a 
                                        href={selectedPartner.website} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="text-[#114f55] text-sm hover:underline"
                                    >
                                        Visit Website
                                    </a>
                                )}
                            </div>
                        )}

                        <div className="flex gap-4 pt-4">
                            <Button
                                onClick={() => handleStepSubmit(true)}
                                disabled={!selectedPartner || submitting}
                                className="bg-[#114f55] hover:bg-[#0d3d42] text-white"
                                data-testid="confirm-partner-btn"
                            >
                                {submitting ? 'Saving...' : 'Confirm Selection & Continue'}
                                <ArrowRight className="ml-2" size={16} />
                            </Button>
                        </div>
                    </div>
                );
            
            case 'info':
                return (
                    <div className="space-y-6">
                        <div className="bg-[#FAFAFA] p-6 rounded-sm border border-[#E4E4E7]">
                            <h4 className="font-semibold text-[#0A0A0A] mb-4">Review Your Information</h4>
                            <p className="text-[#52525B]">{currentStep.description}</p>
                            
                            <div className="mt-6 space-y-4">
                                {steps.slice(0, currentStepIndex).map((step, idx) => {
                                    const stepProgress = progress.find(p => p.step_id === step.id);
                                    return (
                                        <div key={step.id} className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-[#114f55] flex items-center justify-center">
                                                <Check size={16} className="text-white" />
                                            </div>
                                            <div>
                                                <p className="font-medium text-[#0A0A0A]">{step.title}</p>
                                                <p className="text-sm text-[#52525B]">
                                                    {stepProgress?.status === 'completed' ? 'Completed' : 'In Progress'}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="flex gap-4 pt-4">
                            <Button
                                onClick={() => handleStepSubmit(true)}
                                disabled={submitting}
                                className="bg-[#114f55] hover:bg-[#0d3d42] text-white"
                                data-testid="finalize-btn"
                            >
                                {submitting ? 'Finalizing...' : 'Finalize Journey'}
                                <Check className="ml-2" size={16} />
                            </Button>
                        </div>
                    </div>
                );
            
            default:
                return <p>Unknown step type</p>;
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
                <div className="text-[#52525B]">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FAFAFA]">
            {/* Header */}
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <Link to="/" className="font-black text-xl tracking-tight text-[#0A0A0A]">
                            GuidedJourney
                        </Link>
                        <div className="flex items-center gap-4">
                            <span className="text-sm text-[#52525B] hidden sm:block">
                                Welcome, {user?.name}
                            </span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowSettings(!showSettings)}
                                className="text-[#52525B]"
                                data-testid="settings-btn"
                            >
                                <GearSix size={20} />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleLogout}
                                className="text-[#52525B]"
                                data-testid="logout-btn"
                            >
                                <SignOut size={20} />
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Progress Bar */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-2">
                        <h2 className="text-lg font-semibold text-[#0A0A0A]">Your Progress</h2>
                        <span className="text-sm text-[#52525B]">{getProgressPercentage()}% Complete</span>
                    </div>
                    <Progress value={getProgressPercentage()} className="h-2" />
                </div>

                {/* Steps Navigation - Desktop */}
                <div className="hidden md:flex items-center justify-between mb-8 overflow-x-auto">
                    {steps.map((step, index) => {
                        const status = getStepStatus(step.id);
                        const isActive = index === currentStepIndex;
                        const isCompleted = status === 'completed';
                        const canNavigate = isCompleted || index <= currentStepIndex;
                        
                        return (
                            <div key={step.id} className="flex items-center">
                                <button
                                    onClick={() => canNavigate && setCurrentStepIndex(index)}
                                    disabled={!canNavigate}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-sm transition-colors ${
                                        isActive 
                                            ? 'bg-[#114f55] text-white' 
                                            : isCompleted 
                                                ? 'bg-green-500 text-white'
                                                : 'bg-[#E4E4E7] text-[#52525B]'
                                    } ${canNavigate ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
                                    data-testid={`step-nav-${index}`}
                                >
                                    <span className="w-6 h-6 rounded-full border-2 border-current flex items-center justify-center text-sm font-bold">
                                        {isCompleted ? <Check size={14} /> : index + 1}
                                    </span>
                                    <span className="text-sm font-medium hidden lg:block">{step.title}</span>
                                </button>
                                {index < steps.length - 1 && (
                                    <CaretRight size={20} className="mx-2 text-[#E4E4E7]" />
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Steps Navigation - Mobile */}
                <div className="md:hidden mb-6">
                    <div className="flex items-center gap-2 overflow-x-auto pb-2">
                        {steps.map((step, index) => {
                            const status = getStepStatus(step.id);
                            const isActive = index === currentStepIndex;
                            const isCompleted = status === 'completed';
                            
                            return (
                                <div
                                    key={step.id}
                                    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                                        isActive 
                                            ? 'bg-[#114f55] text-white' 
                                            : isCompleted 
                                                ? 'bg-green-500 text-white'
                                                : 'bg-[#E4E4E7] text-[#52525B]'
                                    }`}
                                >
                                    {isCompleted ? <Check size={14} /> : index + 1}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Current Step Content */}
                <div className="bg-white border border-[#E4E4E7] rounded-sm p-6 sm:p-8">
                    {steps[currentStepIndex] && (
                        <>
                            <div className="mb-6">
                                <h1 className="text-2xl font-bold tracking-tight text-[#0A0A0A] mb-2">
                                    {steps[currentStepIndex].title}
                                </h1>
                                <p className="text-[#52525B]">{steps[currentStepIndex].description}</p>
                            </div>
                            {renderStepContent()}
                        </>
                    )}

                    {/* Navigation Buttons */}
                    {currentStepIndex > 0 && (
                        <div className="mt-8 pt-6 border-t border-[#E4E4E7]">
                            <Button
                                variant="ghost"
                                onClick={() => setCurrentStepIndex(currentStepIndex - 1)}
                                className="text-[#52525B]"
                                data-testid="prev-step-btn"
                            >
                                <ArrowLeft className="mr-2" size={16} />
                                Previous Step
                            </Button>
                        </div>
                    )}
                </div>

                {/* Notification Settings */}
                {showSettings && (
                    <div className="mt-6 bg-white border border-[#E4E4E7] rounded-sm p-6 sm:p-8 animate-fadeIn">
                        <div className="flex items-center gap-3 mb-6">
                            <Bell size={24} className="text-[#114f55]" />
                            <h2 className="text-xl font-bold tracking-tight text-[#0A0A0A]">
                                Notification Preferences
                            </h2>
                        </div>
                        <p className="text-sm text-[#52525B] mb-6">
                            Choose when you receive email notifications about your progress.
                        </p>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between p-4 bg-[#FAFAFA] rounded-sm">
                                <div>
                                    <p className="font-medium text-[#0A0A0A]">Step Entry</p>
                                    <p className="text-sm text-[#52525B]">Receive email when starting a new step</p>
                                </div>
                                <Switch
                                    checked={notifPrefs.email_on_step_enter}
                                    onCheckedChange={(val) => setNotifPrefs(prev => ({ ...prev, email_on_step_enter: val }))}
                                    data-testid="notif-step-enter"
                                />
                            </div>
                            <div className="flex items-center justify-between p-4 bg-[#FAFAFA] rounded-sm">
                                <div>
                                    <p className="font-medium text-[#0A0A0A]">Step Edit</p>
                                    <p className="text-sm text-[#52525B]">Receive email when saving progress on a step</p>
                                </div>
                                <Switch
                                    checked={notifPrefs.email_on_step_edit}
                                    onCheckedChange={(val) => setNotifPrefs(prev => ({ ...prev, email_on_step_edit: val }))}
                                    data-testid="notif-step-edit"
                                />
                            </div>
                            <div className="flex items-center justify-between p-4 bg-[#FAFAFA] rounded-sm">
                                <div>
                                    <p className="font-medium text-[#0A0A0A]">Step Completion</p>
                                    <p className="text-sm text-[#52525B]">Receive email when completing a step</p>
                                </div>
                                <Switch
                                    checked={notifPrefs.email_on_step_leave}
                                    onCheckedChange={(val) => setNotifPrefs(prev => ({ ...prev, email_on_step_leave: val }))}
                                    data-testid="notif-step-leave"
                                />
                            </div>
                        </div>
                        <div className="mt-6">
                            <Button
                                onClick={async () => {
                                    try {
                                        await notificationAPI.updatePreferences(notifPrefs);
                                        toast.success('Notification preferences saved');
                                    } catch (error) {
                                        toast.error('Failed to save preferences');
                                    }
                                }}
                                className="bg-[#114f55] hover:bg-[#0d3d42] text-white"
                                data-testid="save-notif-prefs-btn"
                            >
                                Save Preferences
                            </Button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
