import {
  CONTENT_FIELD_TYPES, DEFAULT_NOTIFICATION_PREFERENCES, applyFieldMappings, canNavigateToJourneyStep, compareRankedPartners, evaluateJourneyCondition, evaluateStepConditions,
  isStepHidden, normalizeJourneyBootstrap, optionLabel, optionValue, scorePartner, sortPartnersByRecommendation,
} from './domain';

test('normalizes the journey bootstrap at the API boundary', () => {
  expect(normalizeJourneyBootstrap()).toEqual({
    steps: [], progress: [], allStepData: [],
    notificationPreferences: DEFAULT_NOTIFICATION_PREFERENCES,
    history: [], estimatedCompletion: null,
    uiFlags: { ui_show_journey_indicator: true, ui_show_eta_header: true, ui_show_progress_percentage: true },
  });
  const payload = {
    steps: ['step'], progress: ['progress'], all_step_data: ['data'], history: ['history'],
    notification_preferences: { email_on_step_enter: false }, estimated_completion: 'tomorrow',
    settings: { ui_show_journey_indicator: false, ui_show_eta_header: null, ui_show_progress_percentage: true },
  };
  expect(normalizeJourneyBootstrap(payload)).toEqual({
    steps: ['step'], progress: ['progress'], allStepData: ['data'], history: ['history'],
    notificationPreferences: { email_on_step_enter: false }, estimatedCompletion: 'tomorrow',
    uiFlags: { ui_show_journey_indicator: false, ui_show_eta_header: true, ui_show_progress_percentage: true },
  });
  expect(normalizeJourneyBootstrap({ settings: { ui_show_eta_header: false, ui_show_progress_percentage: false } }).uiFlags).toEqual({
    ui_show_journey_indicator: true,
    ui_show_eta_header: false,
    ui_show_progress_percentage: false,
  });
});

const data = [
  { order: 1, status: 'completed', data: { text: 'hello world', choices: ['a', 'b'], uploads: [{ file_id: '1', document_type: 'A' }], empty: '' } },
  { order: 2, status: 'pending', data: { uploads: 'invalid' } },
];
const condition = (operator, value, field = 'text', order = 1) => ({ operator, value, field, source_step_order: order });

test('normalizes option values and labels', () => {
  expect(optionValue({ value: 1, label: 'One' })).toBe('1');
  expect(optionValue({ label: 'One' })).toBe('One');
  expect(optionValue({})).toBe('');
  expect(optionValue(null)).toBe('');
  expect(optionValue('plain')).toBe('plain');
  expect(optionLabel({ label: 'One', value: 1 })).toBe('One');
  expect(optionLabel({ value: 1 })).toBe('1');
  expect(optionLabel({})).toBe('');
  expect(optionLabel(undefined)).toBe('');
  expect(optionLabel(null)).toBe('');
  expect(optionLabel('plain')).toBe('plain');
  expect(CONTENT_FIELD_TYPES.has('html')).toBe(true);
});

test('allows only current, previous, completed journey destinations', () => {
  const steps = [{ id: 'a' }, { id: 'b' }, { id: 'c', conditions: [{ source_step_order: 1, operator: 'not_empty', field: 'text', action: 'block' }] }];
  expect(canNavigateToJourneyStep(steps, [], 1, data, 0)).toBe(true);
  expect(canNavigateToJourneyStep(steps, [{ step_id: 'c', status: 'completed' }], 0, data, 2)).toBe(true);
  expect(canNavigateToJourneyStep(steps, [], 0, data, 2)).toBe(false);
  expect(canNavigateToJourneyStep(steps, [], 0, [], 1)).toBe(false);
  expect(canNavigateToJourneyStep(steps, [], 0, data, 9)).toBe(false);
  expect(canNavigateToJourneyStep(steps, [{ step_id: 'a', status: 'completed' }], 0, data, 9)).toBe(false);
  expect(canNavigateToJourneyStep(steps, [{ step_id: 'wrong', status: 'completed' }, { step_id: 'b', status: 'pending' }], 0, data, 1)).toBe(false);
  expect(canNavigateToJourneyStep(steps, [], 1, data, 1)).toBe(true);
});

