import { addConditionChildState, addConditionGroupState, addConditionPresetState, addConditionState, addMappingState, buildConditionOperatorOptions, buildConditionValueOptions, buildCurrentFieldOptions, buildDocumentTypeOptions, buildPartnerTagOptions, buildSourceFieldOptions, buildStepOptions, buildSurveyOptions, changeConditionFieldState, changeConditionGroupTypeState, changeConditionOperatorState, changeConditionSourceState, changeMappingSourceState, conditionPresets, createStepFormData, defaultConditionLeaf, findStepByOrder, findStepField, partnerFeeFromInput, removeConditionChildState, removeConditionState, removeMappingState, requiredFieldNames, selectStepSurvey, shouldNotifySurveyChange, sortReferenceSteps, stepDialogTitle, updateConditionChildState, updateConditionState, updateMappingState, updateStepFields, updateStepTranslation, validStepSection } from './stepDialogDomain';

test('step form data has stable create defaults and preserves meaningful edit values', () => {
  expect(createStepFormData(null, 2, 'survey')).toEqual({
    title: '', description: '', order: 3, survey_id: 'survey', step_type: 'form', fields: [], filter_tag: '', partner_user_fee_cents: null,
    skippable: false, skip_label: '', action_label: '', pending_message: '', complete_message: '', required_fields: [], required_uploads: [],
    field_mappings: [], conditions: [], duration_value: 0, duration_unit: 'days', email_on_enter: false, email_on_edit: false,
    email_on_leave: false, is_active: true,
  });
  const step = { title: 'T', description: 'D', order: 4, survey_id: 'own', step_type: 'decision', fields: [{}], filter_tag: 'tag', partner_user_fee_cents: 0, skippable: true, skip_label: 'Skip', action_label: 'Go', pending_message: 'P', complete_message: 'C', required_fields: ['f'], required_uploads: ['u'], field_mappings: [{}], conditions: [{}], duration_value: 0, duration_unit: 'hours', email_on_enter: true, email_on_edit: true, email_on_leave: true, is_active: false };
  expect(createStepFormData(step, 9, 'fallback')).toEqual(step);
});

test('step dialog state transitions are explicit domain operations', () => {
  const form = { title: '', order: 4, survey_id: 'old', fields: [], required_fields: [] };
  expect(selectStepSurvey(form, 'new')).toEqual({ ...form, survey_id: 'new' });
  expect(selectStepSurvey(form, 'new')).not.toBe(form);
  expect(shouldNotifySurveyChange('new', 'old')).toBe(true);
  expect(shouldNotifySurveyChange('same', 'same')).toBe(false);
  expect(updateStepTranslation({}, 'en', 'title', 'Title')).toEqual({ en: { title: 'Title' } });
  expect(updateStepTranslation({ en: { description: 'Keep' }, de: { title: 'Deutsch' } }, 'en', 'title', 'Title')).toEqual({ en: { description: 'Keep', title: 'Title' }, de: { title: 'Deutsch' } });
  const fields = [{ name: 'required', field_type: 'text', required: true }, { name: 'heading', field_type: 'heading', required: true }];
  expect(updateStepFields(form, fields)).toEqual({ ...form, fields, required_fields: ['required'] });
  expect(partnerFeeFromInput('')).toBeNull();
  expect(partnerFeeFromInput('0')).toBe(0);
  expect(partnerFeeFromInput('250')).toBe(250);
  expect(stepDialogTitle({ title: 'Named', order: 2 }, true)).toBe('Named');
  expect(stepDialogTitle({ title: '', order: 2 }, true)).toBe('Step #2');
  expect(stepDialogTitle({ title: '', order: 2 }, false)).toBe('Neuer Schritt');
});

test('sparse edit data falls back field by field without losing explicit states', () => {
  expect(createStepFormData({ order: 0, partner_user_fee_cents: 0, duration_value: 0, is_active: true }, 4, 'active')).toEqual(expect.objectContaining({
    order: 5, survey_id: 'active', partner_user_fee_cents: 0, duration_value: 0, is_active: true,
  }));
  expect(createStepFormData({ is_active: false }, 0, '')).toEqual(expect.objectContaining({ order: 1, is_active: false }));
});

