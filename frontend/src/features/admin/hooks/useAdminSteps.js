import { useMemo, useState } from 'react';
import { usePagination } from '../../../components/PaginationControls';

export function useAdminSteps() {
    const [steps, setSteps] = useState([]);
    const [surveys, setSurveys] = useState([]);
    const [activeSurveyId, setActiveSurveyId] = useState('');
    const [editingStep, setEditingStep] = useState(null);
    const [showStepDialog, setShowStepDialog] = useState(false);
    const [stepTemplates, setStepTemplates] = useState([]);
    const [showTemplatesPanel, setShowTemplatesPanel] = useState(false);
    const [stepsView, setStepsView] = useState('flow');
    const sortedSteps = useMemo(() => [...steps].sort((a, b) => a.order - b.order), [steps]);
    const templatesPagination = usePagination(stepTemplates, 'admin-step-templates');
    const stepsPagination = usePagination(sortedSteps, 'admin-steps', { resetKey: activeSurveyId });
    return { steps, setSteps, surveys, setSurveys, activeSurveyId, setActiveSurveyId, editingStep, setEditingStep, showStepDialog, setShowStepDialog, stepTemplates, setStepTemplates, showTemplatesPanel, setShowTemplatesPanel, stepsView, setStepsView, sortedSteps, templatesPagination, stepsPagination };
}
