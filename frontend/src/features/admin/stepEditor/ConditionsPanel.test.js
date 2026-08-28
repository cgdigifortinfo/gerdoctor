import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { ConditionsPanel } from './ConditionsPanel';

let mockSelectProps = [];
let mockSelectItemProps = [];
let mockSearchableProps = [];
let mockMultiProps = [];
let mockHelpProps = [];

jest.mock('../../../components/ui/select', () => ({
  Select: props => { mockSelectProps.push(props); return <div>{props.children}{['one_of','equals','empty','redirect'].map(value => <button key={value} data-testid={`select-${value}`} onClick={() => props.onValueChange(value)}>{value}</button>)}</div>; },
  SelectContent: ({ children }) => <>{children}</>, SelectItem: props => { mockSelectItemProps.push(props); return <span>{props.children}</span>; }, SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => null,
}));
jest.mock('../../../components/admin/EntityPickers', () => ({
  SearchableSelect: props => { mockSearchableProps.push(props); return <div data-testid={props.testId}>{['', '2', 'status', 'partner_uploads', 'normal'].map((value, index) => <button key={`${value}-${index}`} onClick={() => props.onChange(value)}>{value || 'empty'}</button>)}</div>; },
  SearchableMultiSelect: props => { mockMultiProps.push(props); return <button data-testid={props.testId} onClick={() => props.onChange(['a','b'])}>multi</button>; },
}));
jest.mock('../../../components/ui/help-tooltip', () => ({ HelpLabel: props => { mockHelpProps.push(props); return <>{props.children}</>; } }));
jest.mock('@phosphor-icons/react', () => ({ Plus: () => null, Trash: () => null }));

const callbacks = () => ({
  addCondition: jest.fn(), addConditionGroup: jest.fn(), addConditionPreset: jest.fn(), removeCondition: jest.fn(), changeConditionGroupType: jest.fn(), addConditionChild: jest.fn(), updateConditionChild: jest.fn(), removeConditionChild: jest.fn(), updateCondition: jest.fn(), changeConditionSource: jest.fn(), changeConditionField: jest.fn(), changeConditionOperator: jest.fn(),
  findStepByOrder: jest.fn(order => order === 1 ? { title: 'Source' } : undefined),
  findField: jest.fn((_step, name) => name === 'partner_uploads' ? { field_type: 'multiupload' } : name === 'normal' ? { field_type: 'select', options: [{ value: 'first' }] } : undefined),
  sourceFieldOptions: jest.fn(() => []), conditionOperatorOptions: jest.fn(() => [{ value: 'equals', label: 'Equals' }]),
  conditionValueOptions: jest.fn(condition => condition.options ? [{ value: 'a', label: 'A' }] : []),
});

const baseProps = cb => ({ ...cb, previousStep: { order: 1, title: 'Previous' }, uploadPresetStep: { order: 2 }, uploadPresetField: { name: 'files', options: ['passport'] }, choicePresetStep: { order: 3 }, choicePresetField: { name: 'choice', options: ['a','b','c'] }, sortedReferenceSteps: [{ order: 1 }, { order: 5 }], stepOptions: [], formData: { order: 2, conditions: [] } });
const observableProps = props => Object.fromEntries(Object.entries(props).filter(([key]) => !['children', 'onChange', 'onValueChange'].includes(key)));

beforeEach(() => {
  mockSelectProps = []; mockSelectItemProps = []; mockSearchableProps = []; mockMultiProps = []; mockHelpProps = [];
});

