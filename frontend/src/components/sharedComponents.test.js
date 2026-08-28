import React from 'react';
import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { LanguageProvider, useLanguage } from '../contexts/LanguageContext';
import { JourneyProgressIndicator, computeDecisionBranches, nextVisibleSteps, resolveStepType } from './JourneyProgressIndicator';

jest.mock('./ui/select', () => ({
  Select: ({ children, onValueChange }) => <div>{children}<button onClick={() => onValueChange('all')}>all</button></div>,
  SelectContent: ({ children }) => <div>{children}</div>,
  SelectItem: ({ children }) => <span>{children}</span>,
  SelectTrigger: ({ children, ...props }) => <button {...props}>{children}</button>,
  SelectValue: () => <span>value</span>,
}));
jest.mock('./ui/button', () => ({ Button: ({ children, ...props }) => <button {...props}>{children}</button> }));
jest.mock('./ui/dialog', () => ({ Dialog: ({ open, children }) => open ? <div>{children}</div> : null, DialogContent: ({ children }) => <section>{children}</section>, DialogHeader: ({ children }) => <header>{children}</header>, DialogTitle: ({ children }) => <h2>{children}</h2> }));

const { PaginationControls, usePagination } = require('./PaginationControls');
const { DataTable, EmptyState, PaginatedCollection, SearchToolbar, SegmentedControl, TableActions, TableCell, TableEmptyState, TableHeader, TableHeading, TableRow } = require('./collections');
const { PageCard, SectionCard } = require('./layout');
const { StatusBadge, TagBadge } = require('./ui/entity-badges');
const { ConfirmDialog } = require('./ConfirmDialog');

test('collection controls expose reusable switches and empty states', () => {
  const onChange = jest.fn();
  const Icon = (props) => <span data-testid="empty-icon" {...props} />;
  const { rerender } = render(<SegmentedControl value="list" onChange={onChange} testId="views" options={[
    { value: 'list', label: 'Liste', testId: 'list-view' },
    { value: 'grid', label: 'Kacheln', testId: 'grid-view' },
    { value: 'hidden', label: 'Versteckt', hidden: true },
  ]} />);
  expect(screen.queryByText('Versteckt')).not.toBeInTheDocument();
  fireEvent.click(screen.getByTestId('grid-view'));
  expect(onChange).toHaveBeenCalledWith('grid');
  rerender(<SegmentedControl joined value="grid" onChange={onChange} options={[{ value: 'list', label: 'Liste' }, { value: 'grid', label: 'Kacheln' }]} />);
  fireEvent.click(screen.getByText('Liste'));
  expect(onChange).toHaveBeenCalledWith('list');
  rerender(<EmptyState title="Leer" description="Keine Einträge" icon={Icon} action={<button>Erstellen</button>} testId="empty" />);
  expect(screen.getByTestId('empty-icon')).toBeInTheDocument();
  expect(screen.getByText('Erstellen')).toBeInTheDocument();
  rerender(<table><tbody><TableEmptyState colSpan={3} title="Keine Zeilen" description="Noch nichts vorhanden" testId="empty-row" /></tbody></table>);
  expect(screen.getByTestId('empty-row').querySelector('td')).toHaveAttribute('colspan', '3');
});

test('layout, search, table, badge, and paginated collection primitives compose', () => {
  const change = jest.fn();
  const pagination = { page: 1, pageSize: '10', setPage: jest.fn(), setPageSize: jest.fn(), totalCount: 2, totalPages: 1, startIndex: 0, endIndex: 2, isAll: false, paginatedItems: [{ id: 1, name: 'A' }, { id: 2, name: 'B' }] };
  render(<>
    <PageCard title="Seite" description="Beschreibung" toolbar={<button>Werkzeug</button>} footer={<span>Fuß</span>}><span>Inhalt</span></PageCard>
    <SectionCard><span>Nur Inhalt</span></SectionCard>
    <SearchToolbar value="abc" onChange={change} filters={<span>Filter</span>} actions={<button>Aktion</button>} summary="2 Treffer" inputTestId="search" />
    <DataTable testId="table"><TableHeader><tr><TableHeading>Name</TableHeading></tr></TableHeader><tbody><TableRow><TableCell><TableActions><button>Öffnen</button></TableActions></TableCell></TableRow></tbody></DataTable>
    <StatusBadge tone="success">Aktiv</StatusBadge><StatusBadge tone="unknown">Neutral</StatusBadge><TagBadge>Tag</TagBadge>
    <PaginatedCollection pagination={pagination} id="cards" className="cards">{item => <span>{item.name}</span>}</PaginatedCollection>
  </>);
  fireEvent.change(screen.getByTestId('search'), { target: { value: 'neu' } });
  expect(change).toHaveBeenCalledWith('neu');
  expect(screen.getByText('Seite')).toBeInTheDocument();
  expect(screen.getByTestId('table')).toBeInTheDocument();
  expect(screen.getByText('A')).toBeInTheDocument();
  expect(screen.getByText('B')).toBeInTheDocument();
  expect(screen.getByTestId('pagination-cards')).toBeInTheDocument();
});

