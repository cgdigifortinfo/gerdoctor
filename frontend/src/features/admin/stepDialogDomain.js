import { CONTENT_FIELD_TYPES } from '../../components/admin/surveyFormDomain';
import { CONDITION_OPERATOR_OPTIONS, STEP_STATUS_OPTIONS, conditionFieldUpdate, conditionOperatorUpdate, conditionSourceUpdate, optionLabel, optionValue, stepFieldOptions, withFallbackOption } from './stepEditorDomain';

export function createStepFormData(step, existingStepCount, activeSurveyId) {
    return {
        title: step?.title || '', description: step?.description || '',
        order: step?.order || existingStepCount + 1,
        survey_id: step?.survey_id || activeSurveyId,
        step_type: step?.step_type || 'form', fields: step?.fields || [],
        filter_tag: step?.filter_tag || '', partner_user_fee_cents: step?.partner_user_fee_cents ?? null,
        skippable: step?.skippable || false, skip_label: step?.skip_label || '',
        action_label: step?.action_label || '', pending_message: step?.pending_message || '', complete_message: step?.complete_message || '',
        required_fields: step?.required_fields || [], required_uploads: step?.required_uploads || [],
        field_mappings: step?.field_mappings || [], conditions: step?.conditions || [],
        duration_value: step?.duration_value ?? 0, duration_unit: step?.duration_unit || 'days',
        email_on_enter: step?.email_on_enter || false, email_on_edit: step?.email_on_edit || false,
        email_on_leave: step?.email_on_leave || false, is_active: step?.is_active !== false,
    };
}

export function requiredFieldNames(fields) {
    return fields
        .filter(field => field.required && !CONTENT_FIELD_TYPES.has(field.field_type) && field.field_type !== 'multiupload')
        .map(field => field.name)
        .filter(Boolean);
}

export function selectStepSurvey(formData, surveyId) {
    return { ...formData, survey_id: surveyId };
}

export function shouldNotifySurveyChange(surveyId, activeSurveyId) {
    return surveyId !== activeSurveyId;
}

export function updateStepTranslation(translations, language, field, value) {
    return { ...translations, [language]: { ...translations[language], [field]: value } };
}

export function updateStepFields(formData, fields) {
    return { ...formData, fields, required_fields: requiredFieldNames(fields) };
}

export function partnerFeeFromInput(value) {
    return value === '' ? null : Number(value);
}

export function stepDialogTitle(formData, hasStep) {
    return formData.title || (hasStep ? `Step #${formData.order}` : 'Neuer Schritt');
}

export function buildStepOptions(steps, currentStepId) {
    return steps.map(candidate => ({
        value: String(candidate.order),
        label: `${candidate.order}. ${candidate.title}`,
        description: candidate.step_type === 'form' ? `${candidate.fields?.length || 0} Formularfelder` : candidate.step_type,
        keywords: `${candidate.id || ''} ${candidate.step_type || ''}`,
        disabled: candidate.id === currentStepId,
    }));
}

export function buildSurveyOptions(surveys) {
    return surveys.map(survey => ({ value: survey.id, label: survey.name, description: `/s/${survey.slug}`, keywords: survey.slug }));
}

export function buildPartnerTagOptions(partners) {
    const counts = new Map();
    partners.forEach(partner => (partner.tags || []).forEach(tag => counts.set(tag, (counts.get(tag) || 0) + 1)));
    return [...counts.entries()].sort(([left], [right]) => left.localeCompare(right, 'de')).map(([tag, count]) => ({
        value: tag, label: tag, description: `${count} passende${count === 1 ? 'r Partner' : ' Partner'}`,
    }));
}

export function buildCurrentFieldOptions(fields) {
    return fields.map(field => ({ value: field.name, label: field.label || field.name, description: `${field.name} · ${field.field_type || 'Feld'}` }));
}

