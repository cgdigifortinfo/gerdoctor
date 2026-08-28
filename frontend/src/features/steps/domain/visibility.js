import { evaluateCondition } from './conditionEvaluator';

export function buildStepDataByOrder(steps, progress) {
    const progressByStep = {};
    if (Array.isArray(progress)) {
        progress.forEach(entry => { progressByStep[entry.step_id] = entry; });
    }
    const result = {};
    const sourceSteps = Array.isArray(steps) ? steps : [];
    sourceSteps.forEach(step => {
        const entry = progressByStep[step.id || step.step_id] || {};
        result[step.order] = { data: entry.data || {}, status: entry.status || 'pending' };
    });
    return result;
}

export function getHiddenStepIds(steps, progress) {
    const stepDataByOrder = buildStepDataByOrder(steps, progress);
    const hidden = new Set();
    if (!Array.isArray(steps)) return hidden;
    const sourceSteps = steps;
    sourceSteps.forEach(step => {
        if (!Array.isArray(step.conditions)) return;
        const conditions = step.conditions;
        for (const condition of conditions) {
            if (condition.action !== 'hide') continue;
            if (evaluateCondition(condition, stepDataByOrder)) {
                hidden.add(step.id || step.step_id);
                break;
            }
        }
    });
    return hidden;
}

export function filterVisibleSteps(steps, progress) {
    const hidden = getHiddenStepIds(steps, progress);
    if (!Array.isArray(steps)) return [];
    const sourceSteps = steps;
    return sourceSteps.filter(step => !hidden.has(step.id || step.step_id));
}
