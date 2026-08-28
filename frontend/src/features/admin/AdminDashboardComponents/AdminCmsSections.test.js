import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { CmsSection, LandingPagesSection } from './AdminCmsSections';

jest.mock('../../../components/ui/select', () => ({ Select: ({ children, onValueChange }) => <div>{children}<button type="button" data-testid="cms-select-none" onClick={() => onValueChange('__none')}>none</button><button type="button" data-testid="cms-select-page" onClick={() => onValueChange('page2')}>page</button></div>, SelectContent: ({ children }) => <>{children}</>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children }) => <div>{children}</div>, SelectValue: () => null }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));

test('generic CMS section edits German and English text/input fields and saves', () => {
  const onChange = jest.fn(), onTransChange = jest.fn(updater => updater({ en: {} })), onSave = jest.fn();
  render(<CmsSection title="Demo Section" fields={[{ key: 'title', label: 'Title', type: 'text', placeholder: 'T' }, { key: 'body', label: 'Body', type: 'textarea', placeholder: 'B' }]} content={{ title: 'Deutsch', body: '' }} onChange={onChange} translations={{ en: { title: 'English' } }} onTransChange={onTransChange} onSave={onSave} saving={false} />);
  fireEvent.change(screen.getByTestId('cms-field-title'), { target: { value: 'Neu' } }); fireEvent.change(screen.getByTestId('cms-field-body'), { target: { value: 'Text' } }); fireEvent.click(screen.getByText('EN'));
  fireEvent.change(screen.getByTestId('cms-field-en-title'), { target: { value: 'New' } }); fireEvent.change(screen.getByTestId('cms-field-en-body'), { target: { value: 'Body' } }); fireEvent.click(screen.getByTestId('cms-save-demo-section')); fireEvent.click(screen.getByText('DE'));
  expect(onChange).toHaveBeenCalledTimes(2); expect(onTransChange).toHaveBeenCalledTimes(2); expect(onSave).toHaveBeenCalled();
});

test('landing pages edit languages, survey, add/remove/save and empty state', () => {
  jest.spyOn(Date, 'now').mockReturnValue(123);
  const onChange = jest.fn(), onTransChange = jest.fn(updater => updater({ en: {} })), onSave = jest.fn();
  const pages = [{ id: 'root', title: 'Home', path: '/', survey_slug: '' }, { id: 'page2', title: 'Page', path: '/page', hero_subtitle: 'DE' }];
  const props = { content: { extra: true, pages }, onChange, translations: { en: { page2: { title: 'English' } } }, onTransChange, surveys: [{ id: 's', name: 'Survey', slug: 'survey' }], onSave, saving: false };
  const { rerender } = render(<LandingPagesSection {...props} />);
  fireEvent.click(screen.getAllByTestId('cms-select-page')[0]); fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Changed' } }); fireEvent.change(screen.getAllByRole('textbox').find(node => node.tagName === 'TEXTAREA'), { target: { value: 'Long text' } }); fireEvent.click(screen.getAllByTestId('cms-select-none')[1]); fireEvent.click(screen.getAllByTestId('cms-select-page')[1]);
  fireEvent.click(screen.getByText('EN')); fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Translated' } }); fireEvent.click(screen.getByText('DE'));
  fireEvent.click(screen.getAllByTestId('cms-select-page')[0]); fireEvent.click(screen.getByText('Entfernen')); fireEvent.click(screen.getByText('Neu')); fireEvent.click(screen.getByTestId('cms-save-landingpages'));
  expect(onChange).toHaveBeenCalled(); expect(onTransChange).toHaveBeenCalled(); expect(onSave).toHaveBeenCalled();
  rerender(<LandingPagesSection {...props} content={{ pages: [] }} saving />); expect(screen.getByText('Noch keine Landingpages angelegt.')).toBeInTheDocument(); expect(screen.getByText('Saving...')).toBeDisabled();
  Date.now.mockRestore();
});

test('CMS sections cover absent content, translations, survey and empty-removal fallbacks', () => {
  const onChange = jest.fn(), onTransChange = jest.fn(updater => updater(undefined));
  const { rerender } = render(<LandingPagesSection content={undefined} onChange={onChange} translations={undefined} onTransChange={onTransChange} surveys={[]} onSave={jest.fn()} />); fireEvent.click(screen.getByText('Neu')); expect(onChange).toHaveBeenCalled();
  rerender(<LandingPagesSection content={{ pages: [{ id: 'only', path: '/only', title: '', hero_subtitle: '' }] }} onChange={onChange} translations={undefined} onTransChange={onTransChange} surveys={[]} onSave={jest.fn()} />); expect(screen.getByText((_, node) => node.tagName === 'SPAN' && node.textContent.includes('/only'))).toBeInTheDocument(); fireEvent.click(screen.getByText('EN')); fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'English' } }); fireEvent.change(screen.getAllByRole('textbox').find(n => n.tagName === 'TEXTAREA'), { target: { value: 'Text' } }); fireEvent.click(screen.getByText('Entfernen'));
  rerender(<CmsSection title="Sparse" fields={[{ key: 'title', label: 'Title', type: 'text', placeholder: 'Placeholder' }, { key: 'body', label: 'Body', type: 'textarea', placeholder: 'Body fallback' }]} content={{}} onChange={jest.fn()} translations={undefined} onTransChange={onTransChange} onSave={jest.fn()} saving />); fireEvent.click(screen.getByText('EN')); expect(screen.getByText('Saving...')).toBeDisabled(); fireEvent.change(screen.getByTestId('cms-field-en-title'), { target: { value: 'x' } }); fireEvent.change(screen.getByTestId('cms-field-en-body'), { target: { value: 'y' } });
});