test('required fields exclude content, uploads and unnamed fields', () => {
  expect(requiredFieldNames([
    { name: 'plain', field_type: 'text', required: true }, { name: 'optional', field_type: 'text', required: false },
    { name: 'heading', field_type: 'heading', required: true }, { name: 'upload', field_type: 'multiupload', required: true },
    { name: '', field_type: 'text', required: true },
  ])).toEqual(['plain']);
});

test('step, survey, partner and current-field options preserve all display metadata', () => {
  expect(buildStepOptions([
    { id: 'current', order: 2, title: 'Form', step_type: 'form', fields: [{}, {}] },
    { id: '', order: 3, title: '', step_type: 'display' },
    { id: 'sparse', order: 4, title: 'Sparse', step_type: 'form' },
    { id: 'unknown', order: 5, title: 'Unknown' },
  ], 'current')).toEqual([
    { value: '2', label: '2. Form', description: '2 Formularfelder', keywords: 'current form', disabled: true },
    { value: '3', label: '3. ', description: 'display', keywords: ' display', disabled: false },
    { value: '4', label: '4. Sparse', description: '0 Formularfelder', keywords: 'sparse form', disabled: false },
    { value: '5', label: '5. Unknown', description: undefined, keywords: 'unknown ', disabled: false },
  ]);
  expect(buildSurveyOptions([{ id: 's', name: 'Survey', slug: 'slug' }])).toEqual([{ value: 's', label: 'Survey', description: '/s/slug', keywords: 'slug' }]);
  expect(buildPartnerTagOptions([{ tags: ['B', 'A'] }, { tags: ['A'] }, {}])).toEqual([
    { value: 'A', label: 'A', description: '2 passende Partner' }, { value: 'B', label: 'B', description: '1 passender Partner' },
  ]);
  expect(buildCurrentFieldOptions([{ name: 'plain' }, { name: 'named', label: 'Named', field_type: 'text' }])).toEqual([
    { value: 'plain', label: 'plain', description: 'plain · Feld' }, { value: 'named', label: 'Named', description: 'named · text' },
  ]);
});

test('document type options combine, normalize, deduplicate and sort uploads', () => {
  expect(buildDocumentTypeOptions(['Z', '', 'A'], [
    { fields: [{ field_type: 'multiupload', options: ['B', { value: 'A' }] }, { field_type: 'text', options: ['ignored'] }] },
    {}, { fields: null },
  ], [{ field_type: 'multiupload', options: [{ label: 'C' }] }, { field_type: 'multiupload' }])).toEqual([
    { value: 'A', label: 'A' }, { value: 'B', label: 'B' }, { value: 'C', label: 'C' }, { value: 'Z', label: 'Z' },
  ]);
});

test('mapping reducers create, change, patch and remove immutable mappings', () => {
  const base = { fields: [{ name: 'target' }], field_mappings: [{ source_step_order: 9, source_field: 'old', target_field: 'target' }] };
  const refs = [{ id: 'current', order: 1 }, { id: 'source', order: 2, fields: [{ name: 'origin' }] }];
  const added = addMappingState(base, refs, 'current');
  expect(added.field_mappings[1]).toEqual({ source_step_order: 2, source_field: 'origin', target_field: 'target' });
  expect(base.field_mappings).toHaveLength(1);
  expect(updateMappingState(base, 0, { target_field: 'new' }).field_mappings[0]).toEqual({ source_step_order: 9, source_field: 'old', target_field: 'new' });
  expect(changeMappingSourceState(base, 0, '2', refs[1]).field_mappings[0]).toEqual({ source_step_order: 2, source_field: 'origin', target_field: 'target' });
  expect(changeMappingSourceState(base, 0, '', undefined).field_mappings[0]).toEqual({ source_step_order: null, source_field: '', target_field: 'target' });
  expect(removeMappingState(base, 0).field_mappings).toEqual([]);
  expect(addMappingState({ fields: [], field_mappings: [] }, [], 'none').field_mappings[0]).toEqual({ source_step_order: null, source_field: '', target_field: '' });
  expect(addMappingState({ field_mappings: [] }, [{ id: 'source', order: 1, fields: [] }], 'none').field_mappings[0]).toEqual({ source_step_order: 1, source_field: '', target_field: '' });
  expect(addMappingState({ field_mappings: [] }, [{ id: 'source', order: 1 }], 'none').field_mappings[0]).toEqual({ source_step_order: 1, source_field: '', target_field: '' });
  expect(changeMappingSourceState(base, 0, '1', { fields: [] }).field_mappings[0].source_field).toBe('');
  expect(changeMappingSourceState(base, 0, '1', {}).field_mappings[0].source_field).toBe('');
  const twoMappings = { ...base, field_mappings: [base.field_mappings[0], { source_field: 'keep' }] };
  expect(removeMappingState(twoMappings, 0).field_mappings).toEqual([{ source_field: 'keep' }]);
});