test('conditions panel covers empty state, creation commands and every preset', () => {
  const cb = callbacks();
  const { container } = render(<ConditionsPanel {...baseProps(cb)} />);
  expect(screen.getByText(/Keine Regeln konfiguriert/)).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('add-condition')); fireEvent.click(screen.getByTestId('add-condition-all')); fireEvent.click(screen.getByTestId('add-condition-any'));
  screen.getAllByTestId(/condition-preset-/).forEach(button => fireEvent.click(button));
  expect(cb.addCondition).toHaveBeenCalledTimes(1); expect(cb.addConditionGroup.mock.calls).toEqual([['all_of'], ['any_of']]);
  expect(cb.addConditionPreset.mock.calls).toEqual([
    [{ source_step_order: 1, field: 'status', operator: 'status_not', value: 'completed', action: 'block', message: 'Bitte schließen Sie zuerst „Previous“ ab.' }],
    [{ source_step_order: 2, field: 'files', operator: 'missing_upload', value: 'passport', action: 'block', message: 'Bitte laden Sie zuerst das erforderliche Dokument hoch.' }],
    [{ source_step_order: 3, field: 'choice', operator: 'one_of', value: ['a', 'b'], action: 'allow_next', message: '' }],
    [{ source_step_order: 1, field: 'status', operator: 'status_is', value: 'completed', action: 'redirect', target_step_order: 5, message: '' }],
  ]);
  expect(screen.getByText('Schnellstart mit sinnvoll vorbelegten Regeln')).toBeInTheDocument();
  expect(mockHelpProps).toEqual([expect.objectContaining({ children: 'Regeln für diesen Schritt', help: 'Jede Regel liest einen anderen Step. Mehrere Regeln werden unabhängig ausgewertet; jede zutreffende Aktion kann auf diesen Step wirken.' })]);
  expect(container).toMatchSnapshot();
});

test('preset fallbacks preserve empty option values and a missing redirect target', () => {
  const cb = callbacks();
  render(<ConditionsPanel {...baseProps(cb)} uploadPresetField={{ name: 'files', options: [] }} choicePresetField={{ name: 'choice' }} sortedReferenceSteps={[{ order: 1 }]} />);
  screen.getAllByTestId(/condition-preset-/).forEach(button => fireEvent.click(button));
  expect(cb.addConditionPreset.mock.calls[1][0]).toEqual({ source_step_order: 2, field: 'files', operator: 'missing_upload', value: '', action: 'block', message: 'Bitte laden Sie zuerst das erforderliche Dokument hoch.' });
  expect(cb.addConditionPreset.mock.calls[2][0]).toEqual({ source_step_order: 3, field: 'choice', operator: 'one_of', value: [], action: 'allow_next', message: '' });
  expect(cb.addConditionPreset.mock.calls[3][0]).toEqual({ source_step_order: 1, field: 'status', operator: 'status_is', value: 'completed', action: 'redirect', target_step_order: null, message: '' });
});

test('presets distinguish undefined options and steps at the current order', () => {
  const cb = callbacks();
  render(<ConditionsPanel {...baseProps(cb)} uploadPresetField={{ name: 'files' }} sortedReferenceSteps={[{ order: 2 }, { order: 3 }]} />);
  fireEvent.click(screen.getByTestId('condition-preset-1'));
  fireEvent.click(screen.getByTestId('condition-preset-3'));
  expect(cb.addConditionPreset.mock.calls).toEqual([
    [{ source_step_order: 2, field: 'files', operator: 'missing_upload', value: '', action: 'block', message: 'Bitte laden Sie zuerst das erforderliche Dokument hoch.' }],
    [{ source_step_order: 1, field: 'status', operator: 'status_is', value: 'completed', action: 'redirect', target_step_order: 3, message: '' }],
  ]);
});

test('conditions panel covers absent presets and redirect without later target', () => {
  const cb = callbacks();
  render(<ConditionsPanel {...baseProps(cb)} previousStep={null} uploadPresetStep={null} uploadPresetField={null} choicePresetStep={null} choicePresetField={null} sortedReferenceSteps={[]} />);
  expect(screen.queryByTestId(/condition-preset-/)).not.toBeInTheDocument();
  const { rerender } = render(<ConditionsPanel {...baseProps(cb)} uploadPresetStep={{ order: 2 }} uploadPresetField={null} choicePresetStep={{ order: 3 }} choicePresetField={null} />);
  rerender(<ConditionsPanel {...baseProps(cb)} previousStep={{ order: 1, title: 'P' }} sortedReferenceSteps={[]} />);
});

