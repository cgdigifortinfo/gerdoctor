import { evaluateCondition } from './conditionEvaluator';

export function simulateJourney(steps, profile = {}) {
    const emptyResult = () => ({ hidden: new Set(), blocked: new Set(), autoComplete: new Set() });
    if (!Array.isArray(steps)) return emptyResult();
    const sourceSteps = steps;
    const sortedSteps = [...sourceSteps].sort((left, right) => left.order - right.order);
    const stepDataByOrder = {};
    sortedSteps.forEach(step => {
        const entry = profile[step.order] || {};
        stepDataByOrder[step.order] = {
            data: entry.data || {},
            status: entry.status || (entry.data ? 'completed' : 'pending'),
        };
    });
    const hidden = new Set();
    const blocked = new Set();
    const autoComplete = new Set();
    sortedSteps.forEach(step => {
        const stepId = step.id || step.step_id;
        if (!Array.isArray(step.conditions)) return;
        const conditions = step.conditions;
        for (const condition of conditions) {
            if (!evaluateCondition(condition, stepDataByOrder)) continue;
            if (condition.action === 'hide') hidden.add(stepId);
            else if (condition.action === 'block') blocked.add(stepId);
            else if (condition.action === 'auto_complete') autoComplete.add(stepId);
        }
    });
    return { hidden, blocked, autoComplete };
}