test('condition reducers cover leaf selection, simple updates and presets', () => {
  const refs = [{ id: 'future', order: 4 }, { id: 'previous', order: 2 }, { id: 'current', order: 3 }];
  expect(defaultConditionLeaf(refs, 3, 'current')).toEqual({ source_step_order: 2, field: 'status', operator: 'status_is', value: 'completed' });
  expect(defaultConditionLeaf([{ id: 'old', order: 1 }, { id: 'near', order: 2 }, { id: 'current', order: 3 }], 3, 'current').source_step_order).toBe(2);
  expect(defaultConditionLeaf([{ id: 'current', order: 1 }, { id: 'other', order: 4 }], 1, 'current').source_step_order).toBe(4);
  expect(defaultConditionLeaf([{ id: 'current', order: 1 }], 1, 'current').source_step_order).toBe(1);
  expect(defaultConditionLeaf([], 1, 'current').source_step_order).toBeNull();
  const base = { conditions: [{ field: 'choice', operator: 'equals', value: 'a', action: 'hide' }] };
  expect(addConditionState(base, defaultConditionLeaf([], 1)).conditions[1]).toEqual({ source_step_order: null, field: 'status', operator: 'status_is', value: 'completed', action: 'block', target_step_order: null, message: 'Bitte schließen Sie zuerst den ausgewählten Schritt ab.' });
  expect(addConditionGroupState(base, 'all_of', { field: 'status' }).conditions[1]).toEqual({ all_of: [{ field: 'status' }], action: 'block', target_step_order: null, message: 'Die konfigurierte Bedingungsgruppe ist noch nicht erfüllt.' });
  expect(updateConditionState(base, 0, { message: 'x' }).conditions[0]).toEqual({ ...base.conditions[0], message: 'x' });
  expect(removeConditionState(base, 0).conditions).toEqual([]);
  expect(removeConditionState({ conditions: [base.conditions[0], { field: 'keep' }] }, 0).conditions).toEqual([{ field: 'keep' }]);
  expect(changeConditionSourceState(base, 0, '')).toEqual({ conditions: [{ ...base.conditions[0], source_step_order: null, field: 'status', operator: 'status_is', value: 'completed' }] });
  expect(changeConditionFieldState(base, 0, 'status')).toEqual({ conditions: [{ ...base.conditions[0], field: 'status', operator: 'status_is', value: 'completed' }] });
  expect(changeConditionFieldState(base, 0, 'docs', { field_type: 'multiupload' }).conditions[0]).toEqual({ ...base.conditions[0], field: 'docs', operator: 'has_upload', value: '' });
  expect(changeConditionOperatorState(base, 0, 'one_of').conditions[0].value).toEqual(['a']);
  expect(addConditionPresetState(base, { field: 'status' }).conditions[1]).toEqual({ target_step_order: null, message: '', field: 'status' });
});

test('compound condition reducers update, append, guard removal and rename groups', () => {
  const first = { field: 'status', value: 'completed' }, second = { field: 'choice', value: 'a' };
  const base = { conditions: [{ all_of: [first, second], action: 'block' }, { field: 'keep' }] };
  expect(updateConditionChildState(base, 0, 'all_of', 1, { value: 'b' }).conditions[0].all_of[1]).toEqual({ field: 'choice', value: 'b' });
  expect(addConditionChildState(base, 0, 'all_of', { field: 'new' }).conditions[0].all_of).toEqual([first, second, { field: 'new' }]);
  expect(removeConditionChildState(base, 0, 'all_of', 0).conditions[0].all_of).toEqual([second]);
  const single = { conditions: [{ all_of: [first], action: 'block' }] };
  expect(removeConditionChildState(single, 0, 'all_of', 0)).toBe(single);
  expect(changeConditionGroupTypeState(base, 0, 'all_of', 'any_of').conditions[0]).toEqual({ any_of: [first, second], action: 'block' });
  expect(changeConditionGroupTypeState(base, 0, 'all_of', 'any_of').conditions[1]).toEqual({ field: 'keep' });
});