test('conditions panel renders and operates simple conditions in all value modes', () => {
  const cb = callbacks();
  const conditions = [
    { source_step_order: null, field: '', operator: 'empty', value: null, action: 'block', message: '' },
    { source_step_order: 1, field: 'choice', operator: 'one_of', value: 'a', action: 'redirect', target_step_order: null, options: true },
    { source_step_order: 1, field: 'choice', operator: 'not_one_of', value: ['a'], action: 'hide', options: true },
    { source_step_order: 9, field: 'text', operator: 'equals', value: ['x'], action: 'unknown', options: true },
    { source_step_order: 1, field: 'text', operator: 'equals', value: '', action: 'allow_next' },
    { source_step_order: 1, field: 'choice', operator: 'one_of', value: null, action: 'block', options: true },
    { source_step_order: 1, field: 'choice', operator: 'equals', value: [], action: 'block', options: true },
    { source_step_order: 1, field: 'choice', operator: 'equals', value: ['a'], action: 'block', options: true },
    { source_step_order: 1, field: 'choice', operator: 'equals', value: 'a', action: 'block', options: true },
    { source_step_order: 1, field: 'choice', operator: 'equals', value: '', action: 'block', options: true },
  ];
  render(<ConditionsPanel {...baseProps(cb)} formData={{ order: 2, conditions }} />);
  screen.getAllByText('Entfernen').forEach(button => fireEvent.click(button));
  screen.getAllByTestId(/condition-source-step-/).forEach(box => fireEvent.click(box.querySelectorAll('button')[1]));
  screen.getAllByTestId(/condition-source-field-/).forEach(box => fireEvent.click(box.querySelectorAll('button')[2]));
  screen.getAllByTestId(/condition-values-/).forEach(button => fireEvent.click(button));
  screen.getAllByTestId(/condition-value-\d/).forEach(box => { if (box.tagName === 'DIV') fireEvent.click(box.querySelectorAll('button')[1]); });
  screen.getAllByTestId(/condition-value-input-/).forEach(input => fireEvent.change(input, { target: { value: 'typed' } }));
  screen.getAllByTestId(/condition-message-/).forEach(input => fireEvent.change(input, { target: { value: 'message' } }));
  const target = screen.getByTestId('condition-target-step-1'); fireEvent.click(target.querySelectorAll('button')[0]); fireEvent.click(target.querySelectorAll('button')[1]);
  screen.getAllByTestId('select-redirect').forEach(button => fireEvent.click(button));
  screen.getAllByTestId('select-equals').forEach(button => fireEvent.click(button));
  expect(cb.removeCondition).toHaveBeenCalledTimes(conditions.length); expect(cb.changeConditionSource).toHaveBeenCalled(); expect(cb.changeConditionField).toHaveBeenCalled(); expect(cb.changeConditionOperator).toHaveBeenCalled(); expect(cb.updateCondition).toHaveBeenCalled();
});