export function buildDocumentTypeOptions(requiredUploads, referenceSteps, fields) {
    const values = new Set(requiredUploads);
    [...referenceSteps, { fields }].forEach(candidate => candidate.fields?.forEach(field => {
        if (field.field_type === 'multiupload') (field.options || []).forEach(option => values.add(String(optionValue(option))));
    }));
    return [...values].filter(Boolean).sort((left, right) => left.localeCompare(right, 'de')).map(value => ({ value, label: value }));
}

export function defaultConditionLeaf(referenceSteps, currentOrder, currentStepId) {
    const source = [...referenceSteps].reverse().find(candidate => candidate.order < currentOrder)
        || referenceSteps.find(candidate => candidate.id !== currentStepId)
        || referenceSteps[0];
    return { source_step_order: source?.order || null, field: 'status', operator: 'status_is', value: 'completed' };
}

export function addMappingState(current, referenceSteps, currentStepId) {
    const source = referenceSteps.find(candidate => candidate.id !== currentStepId);
    return { ...current, field_mappings: [...current.field_mappings, {
        source_step_order: source?.order ?? null,
        source_field: source?.fields?.[0]?.name || '',
        target_field: current.fields?.[0]?.name || '',
    }] };
}

export function updateMappingState(current, index, patch) {
    const field_mappings = [...current.field_mappings];
    field_mappings[index] = { ...field_mappings[index], ...patch };
    return { ...current, field_mappings };
}

export function removeMappingState(current, index) {
    return { ...current, field_mappings: current.field_mappings.filter((_, candidateIndex) => candidateIndex !== index) };
}

export function changeMappingSourceState(current, index, value, source) {
    return updateMappingState(current, index, { source_step_order: value ? Number(value) : null, source_field: source?.fields?.[0]?.name || '' });
}

export function updateConditionState(current, index, patch) {
    const conditions = [...current.conditions];
    conditions[index] = { ...conditions[index], ...patch };
    return { ...current, conditions };
}

export function removeConditionState(current, index) {
    return { ...current, conditions: current.conditions.filter((_, candidateIndex) => candidateIndex !== index) };
}

export function addConditionState(current, leaf) {
    return { ...current, conditions: [...current.conditions, { ...leaf, action: 'block', target_step_order: null, message: 'Bitte schließen Sie zuerst den ausgewählten Schritt ab.' }] };
}

export function addConditionGroupState(current, groupKey, leaf) {
    return { ...current, conditions: [...current.conditions, { [groupKey]: [leaf], action: 'block', target_step_order: null, message: 'Die konfigurierte Bedingungsgruppe ist noch nicht erfüllt.' }] };
}

export function changeConditionFieldState(current, index, fieldName, selectedField) {
    return updateConditionState(current, index, conditionFieldUpdate(fieldName, selectedField));
}

export function changeConditionOperatorState(current, index, operator) {
    return updateConditionState(current, index, conditionOperatorUpdate(operator, current.conditions[index].value));
}

export function changeConditionSourceState(current, index, value) {
    return updateConditionState(current, index, conditionSourceUpdate(value));
}

export function updateConditionChildState(current, conditionIndex, groupKey, childIndex, patch) {
    const conditions = [...current.conditions];
    const children = [...conditions[conditionIndex][groupKey]];
    children[childIndex] = { ...children[childIndex], ...patch };
    conditions[conditionIndex] = { ...conditions[conditionIndex], [groupKey]: children };
    return { ...current, conditions };
}

export function addConditionChildState(current, conditionIndex, groupKey, leaf) {
    const condition = current.conditions[conditionIndex];
    return updateConditionState(current, conditionIndex, { [groupKey]: [...condition[groupKey], leaf] });
}

export function removeConditionChildState(current, conditionIndex, groupKey, childIndex) {
    const children = current.conditions[conditionIndex][groupKey].filter((_, index) => index !== childIndex);
    return children.length ? updateConditionState(current, conditionIndex, { [groupKey]: children }) : current;
}