test('reference lookup and condition value options handle status, configured, uploads and fallbacks', () => {
  const steps = sortReferenceSteps([
    { order: 2, fields: [{ name: 'docs', field_type: 'multiupload', options: ['Passport'] }, { name: 'choice', field_type: 'decision', options: [{ value: 'yes', label: 'Yes' }] }, { name: 'text', field_type: 'text' }] },
    { order: 1 },
  ]);
  expect(steps.map(step => step.order)).toEqual([1, 2]);
  expect(findStepByOrder(steps, '2')).toBe(steps[1]);
  expect(findStepByOrder(steps, '9')).toBeUndefined();
  expect(findStepField(steps[1], 'choice').field_type).toBe('decision');
  expect(findStepField(undefined, 'choice')).toBeUndefined();
  expect(findStepField({}, 'choice')).toBeUndefined();
  expect(buildSourceFieldOptions(steps, 9, 'legacy').at(-1)).toEqual({ value: 'legacy', label: 'Nicht gefundenes Feld: legacy' });
  expect(buildConditionValueOptions({ field: 'status', operator: 'status_is', value: ['completed', 'custom'] }, steps, [])).toEqual(expect.arrayContaining([{ value: 'completed', label: 'Abgeschlossen' }, { value: 'custom', label: 'Bestehender Wert: custom' }]));
  expect(buildConditionValueOptions({ field: 'other', operator: 'status_is', value: [] }, steps, [])).toEqual([
    { value: 'pending', label: 'Ausstehend' }, { value: 'in_progress', label: 'In Bearbeitung' }, { value: 'completed', label: 'Abgeschlossen' }, { value: 'rejected', label: 'Abgelehnt' }, { value: 'skipped', label: 'Übersprungen' },
  ]);
  expect(buildConditionValueOptions({ field: 'other', operator: 'status_not', value: [] }, steps, [])).toEqual(expect.arrayContaining([{ value: 'pending', label: 'Ausstehend' }]));
  expect(buildConditionValueOptions({ field: 'status', operator: 'equals', value: 'completed' }, steps, [])).toEqual(expect.arrayContaining([{ value: 'completed', label: 'Abgeschlossen' }]));
  expect(buildConditionValueOptions({ field: 'other', operator: 'status_is', value: 'custom-status' }, steps, [])).toEqual(expect.arrayContaining([{ value: 'custom-status', label: 'Bestehender Wert: custom-status' }]));
  expect(buildConditionValueOptions({ source_step_order: 2, field: 'choice', operator: 'equals', value: 'yes' }, steps, [])).toEqual([{ value: 'yes', label: 'Yes' }]);
  expect(buildConditionValueOptions({ source_step_order: 2, field: 'text', operator: 'equals', value: [], }, steps, [{ value: 'must-not-appear', label: 'Document' }])).toEqual([]);
  expect(buildConditionValueOptions({ source_step_order: 2, field: 'docs', operator: 'has_upload', value: 'Legacy' }, steps, [{ value: 'Other', label: 'Other' }])).toEqual([{ value: 'Passport', label: 'Passport' }, { value: 'Other', label: 'Other' }, { value: 'Legacy', label: 'Bestehender Wert: Legacy' }]);
  expect(buildConditionValueOptions({ source_step_order: 2, field: 'docs', operator: 'missing_upload', value: 'Other' }, steps, [{ value: 'Passport', label: 'duplicate' }, { value: 'Other', label: 'Other' }])).toEqual([{ value: 'Passport', label: 'Passport' }, { value: 'Other', label: 'Other' }]);
  expect(buildConditionValueOptions({ source_step_order: 2, field: 'docs', operator: 'has_upload', value: [] }, steps, [{ value: 'Passport', label: 'duplicate' }])).toEqual([{ value: 'Passport', label: 'Passport' }]);
  expect(buildConditionValueOptions({ source_step_order: 2, field: 'text', operator: 'has_upload', value: [] }, steps, [{ value: 'Document', label: 'Document' }])).toEqual([{ value: 'Document', label: 'Document' }]);
  expect(buildConditionValueOptions({ source_step_order: 9, field: 'missing', operator: 'equals', value: undefined }, steps, [])).toEqual([]);
});