test('conditions panel covers AND and OR compound children and editors', () => {
  const cb = callbacks();
  const children = [
    { source_step_order: null, field: '', operator: 'has_upload', value: '', options: true },
    { source_step_order: 1, field: 'choice', operator: 'one_of', value: 'a', options: true },
    { source_step_order: 9, field: 'text', operator: 'equals', value: ['x'] },
    { source_step_order: 1, field: 'text', operator: 'not_empty', value: null },
    { source_step_order: 1, field: 'choice', operator: 'one_of', value: null, options: true },
    { source_step_order: 1, field: 'choice', operator: 'equals', value: [], options: true },
  ];
  const conditions = [{ all_of: children, action: 'redirect', message: '', target_step_order: 5 }, { any_of: [{ source_step_order: 1, field: 'x', operator: 'missing_upload', value: 'passport' }], action: 'unknown' }];
  render(<ConditionsPanel {...baseProps(cb)} formData={{ order: 2, conditions }} />);
  fireEvent.click(screen.getByTestId('condition-add-child-0')); fireEvent.click(screen.getAllByText('Entfernen')[0]);
  screen.getAllByTestId(/condition-child-source-/).forEach(box => { fireEvent.click(box.querySelectorAll('button')[0]); fireEvent.click(box.querySelectorAll('button')[1]); });
  screen.getAllByTestId(/condition-child-field-/).forEach(box => box.querySelectorAll('button').forEach(button => fireEvent.click(button)));
  screen.getAllByTestId(/condition-child-operator-/).forEach(trigger => trigger.parentElement.querySelectorAll('button').forEach(button => fireEvent.click(button)));
  screen.getAllByTestId(/condition-child-values-/).forEach(button => fireEvent.click(button));
  screen.getAllByTestId(/condition-child-value-\d/).forEach(box => { if (box.tagName === 'DIV') fireEvent.click(box.querySelectorAll('button')[1]); });
  screen.getAllByTestId(/condition-child-value-input-/).forEach(input => fireEvent.change(input, { target: { value: 'typed' } }));
  screen.getAllByTestId(/condition-remove-child-/).forEach(button => fireEvent.click(button));
  screen.getAllByTestId(/condition-group-type-/).forEach(() => screen.getAllByTestId('select-one_of').forEach(button => fireEvent.click(button)));
  screen.getAllByTestId(/condition-message-/).forEach(input => fireEvent.change(input, { target: { value: 'message' } }));
  screen.getAllByTestId('select-redirect').forEach(button => fireEvent.click(button)); screen.getAllByTestId('select-equals').forEach(button => fireEvent.click(button));
  expect(cb.updateConditionChild).toHaveBeenCalled(); expect(cb.removeConditionChild).toHaveBeenCalled(); expect(cb.changeConditionGroupType).toHaveBeenCalled(); expect(cb.addConditionChild).toHaveBeenCalled();
});

test('conditions panel covers empty preset options and missing compound metadata', () => {
  const cb = callbacks();
  const conditions = [{ all_of: [{ source_step_order: 9, field: '', operator: undefined, value: undefined }, { source_step_order: 1, field: 'choice', operator: 'one_of', value: [''] }], action: 'redirect', target_step_order: null, message: '' }, { source_step_order: 1, field: 'choice', operator: 'equals', value: [''], action: 'redirect', target_step_order: 0 }];
  const { container } = render(<ConditionsPanel {...baseProps(cb)} uploadPresetField={{ name: 'files', options: [] }} choicePresetField={{ name: 'choice' }} formData={{ order: 9, conditions }} sortedReferenceSteps={[{ order: 1 }]} />);
  screen.getAllByTestId(/condition-child-value-input-/).forEach(input => fireEvent.change(input, { target: { value: 'x' } })); screen.getAllByTestId(/condition-target-step-/).forEach(box => fireEvent.click(box.querySelectorAll('button')[0]));
  expect(container).toMatchSnapshot();
  expect(mockSearchableProps.map(observableProps)).toMatchSnapshot();
  expect(mockMultiProps.map(observableProps)).toMatchSnapshot();
});