export function changeConditionGroupTypeState(current, conditionIndex, oldKey, newKey) {
    const conditions = [...current.conditions];
    const condition = { ...current.conditions[conditionIndex], [newKey]: current.conditions[conditionIndex][oldKey] };
    delete condition[oldKey];
    conditions[conditionIndex] = condition;
    return { ...current, conditions };
}

export function addConditionPresetState(current, preset) {
    return { ...current, conditions: [...current.conditions, { target_step_order: null, message: '', ...preset }] };
}

export function sortReferenceSteps(steps) {
    return [...steps].sort((left, right) => left.order - right.order);
}

export function findStepByOrder(steps, order) {
    return steps.find(candidate => candidate.order === Number(order));
}

export function findStepField(step, fieldName) {
    return step?.fields?.find(field => field.name === fieldName);
}

export function buildSourceFieldOptions(steps, sourceOrder, currentValue) {
    return withFallbackOption(stepFieldOptions(findStepByOrder(steps, sourceOrder)), currentValue, 'Nicht gefundenes Feld');
}

export function buildConditionValueOptions(condition, steps, documentTypes) {
    if (condition.field === 'status' || condition.operator === 'status_is' || condition.operator === 'status_not') {
        const current = Array.isArray(condition.value) ? condition.value : [condition.value];
        return current.reduce((options, value) => withFallbackOption(options, value), STEP_STATUS_OPTIONS);
    }
    const sourceField = findStepField(findStepByOrder(steps, condition.source_step_order), condition.field);
    const configured = (sourceField?.options || []).map(option => ({ value: String(optionValue(option)), label: String(optionLabel(option)) }));
    const base = condition.operator === 'has_upload' || condition.operator === 'missing_upload'
        ? [...configured, ...documentTypes.filter(option => !configured.some(item => item.value === option.value))]
        : configured;
    const current = Array.isArray(condition.value) ? condition.value : [condition.value];
    return current.reduce((options, value) => withFallbackOption(options, value), base);
}

export function buildConditionOperatorOptions(condition, steps) {
    const sourceField = findStepField(findStepByOrder(steps, condition.source_step_order), condition.field);
    let allowed;
    if (condition.field === 'status') allowed = ['status_is', 'status_not'];
    else if (sourceField?.field_type === 'multiupload') allowed = ['has_upload', 'missing_upload', 'not_empty', 'empty'];
    else if ((sourceField?.options?.length || 0) > 0 || sourceField?.field_type === 'decision') allowed = ['equals', 'not_equals', 'one_of', 'not_one_of', 'not_empty', 'empty'];
    else allowed = ['equals', 'not_equals', 'one_of', 'not_one_of', 'contains', 'not_empty', 'empty'];
    const options = CONDITION_OPERATOR_OPTIONS.filter(option => allowed.includes(option.value));
    return condition.operator && !options.some(option => option.value === condition.operator)
        ? [...options, { value: condition.operator, label: condition.operator }]
        : options;
}

export function conditionPresets(steps, currentOrder) {
    let previousStep;
    let uploadPresetStep;
    let uploadPresetField;
    let choicePresetStep;
    let choicePresetField;
    for (const step of steps) {
        if (step.order < currentOrder) previousStep = step;
        for (const field of step.fields ?? []) {
            if (!uploadPresetField && field.field_type === 'multiupload') {
                uploadPresetStep = step;
                uploadPresetField = field;
            }
            if (!choicePresetField && field.field_type !== 'multiupload' && (field.options?.length ?? 0) > 0) {
                choicePresetStep = step;
                choicePresetField = field;
            }
        }
    }
    return { previousStep, uploadPresetStep, uploadPresetField, choicePresetStep, choicePresetField };
}

export function validStepSection(section, stepType) {
    if (section === 'fields' && stepType !== 'form' && stepType !== 'decision') return 'basic';
    if (section === 'type' && !['partner_selection', 'partner_multiselection', 'milestone', 'display'].includes(stepType)) return 'basic';
    return section;
}
