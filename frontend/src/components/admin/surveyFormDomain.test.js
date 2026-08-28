import {
  appendFieldOption, createField, duplicateField, moveField, optionLabel, optionValue,
  removeFieldOption, slugify, updateFieldOption,
} from './surveyFormDomain';

test('normalizes field names and option values without nullable output', () => {
  expect(slugify(undefined)).toBe('');
  expect(slugify(' A & B ')).toBe('a_b');
  expect(slugify('___A___')).toBe('a');
  expect(optionValue({ value: 0, label: 'Zero' })).toBe('0');
  expect(optionValue({ label: 'Label' })).toBe('Label');
  expect(optionValue({})).toBe('');
  expect(optionValue(null)).toBe('');
  expect(optionLabel({ label: '', value: 'Value' })).toBe('');
  expect(optionLabel({ value: 'Value' })).toBe('Value');
  expect(optionLabel({})).toBe('');
  expect(optionLabel(undefined)).toBe('');
});

test.each([
  ['text', {}],
  ['decision', { options: ['Option 1', 'Option 2'] }],
  ['multiupload', { options: ['Dokument'], multiple: true }],
  ['file', { multiple: false }],
  ['textarea', { rows: 4 }],
  ['heading', { content: 'Neue Überschrift', heading_level: 2 }],
  ['paragraph', { content: 'Hier kann ein erklärender Text stehen.' }],
  ['html', { content: '<p>Hier kann formatierter Inhalt stehen.</p>' }],
  ['image', { image_url: '', alt_text: '', caption: '' }],
  ['unknown', { label: 'Neues Feld' }],
])('creates a complete %s field', (type, expected) => {
  const field = createField(type, 2);
  expect(field).toMatchObject({ field_type: type, required: false, width: 'full', ...expected });
  if (!['decision', 'select', 'selectbox', 'radio', 'multiselect', 'multiupload'].includes(type)) expect(field).not.toHaveProperty('options');
  if (type !== 'textarea') expect(field).not.toHaveProperty('rows');
  if (!['heading', 'paragraph', 'html'].includes(type)) expect(field).not.toHaveProperty('content');
  if (type !== 'image') expect(field).not.toHaveProperty('image_url');
});

test('applies immutable option and field list operations', () => {
  const primitives = ['A', 'B'];
  expect(updateFieldOption(primitives, 'selectbox', 0, 'label', 'C')).toEqual(['C', 'B']);
  expect(updateFieldOption([{ value: 'a', label: 'A' }], 'decision', 0, 'value', 'b')).toEqual([{ value: 'b', label: 'A' }]);
  expect(updateFieldOption([{ value: 'a', label: 'A' }], 'selectbox', 0, 'label', 'Alpha')).toEqual([{ value: 'a', label: 'Alpha' }]);
  expect(updateFieldOption(['A'], 'decision', 0, 'label', 'Alpha')).toEqual([{ value: 'A', label: 'Alpha' }]);
  expect(updateFieldOption([null], 'decision', 0, 'label', 'Alpha')).toEqual([{ value: '', label: 'Alpha' }]);
  expect(appendFieldOption(primitives, 'selectbox')).toEqual(['A', 'B', 'Option 3']);
  expect(appendFieldOption([], 'decision')).toEqual([{ value: 'option_1', label: 'Option 1' }]);
  expect(removeFieldOption(primitives, 0)).toEqual(['B']);
  expect(primitives).toEqual(['A', 'B']);

  const fields = [{ id: 'a', name: 'a', label: 'A', field_type: 'text' }, { id: 'b' }];
  expect(moveField(fields, 0, -1)).toBe(fields);
  expect(moveField(fields, 1, 1)).toBe(fields);
  expect(moveField(fields, 0, 1)).toEqual([fields[1], fields[0]]);
  expect(moveField(fields, 1, -1)).toEqual([fields[1], fields[0]]);
  const duplicate = duplicateField(fields, 0);
  expect(duplicate.fields).toHaveLength(3);
  expect(duplicate.fields[1]).toMatchObject({ name: 'a_kopie', label: 'A (Kopie)' });
  expect(duplicate.selectedId).toBe(duplicate.fields[1].id);
  const fallback = duplicateField([{ field_type: 'text' }], 0);
  expect(fallback.fields[1]).toMatchObject({ name: 'text_kopie', label: 'Textfeld (Kopie)' });
  expect(createField('text').name).toBe('textfeld_1');
});