test('simple condition exposes the exact editor contract and emits exact updates', () => {
  const cb = callbacks();
  cb.sourceFieldOptions.mockReturnValue([{ value: 'status', label: 'Status' }]);
  cb.conditionOperatorOptions.mockReturnValue([{ value: 'equals', label: 'Equals' }]);
  cb.conditionValueOptions.mockReturnValue([{ value: 'a', label: 'A' }]);
  const condition = { source_step_order: 1, field: 'choice', operator: 'equals', value: ['a'], action: 'redirect', target_step_order: 5, message: 'Hinweis' };
  const { container } = render(<ConditionsPanel {...baseProps(cb)} stepOptions={[{ value: '1', label: 'One' }, { value: '5', label: 'Five' }]} formData={{ order: 2, conditions: [condition] }} />);

  expect(screen.getByText('Regel 1')).toBeInTheDocument();
  expect(screen.getByText((_, element) => element.tagName === 'P' && element.textContent === 'Bei Treffer: Zu anderem Schritt weiterleiten')).toBeInTheDocument();
  expect(mockSearchableProps.map(({ testId, value, placeholder, searchPlaceholder, allowCustom }) => ({ testId, value, placeholder, searchPlaceholder, allowCustom: Boolean(allowCustom) }))).toEqual([
    { testId: 'condition-source-step-0', value: '1', placeholder: 'Quell-Schritt auswählen', searchPlaceholder: 'Schritt nach Nummer, Titel oder Typ suchen …', allowCustom: false },
    { testId: 'condition-source-field-0', value: 'choice', placeholder: 'Feld auswählen', searchPlaceholder: 'Feld nach Name oder Typ suchen …', allowCustom: false },
    { testId: 'condition-value-0', value: 'a', placeholder: 'Wert auswählen', searchPlaceholder: 'Wert durchsuchen …', allowCustom: true },
    { testId: 'condition-target-step-0', value: '5', placeholder: 'Ziel-Schritt auswählen', searchPlaceholder: 'Ziel-Schritt suchen …', allowCustom: false },
  ]);
  expect(mockSelectProps.map(({ value }) => value)).toEqual(['equals', 'redirect']);
  expect(mockSelectItemProps.map(({ value, children }) => [value, children])).toEqual(expect.arrayContaining([
    ['equals', 'Equals'], ['hide', 'Schritt ausblenden'], ['block', 'Schritt blockieren'], ['allow_next', 'Zugriff erlauben'], ['redirect', 'Zu anderem Schritt weiterleiten'],
  ]));
  mockSearchableProps.find(p => p.testId === 'condition-source-step-0').onChange('2');
  mockSearchableProps.find(p => p.testId === 'condition-source-field-0').onChange('status');
  mockSearchableProps.find(p => p.testId === 'condition-value-0').onChange('b');
  mockSearchableProps.find(p => p.testId === 'condition-target-step-0').onChange('');
  mockSelectProps[0].onValueChange('one_of');
  mockSelectProps[1].onValueChange('block');
  fireEvent.change(screen.getByTestId('condition-message-0'), { target: { value: 'Neu' } });
  expect(cb.changeConditionSource).toHaveBeenCalledWith(0, '2');
  expect(cb.changeConditionField).toHaveBeenCalledWith(0, 'status');
  expect(cb.changeConditionOperator).toHaveBeenCalledWith(0, 'one_of');
  expect(cb.updateCondition.mock.calls).toEqual([
    [0, { value: 'b' }], [0, { target_step_order: null }], [0, { action: 'block', target_step_order: null }], [0, { message: 'Neu' }],
  ]);
  expect(mockHelpProps.map(({ children, help }) => [children, help])).toEqual(expect.arrayContaining([
    ['1. Schritt auswählen', 'Quell-Step, dessen Status oder gespeicherte Felddaten ausgewertet werden.'],
    ['Ziel-Schritt', 'Step, zu dem bei einer zutreffenden Redirect-Regel gewechselt wird.'],
    ['Hinweis für Nutzer (optional)', 'Erklärt den Grund der Regel in verständlicher Sprache, besonders bei blockierten Steps.'],
  ]));
  expect(mockSearchableProps.map(observableProps)).toMatchSnapshot();
  expect(mockSelectProps.map(observableProps)).toMatchSnapshot();
  expect(container).toMatchSnapshot();
});