test('paginated collection renders its empty state', () => {
  render(<PaginatedCollection pagination={{ totalCount: 0, paginatedItems: [] }} id="empty-cards" emptyTitle="Keine Karten" emptyDescription="Später erneut prüfen">{() => null}</PaginatedCollection>);
  expect(screen.getByText('Keine Karten')).toBeInTheDocument();
});

test('confirm dialog exposes cancel and destructive confirmation commands', () => {
  const close = jest.fn(); const confirm = jest.fn();
  const { rerender } = render(<ConfirmDialog open title="Löschen?" message="Wirklich löschen" confirmLabel="Ja" cancelLabel="Nein" destructive onOpenChange={close} onConfirm={confirm} />);
  fireEvent.click(screen.getByText('Nein'));
  fireEvent.click(screen.getByText('Ja'));
  expect(close).toHaveBeenCalledWith(false);
  expect(confirm).toHaveBeenCalled();
  rerender(<ConfirmDialog open={false} onOpenChange={close} onConfirm={confirm} />);
  expect(screen.queryByText('Bestätigung')).not.toBeInTheDocument();
});

function LanguageConsumer() {
  const value = useLanguage();
  return <div>
    <span data-testid="lang">{value.lang}</span>
    <span data-testid="known">{value.t('nav_home')}</span>
    <span data-testid="fallback">{value.t('missing')}</span>
    <span data-testid="localized">{value.localize({ title: 'Deutsch', translations: { en: { title: 'English' } } }, 'title')}</span>
    <span data-testid="cms">{value.localizeCms({ title: 'Deutsch' }, 'title', { en: { title: 'English' } })}</span>
    <span data-testid="missing-fields">{value.localize({}, 'title')}|{value.localizeCms({}, 'title')}</span>
    <span data-testid="empty">{value.localize(null, 'title')}|{value.localizeCms(null, 'title')}</span>
    <button onClick={value.toggleLang}>toggle language</button>
    <button onClick={() => value.setLang('fr')}>French</button>
  </div>;
}

test('language context translates, localizes, falls back and persists', () => {
  localStorage.removeItem('gj_lang');
  render(<LanguageProvider><LanguageConsumer /></LanguageProvider>);
  expect(screen.getByTestId('lang')).toHaveTextContent('en');
  expect(screen.getByTestId('known')).toHaveTextContent('Home');
  expect(screen.getByTestId('localized')).toHaveTextContent('English');
  expect(screen.getByTestId('cms')).toHaveTextContent('English');
  expect(screen.getByTestId('fallback')).toHaveTextContent('missing');
  fireEvent.click(screen.getByText('toggle language'));
  expect(screen.getByTestId('lang')).toHaveTextContent('de');
  expect(screen.getByTestId('localized')).toHaveTextContent('Deutsch');
  fireEvent.click(screen.getByText('toggle language'));
  fireEvent.click(screen.getByText('French'));
  expect(screen.getByTestId('known')).toHaveTextContent('Home');
  expect(localStorage.getItem('gj_lang')).toBe('fr');
});

test('language context initializes stored language and enforces provider', () => {
  localStorage.setItem('gj_lang', 'de');
  render(<LanguageProvider><LanguageConsumer /></LanguageProvider>);
  expect(screen.getByTestId('lang')).toHaveTextContent('de');
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
  expect(() => renderHook(() => useLanguage())).toThrow('useLanguage must be used within LanguageProvider');
  spy.mockRestore();
});

test('pagination handles storage, bounds, reset, all, and invalid sizes', () => {
  localStorage.setItem('gerdoctor_pagination_users', '25');
  const items = Array.from({ length: 60 }, (_, id) => id);
  const { result, rerender } = renderHook(({ rows, reset }) => usePagination(rows, 'users', { defaultPageSize: 10, resetKey: reset }), { initialProps: { rows: items, reset: 'a' } });
  expect(result.current.pageSize).toBe('25');
  act(() => result.current.setPage(3));
  expect(result.current.paginatedItems).toHaveLength(10);
  rerender({ rows: items.slice(0, 2), reset: 'a' });
  expect(result.current.page).toBe(1);
  act(() => result.current.setPageSize('invalid'));
  expect(result.current.pageSize).toBe('25');
  act(() => result.current.setPageSize('all'));
  expect(result.current.isAll).toBe(true);
  rerender({ rows: items, reset: 'b' });
  expect(result.current.page).toBe(1);
});

