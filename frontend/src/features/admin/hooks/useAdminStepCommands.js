import { adminAPI, formatApiError } from '../../../lib/api';
import { toast } from 'sonner';

export function useAdminStepCommands({ activeSurveyId, editingStep, setSteps, setShowStepDialog, setEditingStep, loadData, setActiveSurveyId, setShowTemplatesPanel, setStepsView, surveys, navigate, setConfirmDialog, steps }) {
    const handleSaveStep = async (stepData) => {
            try {
                const payload = { ...stepData, survey_id: stepData.survey_id || activeSurveyId };
                if (editingStep?.id) {
                    await adminAPI.updateStep(editingStep.id, payload);
                    setSteps((current) => current.map((item) => item.id === editingStep.id ? { ...item, ...payload } : item));
                    toast.success('Step updated');
                } else {
                    await adminAPI.createStep(payload);
                    toast.success('Step created');
                }
                setShowStepDialog(false);
                setEditingStep(null);
                await loadData();
            } catch (error) {
                toast.error(formatApiError(error));
            }
        };

    const handleCreateSurvey = async () => {
            const name = window.prompt('Name des neuen Surveys:', 'FSP Pflege');
            if (!name || !name.trim()) return;
            const slug = window.prompt('URL-Slug, z.B. pflege:', name.toLowerCase().replace(/\s+/g, '-'));
            if (!slug || !slug.trim()) return;
            try {
                await adminAPI.createSurvey({
                    name: name.trim(),
                    slug: slug.trim(),
                    description: '',
                    audience: '',
                    is_active: true,
                    is_default: false,
                });
                toast.success('Survey angelegt');
                setActiveSurveyId('');
                loadData();
            } catch (error) {
                toast.error(formatApiError(error));
            }
        };

    const handleSurveyChange = (surveyId) => {
            setEditingStep(null);
            setShowTemplatesPanel(false);
            setStepsView('list');
            setSteps([]);
            setActiveSurveyId(surveyId);
            const selectedSurvey = surveys.find(s => s.id === surveyId);
            const surveyParam = selectedSurvey?.slug || surveyId;
            navigate(`/admin?tab=steps&survey=${encodeURIComponent(surveyParam)}&step=1`, { replace: true });
        };

    const handleDeleteStep = async (stepId) => {
            setConfirmDialog({
                message: 'Sind Sie sicher, dass Sie diesen Schritt loeschen moechten? Alle Fortschrittsdaten der Nutzer fuer diesen Schritt werden ebenfalls entfernt.',
                onConfirm: async () => {
                    try {
                        await adminAPI.deleteStep(stepId);
                        toast.success('Step deleted');
                        loadData();
                    } catch (error) {
                        toast.error(formatApiError(error));
                    }
                    setConfirmDialog(null);
                }
            });
        };

    const handleMoveStep = async (stepId, direction) => {
            const sorted = [...steps].sort((a, b) => a.order - b.order);
            const idx = sorted.findIndex(s => s.id === stepId);
            if (direction === 'up' && idx <= 0) return;
            if (direction === 'down' && idx >= sorted.length - 1) return;
            
            const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
            const newOrder = sorted.map(s => s.id);
            [newOrder[idx], newOrder[swapIdx]] = [newOrder[swapIdx], newOrder[idx]];
            
            try {
                await adminAPI.reorderSteps(newOrder, activeSurveyId);
                toast.success('Steps reordered');
                loadData();
            } catch (error) {
                toast.error(formatApiError(error));
            }
        };

    const handleSaveStepAsTemplate = async (step) => {
            const name = window.prompt(`Template-Name für "${step.title}":`, step.title);
            if (!name || !name.trim()) return;
            try {
                await adminAPI.saveStepAsTemplate(step.id, name.trim(), step.description || '');
                toast.success('Als Template gespeichert');
                loadData();
            } catch (error) {
                toast.error(formatApiError(error));
            }
        };

    const handleApplyTemplate = async (template) => {
            const maxOrder = steps.length ? Math.max(...steps.map(s => s.order)) : 0;
            const input = window.prompt(
                `An welcher Position soll "${template.name}" eingefügt werden? (1-${maxOrder + 1})`,
                String(maxOrder + 1)
            );
            if (!input) return;
            const order = parseInt(input, 10);
            if (!Number.isFinite(order) || order < 1) { toast.error('Ungültige Position'); return; }
            try {
                await adminAPI.applyStepTemplate(template.id, order, activeSurveyId);
                toast.success(`Template "${template.name}" eingefügt`);
                loadData();
            } catch (error) {
                toast.error(formatApiError(error));
            }
        };

    const handleDeleteTemplate = (template) => {
            setConfirmDialog({
                message: `Template "${template.name}" dauerhaft löschen?`,
                onConfirm: async () => {
                    try {
                        await adminAPI.deleteStepTemplate(template.id);
                        toast.success('Template gelöscht');
                        loadData();
                    } catch (error) {
                        toast.error(formatApiError(error));
                    }
                    setConfirmDialog(null);
                }
            });
        };
    return { handleSaveStep, handleCreateSurvey, handleSurveyChange, handleDeleteStep, handleMoveStep, handleSaveStepAsTemplate, handleApplyTemplate, handleDeleteTemplate };
}