test('compound condition normalizes sources, fields, operators and values exactly', () => {
  const cb = callbacks();
  cb.findStepByOrder.mockImplementation(order => order === 1 ? { title: 'Source' } : undefined);
  cb.findField.mockImplementation((_step, field) => field === 'normal' ? { field_type: 'select', options: [{ value: 'first' }] } : undefined);
  cb.conditionValueOptions.mockReturnValue([{ value: 'a', label: 'A' }]);
  const children = [
    { source_step_order: 1, field: 'choice', operator: 'one_of', value: 'a' },
    { source_step_order: null, field: '', operator: 'has_upload', value: '' },
  ];
  const { container } = render(<ConditionsPanel {...baseProps(cb)} formData={{ order: 2, conditions: [{ all_of: children, action: 'redirect', target_step_order: 5, message: '' }] }} />);
  expect(screen.getByText('Regel 1 · UND-Gruppe')).toBeInTheDocument();
  expect(screen.getByText((_, element) => element.tagName === 'P' && element.textContent === 'Alle Teilbedingungen müssen zutreffen. Bei Treffer: Zu anderem Schritt weiterleiten')).toBeInTheDocument();
  expect(screen.getByTestId('condition-compound-0-0').querySelector('summary').textContent).toBe('Teilbedingung 1 · #1 Source · choice · Ist einer von · a⌄');
  expect(screen.getByTestId('condition-compound-0-1').querySelector('summary').textContent).toBe('Teilbedingung 2 · # Unbekannt · Status · Dokument vorhanden · beliebiges Dokument⌄');
  const source = mockSearchableProps.find(p => p.testId === 'condition-child-source-0-0');
  const field = mockSearchableProps.find(p => p.testId === 'condition-child-field-0-0');
  const value = mockMultiProps.find(p => p.testId === 'condition-child-values-0-0');
  expect({ value: source.value, placeholder: source.placeholder, searchPlaceholder: source.searchPlaceholder }).toEqual({ value: '1', placeholder: 'Quell-Step auswählen', searchPlaceholder: 'Step suchen …' });
  expect({ value: field.value, placeholder: field.placeholder, searchPlaceholder: field.searchPlaceholder }).toEqual({ value: 'choice', placeholder: 'Feld auswählen', searchPlaceholder: 'Feld suchen …' });
  expect({ values: value.values, placeholder: value.placeholder, searchPlaceholder: value.searchPlaceholder, allowCustom: value.allowCustom }).toEqual({ values: ['a'], placeholder: 'Werte auswählen', searchPlaceholder: 'Werte suchen …', allowCustom: true });
  source.onChange(''); source.onChange('2');
  field.onChange('status'); field.onChange('partner_uploads'); field.onChange('normal'); field.onChange('unknown');
  const operator = mockSelectProps.find(p => p.value === 'one_of');
  operator.onValueChange('not_one_of'); operator.onValueChange('equals'); operator.onValueChange('empty');
  value.onChange(['a', 'b']);
  expect(cb.updateConditionChild.mock.calls).toEqual([
    [0, 'all_of', 0, { source_step_order: null, field: 'status', operator: 'status_is', value: 'completed' }],
    [0, 'all_of', 0, { source_step_order: 2, field: 'status', operator: 'status_is', value: 'completed' }],
    [0, 'all_of', 0, { field: 'status', operator: 'status_is', value: 'completed' }],
    [0, 'all_of', 0, { field: 'partner_uploads', operator: 'has_upload', value: '' }],
    [0, 'all_of', 0, { field: 'normal', operator: 'equals', value: 'first' }],
    [0, 'all_of', 0, { field: 'unknown', operator: 'equals', value: '' }],
    [0, 'all_of', 0, { operator: 'not_one_of', value: ['a'] }],
    [0, 'all_of', 0, { operator: 'equals', value: 'a' }],
    [0, 'all_of', 0, { operator: 'empty', value: '' }],
    [0, 'all_of', 0, { value: ['a', 'b'] }],
  ]);
  mockSelectProps.find(p => p.value === 'all_of').onValueChange('any_of');
  mockSelectProps.find(p => p.value === 'redirect').onValueChange('redirect');
  expect(cb.changeConditionGroupType).toHaveBeenCalledWith(0, 'all_of', 'any_of');
  expect(cb.updateCondition).toHaveBeenCalledWith(0, { action: 'redirect', target_step_order: 5 });
  expect(mockSearchableProps.map(observableProps)).toMatchSnapshot();
  expect(mockMultiProps.map(observableProps)).toMatchSnapshot();
  expect(mockSelectProps.map(observableProps)).toMatchSnapshot();
  expect(container).toMatchSnapshot();
});