test('pagination survives disabled storage and renders controls', () => {
  const get = jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('off'); });
  const { result } = renderHook(() => usePagination([1, 2, 3], 'off'));
  get.mockRestore();
  const set = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('off'); });
  act(() => result.current.setPageSize('all'));
  set.mockRestore();
  const setPage = jest.fn(); const setPageSize = jest.fn();
  const { rerender } = render(<PaginationControls id="x" pagination={{ page: 1, pageSize: '10', setPage, setPageSize, totalCount: 0, totalPages: 2, startIndex: 0, endIndex: 0, isAll: false }} />);
  fireEvent.click(screen.getByLabelText('Nächste Seite'));
  fireEvent.click(screen.getByText('all'));
  expect(setPage).toHaveBeenCalledWith(2);
  rerender(<PaginationControls id="x" pagination={{ page: 2, pageSize: '10', setPage, setPageSize, totalCount: 20, totalPages: 2, startIndex: 10, endIndex: 20, isAll: false }} />);
  fireEvent.click(screen.getByLabelText('Vorherige Seite'));
  expect(setPage).toHaveBeenCalledWith(1);
  expect(setPageSize).toHaveBeenCalledWith('all');
  rerender(<PaginationControls id="x" className="extra" pagination={{ page: 1, pageSize: 'all', setPage, setPageSize, totalCount: 3, totalPages: 1, startIndex: 0, endIndex: 3, isAll: true }} />);
  expect(screen.queryByLabelText('Nächste Seite')).not.toBeInTheDocument();
});

test('pagination falls back for an unsupported stored size and default options', () => {
  localStorage.setItem('gerdoctor_pagination_default', 'unsupported');
  const { result } = renderHook(() => usePagination([], 'default'));
  expect(result.current.pageSize).toBe('10');
});

const base = (id, order, type = 'form', extra = {}) => ({ id, order, title: id, step_type: type, ...extra });

test('journey helpers cover defaults and bounded previews', () => {
  expect(resolveStepType(null)).toBe('form');
  expect(resolveStepType({ step_type: 'form' })).toBe('form');
  expect(resolveStepType({ step_type: 'form', fields: [{ field_type: 'file' }] })).toBe('upload');
  expect(resolveStepType({ step_type: 'form', fields: [{ field_type: 'upload' }] })).toBe('upload');
  expect(resolveStepType({ step_type: 'form', fields: [{ field_type: 'text' }] })).toBe('form');
  expect(resolveStepType({ step_type: 'decision', fields: [{ field_type: 'file' }] })).toBe('decision');
  expect(resolveStepType({})).toBe('form');
  expect(nextVisibleSteps(undefined, 0)).toEqual([]);
  expect(nextVisibleSteps([1, 2, 3], 0, 1)).toEqual([2]);
  expect(computeDecisionBranches({ order: 1 }, undefined)).toEqual([]);
  expect(computeDecisionBranches({ order: 1, fields: [{}] }, [])).toEqual([]);
  const option = { order: 1, fields: [{ options: [{ value: 'x' }] }] };
  expect(computeDecisionBranches(option, undefined)[0].steps).toEqual([]);
  expect(computeDecisionBranches(option, [{ order: 1 }, { order: 8 }])[0].steps).toEqual([]);
  expect(computeDecisionBranches(option, [{ order: 1 }, { order: 2 }])[0].steps).toHaveLength(1);
  const selectedField = { order: 1, fields: [{ field_type: 'text', options: [{ value: 'wrong' }] }, { field_type: 'decision', options: [{ value: 'right', label: 'Richtig' }] }] };
  const branch = computeDecisionBranches(selectedField, [{ order: 5, title: 'boundary' }, { order: 3, title: 'second' }, { order: 2, title: 'first' }, { order: 4, title: 'third' }, { order: 6, title: 'too far' }])[0];
  expect(branch.label).toBe('Richtig');
  expect(branch.steps.map(({ title }) => title)).toStrictEqual(['first', 'second']);
  const boundary = base('boundary-only', 5);
  expect(computeDecisionBranches(selectedField, [boundary])[0].steps).toStrictEqual([boundary]);
  expect(computeDecisionBranches({ order: 1, fields: [{ field_type: 'decision', options: [{ value: 'fallback' }] }] }, [base('visible', 2)])[0].label).toBe('fallback');
  const showCondition = base('shown', 2, 'form', { conditions: [{ action: 'show', source_step_order: 1, field: 'decision', operator: 'equals', value: 'right' }] });
  expect(computeDecisionBranches(selectedField, [showCondition])[0].steps).toStrictEqual([showCondition]);
  const falseHide = base('not-hidden', 2, 'form', { conditions: [{ action: 'hide', source_step_order: 1, field: 'decision', operator: 'equals', value: 'other' }] });
  expect(computeDecisionBranches(selectedField, [falseHide])[0].steps).toStrictEqual([falseHide]);
});

