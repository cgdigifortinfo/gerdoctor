import { evaluateCondition } from './conditionEvaluator';

export function buildStepDataByOrder(steps, progress) {
    const progressByStep = {};
    (progress || []).forEach(entry => { progressByStep[entry.step_id] = entry; });
    const result = {};
    (steps || []).forEach(step => {
        const entry = progressByStep[step.id || step.step_id] || {};
        result[step.order] = { data: entry.data || {}, status: entry.status || 'pending' };
    });
    return result;
}

export function getHiddenStepIds(steps, progress) {
    const stepDataByOrder = buildStepDataByOrder(steps, progress);
    const hidden = new Set();
    (steps || []).forEach(step => {
        for (const condition of (step.conditions || [])) {
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
    return (steps || []).filter(step => !hidden.has(step.id || step.step_id));
}