test('compound operator conversion preserves empty and populated array boundaries', () => {
  const cb = callbacks();
  const conditions = [{ any_of: [
    { source_step_order: 1, field: 'choice', operator: 'equals', value: '' },
    { source_step_order: 1, field: 'choice', operator: 'one_of', value: [] },
    { source_step_order: 1, field: 'choice', operator: 'one_of', value: ['first', 'second'] },
  ], action: 'block', message: 'Blocked' }];
  const { container } = render(<ConditionsPanel {...baseProps(cb)} formData={{ order: 2, conditions }} />);
  const operators = mockSelectProps.filter(({ value }) => ['equals', 'one_of'].includes(value));
  operators[0].onValueChange('one_of');
  operators[1].onValueChange('equals');
  operators[2].onValueChange('equals');
  expect(cb.updateConditionChild.mock.calls).toEqual([
    [0, 'any_of', 0, { operator: 'one_of', value: [] }],
    [0, 'any_of', 1, { operator: 'equals', value: '' }],
    [0, 'any_of', 2, { operator: 'equals', value: 'first' }],
  ]);
  expect(mockSearchableProps.map(observableProps)).toMatchSnapshot();
  expect(mockMultiProps.map(observableProps)).toMatchSnapshot();
  expect(mockSelectProps.map(observableProps)).toMatchSnapshot();
  expect(container).toMatchSnapshot();
});

test('non-redirect simple input condition wires every command and hides its target', () => {
  const cb = callbacks();
  cb.conditionValueOptions.mockReturnValue([]);
  const condition = { source_step_order: null, field: '', operator: 'equals', value: '', action: 'block', message: '' };
  const { container } = render(<ConditionsPanel {...baseProps(cb)} formData={{ order: 2, conditions: [condition] }} />);
  expect(screen.queryByTestId('condition-target-step-0')).not.toBeInTheDocument();
  expect(mockSearchableProps.map(observableProps)).toMatchSnapshot();
  expect(mockSelectProps.map(observableProps)).toMatchSnapshot();
  fireEvent.click(screen.getByText('Entfernen'));
  fireEvent.change(screen.getByTestId('condition-value-input-0'), { target: { value: 'typed' } });
  fireEvent.change(screen.getByTestId('condition-message-0'), { target: { value: 'reason' } });
  mockSearchableProps.find(p => p.testId === 'condition-source-step-0').onChange('2');
  mockSearchableProps.find(p => p.testId === 'condition-source-field-0').onChange('status');
  mockSelectProps.find(p => p.value === 'equals').onValueChange('empty');
  mockSelectProps.find(p => p.value === 'block').onValueChange('redirect');
  expect(cb.removeCondition).toHaveBeenCalledWith(0);
  expect(cb.changeConditionSource).toHaveBeenCalledWith(0, '2');
  expect(cb.changeConditionField).toHaveBeenCalledWith(0, 'status');
  expect(cb.changeConditionOperator).toHaveBeenCalledWith(0, 'empty');
  expect(cb.updateCondition.mock.calls).toEqual([
    [0, { value: 'typed' }], [0, { message: 'reason' }], [0, { action: 'redirect', target_step_order: undefined }],
  ]);
  expect(container).toMatchSnapshot();
});

