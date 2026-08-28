export const CONTENT_FIELD_TYPES = new Set(['heading', 'paragraph', 'html', 'image', 'divider']);
const EMPTY_LIST = Object.freeze([]);

export const DEFAULT_NOTIFICATION_PREFERENCES = Object.freeze({
    email_on_step_enter: true,
    email_on_step_edit: false,
    email_on_step_leave: true,
});

export function normalizeJourneyBootstrap(payload) {
    const source = payload ?? {};
    const settings = source.settings ?? {};
    return {
        steps: source.steps ?? [],
        progress: source.progress ?? [],
        allStepData: source.all_step_data ?? [],
        notificationPreferences: source.notification_preferences ?? { ...DEFAULT_NOTIFICATION_PREFERENCES },
        history: source.history ?? [],
        estimatedCompletion: source.estimated_completion ?? null,
        uiFlags: {
            ui_show_journey_indicator: settings.ui_show_journey_indicator !== false,
            ui_show_eta_header: settings.ui_show_eta_header !== false,
            ui_show_progress_percentage: settings.ui_show_progress_percentage !== false,
        },
    };
}

export const optionValue = (option) => typeof option === 'object' && option !== null
    ? String(option.value ?? option.label ?? '')
    : String(option ?? '');

export const optionLabel = (option) => typeof option === 'object' && option !== null
    ? String(option.label ?? option.value ?? '')
    : String(option ?? '');

export function evaluateJourneyCondition(condition, allStepData) {
    if (!condition) return false;
    if (Array.isArray(condition.all_of)) return condition.all_of.every(child => evaluateJourneyCondition(child, allStepData));
    if (Array.isArray(condition.any_of)) return condition.any_of.some(child => evaluateJourneyCondition(child, allStepData));
    const source = allStepData.find(step => step.order === condition.source_step_order);
    if (!source) return false;
    const sourceData = source.data ?? {};
    const fieldValue = condition.field ? sourceData[condition.field] : source.status;
    const expected = condition.value;
    const expectedValues = () => (Array.isArray(expected) ? expected : [expected]).map(String);
    const expectedDocumentType = expected ?? '';
    const uploadMatches = (upload) => Boolean(upload?.file_id) && (expectedDocumentType === '' || upload.document_type === expectedDocumentType);
    switch (condition.operator) {
        case 'equals': return String(fieldValue) === String(expected);
        case 'not_equals': return String(fieldValue) !== String(expected);
        case 'one_of': return Array.isArray(fieldValue) ? fieldValue.some(value => expectedValues().includes(String(value))) : expectedValues().includes(String(fieldValue));
        case 'not_one_of': return Array.isArray(fieldValue) ? !fieldValue.some(value => expectedValues().includes(String(value))) : !expectedValues().includes(String(fieldValue));
        case 'contains': return String(fieldValue).includes(String(expected));
        case 'not_empty': return Boolean(fieldValue);
        case 'empty': return !fieldValue;
        case 'status_is': return source.status === expected;
        case 'status_not': return source.status !== expected;
        case 'has_upload': return Array.isArray(fieldValue) && fieldValue.some(uploadMatches);
        case 'missing_upload': return !Array.isArray(fieldValue) || !fieldValue.some(uploadMatches);
        default: return false;
    }
}

export function evaluateStepConditions(step, allStepData) {
    const result = { allowed: true, blocked: false, hidden: false, readOnly: false, message: '', redirectStep: null };
    for (const condition of step.conditions ?? EMPTY_LIST) {
        if (!evaluateJourneyCondition(condition, allStepData)) continue;
        if (condition.action === 'block') Object.assign(result, { allowed: false, blocked: true, message: condition.message || 'Dieser Schritt ist gesperrt.' });
        else if (condition.action === 'hide') result.hidden = true;
        else if (condition.action === 'read_only') Object.assign(result, { readOnly: true, message: condition.message || result.message });
        else if (condition.action === 'allow_next') Object.assign(result, { allowed: true, message: condition.message || '' });
        else if (condition.action === 'redirect') result.redirectStep = condition.target_step_order;
    }
    return result;
}

export const isStepHidden = (step, allStepData) => evaluateStepConditions(step, allStepData).hidden;

export function applyFieldMappings(step, allStepData) {
    const prefilled = {};
    for (const mapping of step.field_mappings ?? EMPTY_LIST) {
        const source = allStepData.find(item => item.order === mapping.source_step_order);
        const sourceData = source?.data ?? {};
        if (sourceData[mapping.source_field] !== undefined) prefilled[mapping.target_field] = sourceData[mapping.source_field];
    }
    return prefilled;
}

export function scorePartner(partner, profile) {
    if (!profile) return 0;
    const specialty = profile.fachrichtung_gewuenscht || profile.fachrichtung_praktiziert || profile.field_of_study;
    const state = profile.anerkennungsverfahren_bundesland;
    const tags = partner.tags ?? EMPTY_LIST;
    return (specialty && partner.category === specialty ? 10 : 0)
        + (specialty && tags.includes(specialty) ? 10 : 0)
        + (state && tags.includes(state) ? 5 : 0);
}

export function sortPartnersByRecommendation(partners, profile) {
    return partners.map(partner => ({ ...partner, _score: scorePartner(partner, profile) }))
        .sort(compareRankedPartners);
}

export function compareRankedPartners(left, right) {
    const scoreDelta = right._score - left._score;
    return scoreDelta || String(left.name ?? '').localeCompare(String(right.name ?? ''));
}

export function canNavigateToJourneyStep(steps, progress, currentIndex, allStepData, targetIndex) {
    const step = steps[targetIndex];
    if (!step) return false;
    const status = progress.find(entry => entry.step_id === step.id)?.status || 'pending';
    if (status === 'completed' || targetIndex <= currentIndex) return true;
    return false;
}