test('journey indicator renders empty, linear, upload, fallback and milestone states', () => {
  const { rerender, container } = render(<JourneyProgressIndicator visibleSteps={[]} currentIndex={0} allSteps={[]} />);
  expect(container).toBeEmptyDOMElement();
  const steps = [base('first', 1, 'form', { fields: [{ field_type: 'upload' }] }), base('unknown', 2, 'custom'), base('milestone', 3, 'milestone')];
  rerender(<JourneyProgressIndicator visibleSteps={steps} currentIndex={0} allSteps={steps} />);
  expect(screen.getByTestId('journey-upcoming')).toHaveTextContent('unknown');
  rerender(<JourneyProgressIndicator visibleSteps={steps} currentIndex={2} allSteps={steps} />);
  expect(screen.getByTestId('journey-milestone-hint')).toBeInTheDocument();
  const fallbackSteps = [{ step_id: 'fallback', order: 1, title: 'fallback', step_type: 'custom' }, { step_id: 'next', order: 2, title: 'next', step_type: 'custom' }];
  rerender(<JourneyProgressIndicator visibleSteps={fallbackSteps} currentIndex={0} allSteps={fallbackSteps} />);
  expect(screen.getByTestId('journey-current-title')).toHaveTextContent('fallback');
  rerender(<JourneyProgressIndicator visibleSteps={undefined} currentIndex={undefined} allSteps={[]} />);
});

test('journey decision preview evaluates every condition operator and branch shape', () => {
  const decision = base('decision', 1, 'decision', { fields: [{ field_type: 'decision', options: [{ value: 'yes', label: 'Ja' }, { value: 'no' }] }] });
  const conditions = [
    { operator: 'equals', value: 'yes' }, { operator: 'not_equals', value: 'yes' },
    { operator: 'one_of', value: ['yes'] }, { operator: 'not_one_of', value: ['yes'] },
    { operator: 'empty', value: '' }, { operator: 'not_empty', value: '' }, { operator: 'other', value: '' },
  ];
  const future = conditions.map((condition, index) => base(`step-${index}`, index + 2, 'form', { conditions: [{ action: 'hide', source_step_order: 1, field: 'decision', ...condition }] }));
  future.push(base('ignored-action', 3, 'form', { conditions: [{ action: 'show' }] }));
  future.push(base('missing-source', 4, 'form', { conditions: [{ action: 'hide', source_step_order: 99 }] }));
  future.push(base('too-far', 20));
  render(<JourneyProgressIndicator visibleSteps={[decision]} currentIndex={0} allSteps={[decision, ...future]} />);
  expect(screen.getByTestId('journey-decision-branches')).toBeInTheDocument();
  expect(screen.getByTestId('journey-branch-yes')).toBeInTheDocument();
  expect(screen.getByTestId('journey-branch-no')).toBeInTheDocument();
});

test('journey decision supports array values, empty branches and missing options', () => {
  const empty = base('d', 1, 'decision', { fields: [] });
  const { rerender } = render(<JourneyProgressIndicator visibleSteps={[empty]} currentIndex={0} allSteps={[empty]} />);
  expect(screen.queryByTestId('journey-decision-branches')).not.toBeInTheDocument();
  const decision = base('d', 1, 'decision', { fields: [{ options: [{ value: ['a'] }, { value: [] }] }] });
  const hidden = base('h', 2, 'form', { conditions: [{ action: 'hide', source_step_order: 1, field: 'decision', operator: 'one_of', value: ['a'] }] });
  const hidden2 = base('h2', 3, 'form', { conditions: [{ action: 'hide', source_step_order: 1, field: 'decision', operator: 'not_one_of', value: ['a'] }] });
  rerender(<JourneyProgressIndicator visibleSteps={[decision]} currentIndex={0} allSteps={[decision, hidden, hidden2]} />);
  expect(screen.getByTestId('journey-decision-branches')).toBeInTheDocument();
  const single = base('single', 1, 'decision', { fields: [{ options: [{ value: 'yes' }] }] });
  const alwaysHidden = { step_id: 'hidden', order: 2, title: 'hidden', step_type: 'custom', conditions: [{ action: 'hide', source_step_order: 1, field: 'decision', operator: 'equals', value: 'yes' }] };
  rerender(<JourneyProgressIndicator visibleSteps={[single]} currentIndex={0} allSteps={[single, alwaysHidden]} />);
  expect(screen.getByText('→ direkt zum Meilenstein')).toBeInTheDocument();
  const custom = { step_id: 'custom-step', order: 2, title: 'custom branch', step_type: 'custom' };
  rerender(<JourneyProgressIndicator visibleSteps={[single]} currentIndex={0} allSteps={[single, custom]} />);
  expect(screen.getByText('custom branch')).toBeInTheDocument();
});