test('compound value editors emit exact values and enforce the last-child guard', () => {
  const cb = callbacks();
  cb.conditionValueOptions.mockImplementation(condition => condition.hasOptions ? [{ value: 'a', label: 'A' }] : []);
  const children = [
    { source_step_order: 1, field: 'choice', operator: 'not_one_of', value: 'a', hasOptions: true },
    { source_step_order: 1, field: 'choice', operator: 'equals', value: ['a'], hasOptions: true },
    { source_step_order: 1, field: 'text', operator: 'equals', value: '', hasOptions: false },
    { source_step_order: 1, field: 'text', operator: 'not_empty', value: 'ignored', hasOptions: false },
  ];
  const { unmount } = render(<ConditionsPanel {...baseProps(cb)} formData={{ order: 2, conditions: [{ any_of: children, action: 'block', message: '' }] }} />);
  mockMultiProps.find(p => p.testId === 'condition-child-values-0-0').onChange(['b']);
  mockSearchableProps.find(p => p.testId === 'condition-child-value-0-1').onChange('b');
  fireEvent.change(screen.getByTestId('condition-child-value-input-0-2'), { target: { value: 'typed' } });
  fireEvent.change(screen.getByTestId('condition-message-0'), { target: { value: 'blocked' } });
  fireEvent.click(screen.getByTestId('condition-remove-child-0-2'));
  fireEvent.click(screen.getAllByText('Entfernen')[0]);
  expect(screen.getByText('Kein Wert erforderlich')).toBeInTheDocument();
  expect(screen.getByTestId('condition-remove-child-0-0')).not.toBeDisabled();
  expect(cb.updateConditionChild.mock.calls).toEqual([
    [0, 'any_of', 0, { value: ['b'] }],
    [0, 'any_of', 1, { value: 'b' }],
    [0, 'any_of', 2, { value: 'typed' }],
  ]);
  expect(cb.updateCondition).toHaveBeenCalledWith(0, { message: 'blocked' });
  expect(cb.removeConditionChild).toHaveBeenCalledWith(0, 'any_of', 2);
  expect(cb.removeCondition).toHaveBeenCalledWith(0);

  unmount();
  const single = callbacks();
  render(<ConditionsPanel {...baseProps(single)} formData={{ order: 2, conditions: [{ all_of: [children[2]], action: 'block' }] }} />);
  expect(screen.getByTestId('condition-remove-child-0-0')).toBeDisabled();
});

test('simple no-value, multi-value and null redirect modes retain their exact contracts', () => {
  const cb = callbacks();
  cb.conditionValueOptions.mockReturnValue([{ value: 'a', label: 'A' }]);
  const conditions = [
    { source_step_order: 1, field: 'text', operator: 'not_empty', value: 'ignored', action: 'block' },
    { source_step_order: 1, field: 'choice', operator: 'not_one_of', value: 'a', action: 'block' },
    { source_step_order: 1, field: 'choice', operator: 'equals', value: 'a', action: 'redirect', target_step_order: null },
  ];
  render(<ConditionsPanel {...baseProps(cb)} formData={{ order: 2, conditions }} />);
  expect(screen.getByTestId('condition-card-0')).toHaveTextContent('Kein Wert erforderlich');
  expect(screen.queryByTestId('condition-values-0')).not.toBeInTheDocument();
  const multi = mockMultiProps.find(p => p.testId === 'condition-values-1');
  expect(observableProps(multi)).toEqual({ options: [{ value: 'a', label: 'A' }], values: ['a'], placeholder: 'Mehrere Werte auswählen', searchPlaceholder: 'Werte durchsuchen oder eingeben …', testId: 'condition-values-1', allowCustom: true });
  multi.onChange(['b']);
  const target = mockSearchableProps.find(p => p.testId === 'condition-target-step-2');
  expect(target.value).toBe('');
  expect(cb.updateCondition).toHaveBeenCalledWith(1, { value: ['b'] });
});