test('evaluates composite, scalar, list, status and unknown conditions', () => {
  expect(evaluateJourneyCondition({ all_of: [condition('contains', 'world'), condition('not_empty')] }, data)).toBe(true);
  expect(evaluateJourneyCondition({ all_of: [condition('contains', 'world'), condition('equals', 'wrong')] }, data)).toBe(false);
  expect(evaluateJourneyCondition({ any_of: [condition('equals', 'no'), condition('equals', 'hello world')] }, data)).toBe(true);
  expect(evaluateJourneyCondition({ any_of: [condition('equals', 'no'), condition('equals', 'wrong')] }, data)).toBe(false);
  expect(evaluateJourneyCondition(undefined, data)).toBe(false);
  expect(evaluateJourneyCondition(condition('equals', 'hello world'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('not_equals', 'no'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('equals', 'no'), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('not_equals', 'hello world'), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('one_of', ['b'], 'choices'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('one_of', 'hello world'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('not_one_of', ['x'], 'choices'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('not_one_of', ['a', 'x'], 'choices'), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('not_one_of', 'x'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('empty', '', 'empty'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('status_is', 'completed', null), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('status_not', 'pending', null), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('status_is', 'pending', null), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('status_not', 'completed', null), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('contains', 'missing'), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('unknown'), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('equals', 'x', 'text', 99), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('equals', '', 'missing'), [{ order: 1 }])).toBe(false);
});

test('evaluates upload conditions with and without a type', () => {
  expect(evaluateJourneyCondition(condition('has_upload', undefined, 'uploads'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('has_upload', 'A', 'uploads'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('has_upload', 'B', 'uploads'), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('missing_upload', 'B', 'uploads'), data)).toBe(true);
  expect(evaluateJourneyCondition(condition('missing_upload', 'A', 'uploads'), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('has_upload', '', 'uploads', 2), data)).toBe(false);
  expect(evaluateJourneyCondition(condition('missing_upload', '', 'uploads', 2), data)).toBe(true);
  const uploads = [{ order: 3, data: { uploads: [null, { file_id: '1', document_type: 'A' }, { file_id: '', document_type: 'A' }] } }];
  expect(evaluateJourneyCondition(condition('has_upload', null, 'uploads', 3), uploads)).toBe(true);
  expect(evaluateJourneyCondition(condition('has_upload', 'A', 'uploads', 3), uploads)).toBe(true);
  expect(evaluateJourneyCondition(condition('has_upload', 'B', 'uploads', 3), uploads)).toBe(false);
  expect(evaluateJourneyCondition(condition('missing_upload', 'A', 'uploads', 3), uploads)).toBe(false);
});

test('combines every supported step action', () => {
  const step = { conditions: [
    { ...condition('not_empty'), action: 'block' },
    { ...condition('not_empty'), action: 'hide' },
    { ...condition('not_empty'), action: 'read_only', message: 'read' },
    { ...condition('not_empty'), action: 'allow_next', message: 'go' },
    { ...condition('not_empty'), action: 'redirect', target_step_order: 4 },
    { ...condition('equals', 'never'), action: 'hide' },
  ] };
  expect(evaluateStepConditions(step, data)).toEqual({ allowed: true, blocked: true, hidden: true, readOnly: true, message: 'go', redirectStep: 4 });
  expect(evaluateStepConditions({}, data)).toEqual({ allowed: true, blocked: false, hidden: false, readOnly: false, message: '', redirectStep: null });
  expect(evaluateStepConditions({ conditions: [{ ...condition('not_empty'), action: 'read_only' }] }, data).message).toBe('');
  expect(evaluateStepConditions({ conditions: [{ ...condition('not_empty'), action: 'allow_next' }] }, data).message).toBe('');
  expect(evaluateStepConditions({ conditions: [{ ...condition('not_empty'), action: 'server_only' }] }, data).redirectStep).toBeNull();
  expect(evaluateStepConditions({ conditions: [{ ...condition('not_empty'), action: 'block' }] }, data)).toMatchObject({ allowed: false, blocked: true, message: 'Dieser Schritt ist gesperrt.' });
  expect(evaluateStepConditions({ conditions: [{ ...condition('equals', 'wrong'), action: 'hide' }] }, data).hidden).toBe(false);
  expect(isStepHidden(step, data)).toBe(true);
});

test('maps fields and ranks matching partners deterministically', () => {
  expect(applyFieldMappings({ field_mappings: [{ source_step_order: 1, source_field: 'text', target_field: 'copy' }, { source_step_order: 9, source_field: 'x', target_field: 'none' }] }, [{ order: 0, data: { text: 'wrong' } }, ...data])).toEqual({ copy: 'hello world' });
  expect(applyFieldMappings({ field_mappings: [{ source_step_order: 2, source_field: 'missing', target_field: 'none' }] }, data)).toStrictEqual({});
  expect(applyFieldMappings({ field_mappings: [{ source_step_order: 3, source_field: 'missing', target_field: 'none' }] }, [{ order: 3 }])).toStrictEqual({});
  expect(applyFieldMappings({}, data)).toEqual({});
  const profile = { fachrichtung_gewuenscht: 'Cardiology', anerkennungsverfahren_bundesland: 'Berlin' };
  expect(scorePartner({ category: 'Cardiology', tags: ['Cardiology', 'Berlin'] }, profile)).toBe(25);
  expect(scorePartner({ tags: ['Surgery'] }, { fachrichtung_praktiziert: 'Surgery' })).toBe(10);
  expect(scorePartner({ category: 'Medicine' }, { field_of_study: 'Medicine' })).toBe(10);
  expect(scorePartner({}, null)).toBe(0);
  expect(scorePartner({}, { fachrichtung_gewuenscht: 'Stryker was here!' })).toBe(0);
  expect(scorePartner({ tags: ['Hamburg'] }, { anerkennungsverfahren_bundesland: 'Berlin' })).toBe(0);
  const ranked = sortPartnersByRecommendation([{ name: 'Zulu' }, { name: 'Alpha', tags: ['Berlin'] }], profile);
  expect(ranked.map(item => item.name)).toEqual(['Alpha', 'Zulu']);
  expect(compareRankedPartners({ _score: 0 }, { _score: 0, name: 'Alpha' })).toBeLessThan(0);
  expect(compareRankedPartners({ _score: 0, name: 'Alpha' }, { _score: 0 })).toBeGreaterThan(0);
  expect(compareRankedPartners({ _score: 1, name: 'Zulu' }, { _score: 0, name: 'Alpha' })).toBeLessThan(0);
});
