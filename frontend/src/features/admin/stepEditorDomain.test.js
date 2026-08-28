import { CONDITION_ACTION_OPTIONS, CONDITION_OPERATOR_OPTIONS, STEP_STATUS_OPTIONS, conditionActionUpdate, conditionDisplayValue, conditionFieldUpdate, conditionGroupKey, conditionMultiValue, conditionOperatorUpdate, conditionScalarValue, conditionSourceUpdate, conditionValueMode, optionLabel, optionValue, stepFieldOptions, withFallbackOption } from './stepEditorDomain';

test('step editor option helpers normalize every supported option shape', () => {
  expect(STEP_STATUS_OPTIONS).toHaveLength(5); expect(CONDITION_OPERATOR_OPTIONS).toHaveLength(11); expect(CONDITION_ACTION_OPTIONS).toHaveLength(6);
  expect(optionValue('x')).toBe('x'); expect(optionValue({ value: 'v', label: 'l' })).toBe('v'); expect(optionValue({ label: 'l' })).toBe('l'); expect(optionValue(null)).toBe('');
  expect(optionLabel('x')).toBe('x'); expect(optionLabel({ label: 'l', value: 'v' })).toBe('l'); expect(optionLabel({ value: 'v' })).toBe('v'); expect(optionLabel(undefined)).toBe('');
});

test('condition domain creates unambiguous group, source and action updates', () => {
  expect(conditionGroupKey({ all_of: [] })).toBe('all_of');
  expect(conditionGroupKey({ any_of: [] })).toBe('any_of');
  expect(conditionGroupKey({ all_of: null, any_of: null })).toBeNull();
  expect(conditionActionUpdate('redirect', 7)).toEqual({ action: 'redirect', target_step_order: 7 });
  expect(conditionActionUpdate('block', 7)).toEqual({ action: 'block', target_step_order: null });
  expect(conditionSourceUpdate('2')).toEqual({ source_step_order: 2, field: 'status', operator: 'status_is', value: 'completed' });
  expect(conditionSourceUpdate('')).toEqual({ source_step_order: null, field: 'status', operator: 'status_is', value: 'completed' });
});

test('condition field updates select the matching operator and initial value', () => {
  expect(conditionFieldUpdate('status')).toEqual({ field: 'status', operator: 'status_is', value: 'completed' });
  expect(conditionFieldUpdate('upload', { field_type: 'multiupload' })).toEqual({ field: 'upload', operator: 'has_upload', value: '' });
  expect(conditionFieldUpdate('partner_uploads')).toEqual({ field: 'partner_uploads', operator: 'has_upload', value: '' });
  expect(conditionFieldUpdate('choice', { options: [{ value: 'a' }] })).toEqual({ field: 'choice', operator: 'equals', value: 'a' });
  expect(conditionFieldUpdate('choice', { options: [] })).toEqual({ field: 'choice', operator: 'equals', value: '' });
  expect(conditionFieldUpdate('choice', {})).toEqual({ field: 'choice', operator: 'equals', value: '' });
  expect(conditionFieldUpdate('choice')).toEqual({ field: 'choice', operator: 'equals', value: '' });
});

test('condition editor values preserve list and scalar shapes', () => {
  expect(conditionMultiValue(['a'])).toEqual(['a']);
  expect(conditionMultiValue('a')).toEqual(['a']);
  expect(conditionMultiValue('')).toEqual([]);
  expect(conditionMultiValue(null)).toEqual([]);
  expect(conditionScalarValue(['a', 'b'])).toBe('a');
  expect(conditionScalarValue([])).toBe('');
  expect(conditionScalarValue('a')).toBe('a');
  expect(conditionScalarValue(null)).toBe('');
  expect(conditionValueMode('empty', true)).toBe('none');
  expect(conditionValueMode('not_empty', false)).toBe('none');
  expect(conditionValueMode('one_of', false)).toBe('multi');
  expect(conditionValueMode('not_one_of', true)).toBe('multi');
  expect(conditionValueMode('equals', true)).toBe('select');
  expect(conditionValueMode('equals', false)).toBe('input');
});

test.each([
  ['one_of', 'a', ['a']], ['not_one_of', '', []], ['one_of', ['a'], ['a']],
  ['equals', ['a', 'b'], 'a'], ['equals', [], ''], ['equals', 'a', 'a'],
  ['empty', ['a'], ''], ['not_empty', 'a', ''], ['has_upload', 'a', ''], ['missing_upload', 'a', ''],
])('condition operator %s normalizes %p to %p', (operator, currentValue, value) => {
  expect(conditionOperatorUpdate(operator, currentValue)).toEqual({ operator, value });
});

test('condition summaries distinguish document, list, scalar and absent values', () => {
  expect(conditionDisplayValue('has_upload', null)).toBe('beliebiges Dokument');
  expect(conditionDisplayValue('missing_upload', '')).toBe('beliebiges Dokument');
  expect(conditionDisplayValue('has_upload', 'passport')).toBe('passport');
  expect(conditionDisplayValue('equals', ['a', 'b'])).toBe('a, b');
  expect(conditionDisplayValue('equals', 0)).toBe('0');
  expect(conditionDisplayValue('equals', null)).toBe('–');
});

test('step field options cover status, fields, milestone uploads and fallbacks', () => {
  expect(stepFieldOptions(undefined, false)).toEqual([]);
  expect(stepFieldOptions({ fields: [{ name: 'plain' }, { name: 'named', label: 'Named', field_type: 'text' }] })).toEqual([
    { value: 'status', label: 'Schrittstatus', description: 'Systemfeld · pending, in_progress, completed …', keywords: 'status abgeschlossen ausstehend system' },
    { value: 'plain', label: 'plain', description: 'plain · Feld', keywords: 'plain ' },
    { value: 'named', label: 'Named', description: 'named · text', keywords: 'named text' },
  ]);
  const milestone = stepFieldOptions({ step_type: 'milestone', fields: [] });
  expect(milestone.at(-1)).toEqual({ value: 'partner_uploads', label: 'Partner-Dokumente', description: 'Systemfeld · vom Partner hochgeladene Dokumente', keywords: 'partner uploads dokumente system' });
  const existing = stepFieldOptions({ step_type: 'milestone', fields: [{ name: 'partner_uploads', field_type: 'multiupload' }] }); expect(existing.filter(option => option.value === 'partner_uploads')).toHaveLength(1);
  const options = [{ value: 1, label: 'One' }];
  expect(withFallbackOption(options, null)).toBe(options); expect(withFallbackOption(options, '')).toBe(options); expect(withFallbackOption(options, '1')).toBe(options);
  expect(withFallbackOption(options, 'missing')).toEqual([...options, { value: 'missing', label: 'Bestehender Wert: missing' }]);
  expect(withFallbackOption([], 'x', 'Fehlt')).toEqual([{ value: 'x', label: 'Fehlt: x' }]);
});
