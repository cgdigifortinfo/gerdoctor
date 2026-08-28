import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import SurveyFormBuilder, { createField, FieldPreview, FieldSettings, moveField, OptionEditor, optionLabel, optionValue, slugify } from './SurveyFormBuilder';

jest.mock('../ui/select', () => ({
  Select: ({ children, onValueChange, value }) => <div>{children}<button type="button" data-testid="mock-select" onClick={() => onValueChange(String(value) === '2' ? '3' : 'half')}>select value</button></div>,
  SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children }) => <span>{children}</span>,
  SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => <span>value</span>,
}));
jest.mock('../ui/switch', () => ({ Switch: ({ checked, onCheckedChange, ...props }) => <button type="button" aria-pressed={checked} onClick={() => onCheckedChange(!checked)} {...props}>switch</button> }));
jest.mock('../ui/help-tooltip', () => ({ HelpTooltip: ({ content, testId }) => content ? <span data-testid={testId}>{content}</span> : null, HelpLabel: ({ children }) => <>{children}</> }));

test('field factory and scalar helpers cover every supported field shape', () => {
  expect(slugify('  Hello World! ')).toBe('hello_world');
  expect(slugify(null)).toBe('');
  expect(optionValue({ value: 0, label: 'zero' })).toBe('0');
  expect(optionValue({ label: 'label' })).toBe('label');
  expect(optionValue({})).toBe('');
  expect(optionValue(null)).toBe('');
  expect(optionLabel({ label: '', value: 'value' })).toBe('');
  expect(optionLabel({ value: 'value' })).toBe('value');
  expect(optionLabel({})).toBe('');
  expect(optionLabel('plain')).toBe('plain');
  expect(optionLabel(null)).toBe('');
  const types = ['text', 'textarea', 'email', 'phone', 'number', 'date', 'time', 'checkbox', 'selectbox', 'radio', 'multiselect', 'decision', 'file', 'multiupload', 'heading', 'paragraph', 'html', 'image', 'divider', 'unknown'];
  const fields = Object.fromEntries(types.map((type, index) => [type, createField(type, index)]));
  expect(fields.text.name).toContain('textfeld');
  expect(fields.unknown.label).toBe('Neues Feld');
  expect(fields.decision.options).toEqual(['Option 1', 'Option 2']);
  expect(fields.multiupload.multiple).toBe(true);
  expect(fields.file.multiple).toBe(false);
  expect(fields.textarea.rows).toBe(4);
  expect(fields.heading.heading_level).toBe(2);
  expect(fields.paragraph.content).toContain('erklärender');
  expect(fields.html.content).toContain('<p>');
  expect(fields.image.caption).toBe('');
  expect(fields.divider.required).toBe(false);
  expect(createField('text').name).toBe('textfeld_1');
  const rows = [{ id: 1 }, { id: 2 }];
  expect(moveField(rows, 0, -1)).toBe(rows);
  expect(moveField(rows, 1, 1)).toBe(rows);
  expect(moveField(rows, 0, 1)).toEqual([{ id: 2 }, { id: 1 }]);
});

test('field previews render every content and input variant with fallbacks', () => {
  const fields = [
    { field_type: 'divider' }, { field_type: 'heading', heading_level: 3, content: 'Heading' },
    { field_type: 'heading', label: 'Fallback heading' }, { field_type: 'paragraph', content: '<b>Paragraph</b>' },
    { field_type: 'html', name: 'html-name' }, { field_type: 'image', image_url: 'x.png', alt_text: 'Alt' }, { field_type: 'image', image_url: 'y.png' },
    { field_type: 'image' }, { field_type: 'decision', label: 'Choice', required: true, options: [{ label: 'One' }, '', 'Two'] },
    { field_type: 'multiupload', options: [] }, { field_type: 'selectbox' }, { field_type: 'unknown', name: 'Technical name' }, { field_type: 'textarea', placeholder: '' },
    { field_type: 'checkbox' }, { field_type: 'file' }, { field_type: 'text', placeholder: 'Type here', help_text: 'Help' },
  ];
  render(<>{fields.map((field, index) => <div key={index}><FieldPreview field={field} /></div>)}</>);
  expect(screen.getByText('Heading').tagName).toBe('H3');
  expect(screen.getByText('Paragraph')).toBeInTheDocument();
  expect(screen.getByAltText('Alt')).toBeInTheDocument();
  expect(screen.getByText('Bildvorschau')).toBeInTheDocument();
  expect(screen.getAllByText('Optionen ergänzen').length).toBeGreaterThan(0);
  expect(screen.getByText('Help')).toBeInTheDocument();
});