test('condition operator options follow field shape and retain unknown configured operators', () => {
  const steps = [{ order: 1, fields: [{ name: 'docs', field_type: 'multiupload' }, { name: 'choice', field_type: 'decision', options: [] }, { name: 'select', field_type: 'text', options: ['a'] }, { name: 'text', field_type: 'text' }] }];
  const values = condition => buildConditionOperatorOptions({ source_step_order: 1, ...condition }, steps).map(option => option.value);
  expect(values({ field: 'status', operator: 'status_is' })).toEqual(['status_is', 'status_not']);
  expect(values({ field: 'docs', operator: 'has_upload' })).toEqual(['not_empty', 'empty', 'has_upload', 'missing_upload']);
  expect(values({ field: 'choice', operator: 'equals' })).toEqual(['equals', 'not_equals', 'one_of', 'not_one_of', 'not_empty', 'empty']);
  expect(values({ field: 'select', operator: 'equals' })).toEqual(['equals', 'not_equals', 'one_of', 'not_one_of', 'not_empty', 'empty']);
  expect(values({ field: 'text', operator: 'custom' })).toEqual(['equals', 'not_equals', 'one_of', 'not_one_of', 'contains', 'not_empty', 'empty', 'custom']);
  expect(buildConditionOperatorOptions({ source_step_order: 9, field: 'missing', operator: '' }, steps).map(option => option.value)).toEqual(['equals', 'not_equals', 'one_of', 'not_one_of', 'contains', 'not_empty', 'empty']);
});

test('condition presets and section guards select only valid candidates', () => {
  const steps = [{ order: 1, fields: [] }, { order: 2, fields: [{ name: 'docs', field_type: 'multiupload', options: ['must-not-be-choice'] }] }, { order: 3, fields: [{ name: 'plain', field_type: 'text' }, { name: 'choice', field_type: 'decision', options: ['yes'] }] }];
  expect(conditionPresets(steps, 4)).toEqual({ previousStep: steps[2], uploadPresetStep: steps[1], uploadPresetField: steps[1].fields[0], choicePresetStep: steps[2], choicePresetField: steps[2].fields[1] });
  expect(conditionPresets([{ order: 1 }], 1)).toEqual({ previousStep: undefined, uploadPresetStep: undefined, uploadPresetField: undefined, choicePresetStep: undefined, choicePresetField: undefined });
  expect(conditionPresets([{ order: 1, fields: [] }, { order: 2, fields: [{ name: 'empty', field_type: 'text', options: [] }] }], 3)).toEqual({ previousStep: expect.objectContaining({ order: 2 }), uploadPresetStep: undefined, uploadPresetField: undefined, choicePresetStep: undefined, choicePresetField: undefined });
  expect(conditionPresets([{ order: 1, fields: [{ name: 'upload', field_type: 'multiupload' }] }, { order: 2, fields: [{ name: 'choice', field_type: 'text', options: [''] }] }], 3)).toEqual(expect.objectContaining({ uploadPresetField: expect.objectContaining({ name: 'upload' }), choicePresetField: expect.objectContaining({ name: 'choice' }) }));
  expect(conditionPresets([
    { order: 1, fields: [{ name: 'first-choice', field_type: 'decision', options: ['yes'] }] },
    { order: 2, fields: [{ name: 'later-upload', field_type: 'multiupload', options: ['passport'] }, { name: 'later-choice', field_type: 'radio', options: ['no'] }] },
  ], 3)).toEqual(expect.objectContaining({
    uploadPresetField: expect.objectContaining({ name: 'later-upload' }),
    choicePresetField: expect.objectContaining({ name: 'first-choice' }),
  }));
  expect(validStepSection('fields', 'display')).toBe('basic');
  expect(validStepSection('fields', 'decision')).toBe('fields');
  expect(validStepSection('fields', 'form')).toBe('fields');
  expect(validStepSection('type', 'form')).toBe('basic');
  expect(validStepSection('type', 'milestone')).toBe('type');
  expect(validStepSection('type', 'partner_selection')).toBe('type');
  expect(validStepSection('type', 'partner_multiselection')).toBe('type');
  expect(validStepSection('type', 'display')).toBe('type');
  expect(validStepSection('conditions', 'form')).toBe('conditions');
});
