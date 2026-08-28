import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { SearchableMultiSelect, SearchableSelect } from './EntityPickers';

jest.mock('@phosphor-icons/react', () => ({
  CaretDown: () => <i />, Check: () => <i />, MagnifyingGlass: () => <i />, X: () => <i />,
}));

const options = [
  'Plain',
  { value: 2, label: 'Zwei', description: 'Beschreibung', keywords: 'zweites', disabled: true },
  { value: 'three', label: '', description: '', keywords: '' },
];

test('single picker selects, filters, accepts custom values and closes from every supported input', () => {
  const onChange = jest.fn();
  const { rerender } = render(<SearchableSelect options={options} value="Plain" onChange={onChange} testId="single" allowCustom />);
  expect(screen.getByText('Plain')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('single'));
  expect(screen.getByRole('listbox')).not.toHaveAttribute('aria-multiselectable');
  fireEvent.change(screen.getByTestId('single-search'), { target: { value: 'beschreib' } });
  expect(screen.getByText('Zwei')).toBeInTheDocument();
  fireEvent.change(screen.getByTestId('single-search'), { target: { value: 'Eigener Wert' } });
  fireEvent.click(screen.getByTestId('single-custom-option'));
  expect(onChange).toHaveBeenCalledWith('Eigener Wert');

  rerender(<SearchableSelect options={options} value="missing" onChange={onChange} testId="single" />);
  expect(screen.getByText('missing')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('single'));
  fireEvent.change(screen.getByTestId('single-search'), { target: { value: 'nothing' } });
  expect(screen.getByText('Keine passenden Einträge')).toBeInTheDocument();
  fireEvent.keyDown(document, { key: 'x' });
  expect(screen.getByTestId('single-menu')).toBeInTheDocument();
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(screen.queryByTestId('single-menu')).not.toBeInTheDocument();

  fireEvent.click(screen.getByTestId('single'));
  fireEvent.mouseDown(document.body);
  expect(screen.queryByTestId('single-menu')).not.toBeInTheDocument();
  fireEvent.click(screen.getByTestId('single'));
  fireEvent.mouseDown(screen.getByTestId('single-search'));
  expect(screen.getByTestId('single-menu')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('single'));
});

test('single picker renders defaults, selected numeric labels, disabled state and ordinary option choice', () => {
  const onChange = jest.fn();
  const { rerender } = render(<SearchableSelect onChange={onChange} disabled />);
  expect(screen.getByRole('combobox')).toBeDisabled();
  expect(screen.getByText('Auswählen')).toBeInTheDocument();
  rerender(<SearchableSelect onChange={onChange} />);
  fireEvent.click(screen.getByRole('combobox'));
  expect(screen.getByText('Keine passenden Einträge')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('combobox'));
  rerender(<SearchableSelect options={options} value={2} onChange={onChange} testId="pick" />);
  expect(screen.getByText('Zwei')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('pick'));
  fireEvent.click(screen.getAllByTestId('pick-option')[0]);
  expect(onChange).toHaveBeenCalledWith('Plain');
});

test('multi picker toggles known and custom values, removes chips and closes explicitly', () => {
  const onChange = jest.fn();
  const { rerender } = render(<SearchableMultiSelect options={options} values={['Plain', null, '', 'unknown']} onChange={onChange} testId="multi" allowCustom />);
  expect(screen.getByText('unknown')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('multi'));
  expect(screen.getByRole('listbox')).toHaveAttribute('aria-multiselectable', 'true');
  fireEvent.click(screen.getAllByTestId('multi-option')[0]);
  expect(onChange).toHaveBeenLastCalledWith(['unknown']);
  fireEvent.click(screen.getAllByTestId('multi-option')[0]);
  expect(onChange).toHaveBeenLastCalledWith(['unknown', 'Plain']);
  fireEvent.change(screen.getByTestId('multi-search'), { target: { value: 'Custom' } });
  fireEvent.click(screen.getByTestId('multi-custom-option'));
  expect(onChange).toHaveBeenLastCalledWith(['unknown', 'Plain', 'Custom']);
  fireEvent.click(screen.getByTestId('multi-done'));
  expect(screen.queryByTestId('multi-menu')).not.toBeInTheDocument();

  rerender(<SearchableMultiSelect options={options} values={['Plain']} onChange={onChange} testId="multi" />);
  fireEvent.click(screen.getByLabelText('Plain entfernen'));
  expect(onChange).toHaveBeenLastCalledWith([]);
  rerender(<SearchableMultiSelect options={options} values={['Plain']} onChange={onChange} testId="multi" />);
  fireEvent.keyDown(screen.getByLabelText('Plain entfernen'), { key: 'x' });
  fireEvent.keyDown(screen.getByLabelText('Plain entfernen'), { key: 'Enter' });
  fireEvent.keyDown(screen.getByLabelText('Plain entfernen'), { key: ' ' });
  expect(onChange).toHaveBeenCalledWith([]);
});

test('multi picker renders its empty defaults and closes on escape and outside clicks', () => {
  render(<SearchableMultiSelect onChange={jest.fn()} />);
  expect(screen.getByText('Mehrere Einträge auswählen')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('searchable-multi-select'));
  expect(screen.getByText('Keine passenden Einträge')).toBeInTheDocument();
  fireEvent.keyDown(document, { key: 'Escape' });
  fireEvent.click(screen.getByTestId('searchable-multi-select'));
  fireEvent.mouseDown(document.body);
  expect(screen.queryByTestId('searchable-multi-select-menu')).not.toBeInTheDocument();
});