test('option editor updates primitive and decision options, adds and removes', () => {
  const update = jest.fn();
  const { rerender } = render(<OptionEditor field={{ field_type: 'selectbox' }} updateField={update} />);
  expect(screen.queryByLabelText('Bezeichnung Option 1')).not.toBeInTheDocument();
  rerender(<OptionEditor field={{ field_type: 'decision', options: ['old', { value: 'v', label: 'L' }] }} updateField={update} />);
  fireEvent.change(screen.getByLabelText('Wert Option 1'), { target: { value: 'new-value' } });
  fireEvent.change(screen.getByLabelText('Bezeichnung Option 1'), { target: { value: 'New label' } });
  fireEvent.change(screen.getByLabelText('Bezeichnung Option 2'), { target: { value: 'Changed' } });
  fireEvent.click(screen.getByText('Option', { selector: 'button' }));
  fireEvent.click(screen.getByLabelText('Option 1 löschen'));
  expect(update).toHaveBeenCalledTimes(5);
  rerender(<OptionEditor field={{ field_type: 'selectbox', options: ['A'] }} updateField={update} />);
  fireEvent.change(screen.getByLabelText('Bezeichnung Option 1'), { target: { value: 'B' } });
  fireEvent.click(screen.getByText('Option', { selector: 'button' }));
  expect(update).toHaveBeenLastCalledWith({ options: ['A', 'Option 2'] });
  rerender(<OptionEditor field={{ field_type: 'selectbox', options: [{ value: 'A', label: 'Alpha' }] }} updateField={update} />);
  fireEvent.change(screen.getByLabelText('Bezeichnung Option 1'), { target: { value: 'Beta' } });
});

function exerciseSettings(field) {
  const change = jest.fn();
  const view = render(<FieldSettings field={field} onChange={change} />);
  for (const input of screen.queryAllByRole('textbox')) fireEvent.change(input, { target: { value: input.type === 'number' ? '5' : 'Changed Value' } });
  for (const input of view.container.querySelectorAll('input[type="number"]')) {
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.change(input, { target: { value: '5' } });
  }
  for (const button of screen.queryAllByText('switch')) fireEvent.click(button);
  for (const button of screen.queryAllByTestId('mock-select')) fireEvent.click(button);
  view.unmount();
  return change;
}

test('field settings covers empty, content, constraints, uploads and image settings', () => {
  const empty = render(<FieldSettings field={null} onChange={jest.fn()} />);
  expect(screen.getByText(/Wähle ein Feld/)).toBeInTheDocument(); empty.unmount();
  const cases = [
    { field_type: 'text', name: 'name', label: 'Text', width: 'full', min_length: 1, max_length: 5 },
    { field_type: 'textarea', name: 'area', label: 'Area', rows: 3 },
    { field_type: 'number', name: 'number', label: 'Number', min: 1, max: 9, step: 2 },
    { field_type: 'number', name: 'empty-number', label: 'Empty number' },
    { field_type: 'checkbox', name: 'check', label: 'Check' },
    { field_type: 'file', name: 'file', label: 'File', accept: '.pdf', multiple: false },
    { field_type: 'multiupload', name: 'multi', label: 'Multi', options: ['Doc'] },
    { field_type: 'decision', name: 'decision', label: 'Decision', options: [{ value: 'v', label: 'V' }] },
    { field_type: 'heading', label: 'Heading', content: 'Content', heading_level: 2 },
    { field_type: 'heading', label: '', content: '', heading_level: 0 },
    { field_type: 'paragraph', label: 'Paragraph', content: 'Content' },
    { field_type: 'html', label: 'Html', content: '<p>x</p>' },
    { field_type: 'image', label: 'Image', image_url: '', alt_text: '', caption: '' },
    { field_type: 'divider' },
    { field_type: 'unknown', name: '', label: '' },
  ];
  for (const field of cases) exerciseSettings(field);
});

test('form builder adds, filters, selects, reorders, duplicates, deletes and resets fields', () => {
  const initial = [{ id: 'a', name: 'a', field_type: 'text', label: 'A' }, { id: 'b', name: 'b', field_type: 'textarea', label: 'B' }];
  const change = jest.fn();
  const { rerender } = render(<SurveyFormBuilder fields={initial} onChange={change} />);
  expect(screen.getByText('2 Elemente')).toBeInTheDocument();
  fireEvent.change(screen.getByTestId('builder-field-label'), { target: { value: 'Updated' } });
  fireEvent.change(screen.getByTestId('form-builder-search'), { target: { value: 'heading' } });
  expect(screen.getByTestId('add-field-heading')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('add-field-heading'));
  fireEvent.click(screen.getAllByLabelText('Nach unten')[0]);
  fireEvent.click(screen.getAllByLabelText('Nach oben')[1]);
  fireEvent.click(screen.getAllByLabelText('Duplizieren')[0]);
  fireEvent.click(screen.getAllByLabelText('Löschen')[0]);
  fireEvent.click(screen.getByTestId('builder-field-1'));
  fireEvent.keyDown(screen.getByTestId('builder-field-0'), { key: 'Enter' });
  fireEvent.keyDown(screen.getByTestId('builder-field-0'), { key: 'Space' });
  expect(change).toHaveBeenCalled();
  rerender(<SurveyFormBuilder fields={[initial[1]]} onChange={change} />);
  expect(screen.getByText('1 Element')).toBeInTheDocument();
  rerender(<SurveyFormBuilder fields={[]} onChange={change} />);
  expect(screen.getByText('Noch keine Formularfelder')).toBeInTheDocument();
});

test('form builder supports name-only and sparse field identities and duplicate fallbacks', () => {
  const change = jest.fn();
  const sparse = [{ name: 'named', field_type: 'unknown' }, { field_type: 'unknown' }];
  render(<SurveyFormBuilder fields={sparse} onChange={change} />);
  fireEvent.click(screen.getAllByLabelText('Duplizieren')[1]);
  expect(change).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({ name: 'unknown_kopie' })]));
});

test('form builder supports default empty fields', () => {
  render(<SurveyFormBuilder onChange={jest.fn()} />);
  expect(screen.getByText('0 Elemente')).toBeInTheDocument();
});
