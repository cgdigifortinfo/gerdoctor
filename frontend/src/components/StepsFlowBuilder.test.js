import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import StepsFlowBuilder, {
  buildGraph, changeConditionField, changeConditionOperator, conditionLeaves, conditionModalOptions, conditionValueLabel, ConditionModal, createConditionForm, dagreLayout, durationToDays,
  activePlaybackId, applyFlowSnapshot, connectionModalState, decorateFlowNodes, dependencyGraphStats, edgeModalState, flowKeyboardAction, flowPositionSnapshot, flowStepId, flowViewportCommand, formatDays, isDependencyLayout, linearLayout, minimapNodeColor, nodeLayoutPatch, Palette, playbackFrame, playbackHiddenSteps, simulatorStateMap, StepNode, validLayoutEdges, visiblePlaybackStepIds,
} from './StepsFlowBuilder';

const mockFlowProps = jest.fn();
const mockProject = jest.fn((point) => point);
const mockSetViewport = jest.fn();
const mockFitView = jest.fn();
const mockSetNodes = jest.fn();
const mockSetEdges = jest.fn();
jest.mock('reactflow', () => ({
  __esModule: true,
  default: (props) => { mockFlowProps(props); return <div data-testid="react-flow">{props.children}</div>; },
  Background: () => <i />, Controls: (props) => <i data-testid="controls" data-props={JSON.stringify(props)} />, MiniMap: ({ nodeColor, ...props }) => <button data-testid="minimap" data-props={JSON.stringify(props)} data-form-color={nodeColor({ data: { step_type: 'form' } })} data-fallback-color={nodeColor({})} />,
  Handle: (props) => <i data-testid={`handle-${props.id}`} data-type={props.type} data-position={props.position} style={props.style} />, Position: { Left: 'left', Right: 'right' }, MarkerType: { ArrowClosed: 'arrow' },
  ReactFlowProvider: ({ children }) => <>{children}</>, useReactFlow: () => ({ project: mockProject, setViewport: mockSetViewport, fitView: mockFitView }),
  useNodesState: (initial) => [initial, mockSetNodes, jest.fn()],
  useEdgesState: (initial) => [initial, mockSetEdges, jest.fn()], addEdge: jest.fn(),
}), { virtual: true });
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('./ui/button', () => ({ Button: ({ children, ...props }) => <button {...props}>{children}</button> }));
jest.mock('./FlowSimulatorPanel', () => ({
  __esModule: true,
  default: ({ value, onChange }) => <button data-testid="simulator" onClick={() => onChange(value === 'none' ? 'profile' : 'none')}>simulator</button>,
}));
jest.mock('../features/steps', () => ({
  SIMULATOR_PROFILES: { profile: { profile: { answer: 'x' } }, empty: {} },
  simulateJourney: jest.fn((steps) => ({ hidden: new Set([steps[0]?.id]), blocked: new Set([steps[1]?.id]), autoComplete: new Set([steps[2]?.id]) })),
}));
const mockHistory = { clear: jest.fn(), push: jest.fn(), undo: jest.fn(), redo: jest.fn(), canUndo: true, canRedo: true };
jest.mock('../hooks/useFlowHistory', () => ({ useFlowHistory: () => mockHistory }));
jest.mock('./admin/EntityPickers', () => ({
  SearchableSelect: ({ testId, onChange, value, options, placeholder, searchPlaceholder }) => <button data-testid={testId} data-options={JSON.stringify(options)} data-placeholder={placeholder} data-search-placeholder={searchPlaceholder} onClick={() => onChange(value === 'status' ? 'choice' : 'status')}>select:{value}</button>,
  SearchableMultiSelect: ({ testId, onChange, values, options, placeholder, searchPlaceholder }) => <button data-testid={testId} data-values={JSON.stringify(values)} data-options={JSON.stringify(options)} data-placeholder={placeholder} data-search-placeholder={searchPlaceholder} onClick={() => onChange(['a', 'b'])}>multi</button>,
}));

const step = (id, order, extra = {}) => ({ id, order, title: id, step_type: 'form', fields: [], conditions: [], ...extra });

beforeEach(() => {
  mockProject.mockImplementation((point) => point);
  require('../features/steps').simulateJourney.mockImplementation((steps) => ({
    hidden: new Set([steps[0]?.id]), blocked: new Set([steps[1]?.id]), autoComplete: new Set([steps[2]?.id]),
  }));
  global.requestAnimationFrame = (callback) => { callback(); return 1; };
  global.cancelAnimationFrame = jest.fn();
});

test('duration and condition helpers cover all units, ranges, operators and nested groups', () => {
  expect(['hours', 'days', 'weeks', 'months', 'years', 'other'].map(unit => durationToDays(2, unit))).toEqual([2 / 24, 2, 14, 60, 730, 2]);
  expect(durationToDays('', 'days')).toBe(0);
  expect([-1, 0, 1, 13, 14, 59, 60].map(formatDays)).toEqual(['0d', '0d', '1d', '13d', '2w', '8w', '2M']);
  const nested = conditionLeaves({ action: 'hide', all_of: [{ field: 'a', any_of: [{ value: 1 }, { value: 2 }] }, { field: 'b' }] });
  expect(nested).toHaveLength(3);
  expect(nested[0]).toEqual(expect.objectContaining({ group: 'UND / ODER', condition: expect.objectContaining({ action: 'hide' }) }));
  expect(conditionLeaves({ field: 'x' }, 'block', 'Group')[0].condition.action).toBe('block');
  const operators = ['equals', 'not_equals', 'contains', 'not_contains', 'in', 'not_in', 'completed', 'not_completed', 'custom', undefined];
  expect(operators.map(operator => conditionValueLabel({ operator, value: 'x' }))).toEqual([
    ' = x', ' ≠ x', ' enthält x', ' enthält nicht x', ' ist in x', ' ist nicht in x', ' abgeschlossen x', ' nicht abgeschlossen x', ' custom x', ' = x',
  ]);
  expect(conditionValueLabel({ operator: 'one_of', value: ['a', 'b'] })).toContain('a, b');
  expect(conditionValueLabel({ value: '' })).toBe('');
  expect(conditionValueLabel({ value: null })).toBe('');
  expect(conditionValueLabel({ value: undefined })).toBe('');
  const form = { value: 'x', keep: true };
  expect(changeConditionField(form, [], 'status')).toEqual(expect.objectContaining({ operator: 'status_is', value: 'completed' }));
  expect(changeConditionField(form, [{ name: 'upload', field_type: 'multiupload', options: ['Doc'] }], 'upload')).toEqual(expect.objectContaining({ operator: 'has_upload', value: 'Doc' }));
  expect(changeConditionField(form, [{ name: 'upload', field_type: 'multiupload' }], 'upload').value).toBe('');
  expect(changeConditionField(form, [{ name: 'choice', options: ['yes'] }], 'choice').value).toBe('yes');
  expect(changeConditionField(form, [{ name: 'plain' }], 'plain')).toEqual({ value: '', keep: true, field: 'plain', operator: 'equals' });
  expect(changeConditionField(form, [{ name: 'wrong', options: ['no'] }, { name: 'choice', options: ['yes'] }], 'choice')).toEqual({ value: 'yes', keep: true, field: 'choice', operator: 'equals' });
  expect(changeConditionField(form, [], 'missing')).toEqual({ value: '', keep: true, field: 'missing', operator: 'equals' });
  expect(changeConditionOperator({ value: 'x' }, 'one_of').value).toEqual(['x']);
  expect(changeConditionOperator({ value: '' }, 'not_one_of').value).toEqual([]);
  expect(changeConditionOperator({ value: ['x'] }, 'one_of').value).toEqual(['x']);
  expect(changeConditionOperator({ value: ['x'] }, 'equals').value).toBe('x');
  expect(changeConditionOperator({ value: [] }, 'contains').value).toBe('');
  expect(changeConditionOperator({ value: 'x' }, 'empty')).toEqual({ value: '', operator: 'empty' });
  expect(changeConditionOperator({ value: 'x' }, 'not_empty')).toEqual({ value: '', operator: 'not_empty' });
});

test('linear and dagre layouts position normal, conditional and invalid edges', () => {
  const steps = [
    step('decision', 1),
    step('b', 3, { conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1, value: 'b' }] }),
    step('a', 2, { conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1, value: 'a' }] }),
    step('merge', 4, { conditions: [{ action: 'hide', field: 'decision', operator: 'empty', source_step_order: 1 }] }),
  ];
  const positions = linearLayout(steps);
  expect(positions).toMatchSnapshot('conditional linear layout');
  expect(positions.a.x).toBe(positions.b.x);
  expect(positions.a.y).toBeLessThan(positions.b.y);
  expect(positions.merge.x).toBeGreaterThan(positions.b.x);
  const dagre = dagreLayout(steps, [{ source: 'decision', target: 'a' }, { source: '', target: 'a' }, { source: 'missing', target: 'a' }]);
  expect(dagre).toMatchSnapshot('dagre layout');
  expect(dagre.decision).toEqual(expect.objectContaining({ x: expect.any(Number), y: expect.any(Number) }));
  expect(dagreLayout([], [])).toEqual({});
  expect(validLayoutEdges(steps, [
    { source: 'decision', target: 'a' }, { source: '', target: 'a' }, { source: 'decision', target: '' }, { source: 'missing', target: 'a' }, { source: 'decision', target: 'missing' },
  ])).toEqual([{ source: 'decision', target: 'a' }]);
  const sparse = linearLayout([{ id: 'plain', order: 1 }, { id: 'branch', order: 2, conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1 }] }, { id: 'branch2', order: 3, conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1 }] }, { id: 'after', order: 4 }]);
  expect(sparse).toMatchSnapshot('sparse conditional layout');
  expect(sparse.branch).toEqual(expect.objectContaining({ x: expect.any(Number) }));
  expect(linearLayout([step('last', 3), step('first', 1), step('middle', 2)])).toEqual({
    first: { x: 20, y: 140 }, middle: { x: 300, y: 140 }, last: { x: 580, y: 140 },
  });
  const nonBranches = linearLayout([
    step('wrong-action', 1, { conditions: [{ action: 'block', field: 'decision', operator: 'not_equals', source_step_order: 9 }] }),
    step('wrong-field', 2, { conditions: [{ action: 'hide', field: 'status', operator: 'not_equals', source_step_order: 9 }] }),
    step('wrong-operator', 3, { conditions: [{ action: 'hide', field: 'decision', operator: 'equals', source_step_order: 9 }] }),
    step('no-conditions', 4, { conditions: undefined }),
  ]);
  expect(nonBranches).toEqual({
    'wrong-action': { x: 20, y: 140 }, 'wrong-field': { x: 300, y: 140 }, 'wrong-operator': { x: 580, y: 140 }, 'no-conditions': { x: 860, y: 140 },
  });
  expect(linearLayout([
    step('decision-source', 1),
    step('valued-branch', 2, { conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1, value: 'A' }] }),
    step('empty-branch', 3, { conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1 }] }),
  ])).toEqual({
    'decision-source': { x: 20, y: 140 }, 'empty-branch': { x: 300, y: 60 }, 'valued-branch': { x: 300, y: 220 },
  });
  const invalidPairs = (firstValue, secondValue) => linearLayout([
    step('first-invalid', 1, { conditions: [{ action: firstValue.action, field: firstValue.field, operator: firstValue.operator, source_step_order: 9 }] }),
    step('second-invalid', 2, { conditions: [{ action: secondValue.action, field: secondValue.field, operator: secondValue.operator, source_step_order: 9 }] }),
  ]);
  const separateColumns = { 'first-invalid': { x: 20, y: 140 }, 'second-invalid': { x: 300, y: 140 } };
  expect(invalidPairs({ action: 'block', field: 'decision', operator: 'not_equals' }, { action: 'block', field: 'decision', operator: 'not_equals' })).toEqual(separateColumns);
  expect(invalidPairs({ action: 'hide', field: 'status', operator: 'not_equals' }, { action: 'hide', field: 'status', operator: 'not_equals' })).toEqual(separateColumns);
  expect(invalidPairs({ action: 'hide', field: 'decision', operator: 'equals' }, { action: 'hide', field: 'decision', operator: 'equals' })).toEqual(separateColumns);
});

test('graph builder creates grouped dependency edges, read-only badges, saved positions and sequence arrows', () => {
  const callbacks = { onEdit: jest.fn(), onDelete: jest.fn() };
  const steps = [
    step('one', 1, { title: 'One', flow_position: { x: 9, y: 8 }, fields: [{ name: 'answer' }] }),
    step('two', 2, { flow_position: null, conditions: [
      { action: 'hide', source_step_order: 1, field: 'answer', operator: 'equals', value: 'yes' },
      { action: 'auto_complete', source_step_order: 1, field: 'answer', operator: 'equals', value: 'automatic' },
      { action: 'read_only', source_step_order: 1, field: '', operator: 'completed' },
      { action: 'block', all_of: [{ source_step_order: 1, field: 'answer', value: ['a', 'b'] }, { source_step_order: 99, field: 'x' }] },
    ] }),
    step('three', 3, { step_type: 'unknown', conditions: [{ action: 'block', source_step_order: 1, field: 'answer', operator: 'equals', value: 'later' }] }),
  ];
  const graph = buildGraph(steps, callbacks);
  expect(graph).toMatchSnapshot('editor graph');
  expect(graph.nodes[0].position).toEqual({ x: 9, y: 8 });
  expect(graph.nodes[1].position).toEqual({ x: 280, y: 140 });
  expect(graph.nodes[1].data.readOnlyRules[0]).toContain('#1 One');
  expect(graph.edges.some(edge => edge.id.startsWith('seq-'))).toBe(true);
  expect(graph.edges.some(edge => edge.label?.includes('UND'))).toBe(true);
  expect(graph.edges.every(edge => !edge.label?.includes('Schreibschutz'))).toBe(true);
  const dependency = buildGraph(steps, callbacks, 'dependency');
  expect(dependency).toMatchSnapshot('dependency graph');
  expect(dependency.edges.every(edge => !edge.id.startsWith('seq-'))).toBe(true);
  expect(buildGraph([step('solo', 1)], callbacks).nodes[0].position).toEqual({ x: 20, y: 140 });
  expect(buildGraph([step('last', 3), step('first', 1), step('middle', 2)], callbacks).nodes.map(node => node.id)).toEqual(['first', 'middle', 'last']);
  const branchGraph = buildGraph([
    step('decision', 1),
    step('upper', 2, { conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1, value: 'a' }] }),
    step('lower', 3, { conditions: [{ action: 'hide', field: 'decision', operator: 'not_equals', source_step_order: 1, value: 'b' }] }),
  ], callbacks);
  expect(branchGraph.nodes.map(node => node.position)).toEqual([{ x: 20, y: 140 }, { x: 300, y: 60 }, { x: 300, y: 220 }]);
  const mixedEdges = buildGraph([
    step('a', 1), step('b', 2, { conditions: [{ action: 'block', source_step_order: 1 }] }), step('c', 3, { conditions: [{ action: 'block', source_step_order: 1 }] }),
  ], callbacks).edges;
  expect(mixedEdges.filter(edge => edge.source === 'a' && edge.target === 'b')).toHaveLength(1);
  expect(mixedEdges.some(edge => edge.id === 'seq-b-c')).toBe(true);
  const skipTargetEdges = buildGraph([
    step('a', 1), step('b', 2), step('c', 3, { conditions: [{ action: 'block', source_step_order: 1 }] }),
  ], callbacks).edges;
  expect(skipTargetEdges.some(edge => edge.id === 'seq-a-b')).toBe(true);
  const sparse = buildGraph([
    { id: 's1', order: 1, title: 'Sparse' },
    { id: 's2', order: 2, title: 'Target', conditions: [{ source_step_order: 1 }, { action: 'custom', source_step_order: 1, field: '' }, { action: 'read_only', source_step_order: 99, field: '' }] },
  ], callbacks);
  expect(sparse).toMatchSnapshot('sparse graph');
  expect(sparse.edges.some(edge => edge.label.includes('Bedingung'))).toBe(true);
  expect(sparse.edges.some(edge => edge.label.includes('custom'))).toBe(true);
  expect(sparse.nodes[1].data.readOnlyRules[0]).toContain('#99');
});

test('step nodes render every simulation state and invoke edit/delete without bubbling', () => {
  const onEdit = jest.fn(); const onDelete = jest.fn(); const stopPropagation = jest.fn();
  const base = { id: 's', order: 1, title: 'Title', step_type: 'partner_selection', filter_tag: 'tag', duration_value: 2, duration_unit: 'days', readOnlyRules: ['first', 'second'], raw: { id: 's' }, onEdit, onDelete };
  const { container, rerender } = render(<StepNode data={{ ...base, simState: 'hidden' }} />);
  expect(container).toMatchSnapshot('hidden step node');
  expect(screen.getByText('#1 · Partner').parentElement).toHaveStyle({ background: '#2563eb' });
  expect(screen.getByText('#1 · Partner').parentElement.style.background).toBe('rgb(37, 99, 235)');
  expect(screen.getByTestId('sim-badge-s')).toHaveTextContent('versteckt');
  fireEvent.click(screen.getByTestId('flow-edit-s'), { stopPropagation });
  fireEvent.click(screen.getByTestId('flow-delete-s'), { stopPropagation });
  expect(onEdit).toHaveBeenCalledWith({ id: 's' }); expect(onDelete).toHaveBeenCalled();
  for (const simState of ['blocked', 'auto_complete', 'visible', undefined]) {
    rerender(<StepNode data={{ ...base, simState }} />);
    expect(container).toMatchSnapshot(`${simState || 'default'} step node`);
  }
  rerender(<StepNode data={{ ...base, isPlayback: true, readOnlyRules: [], duration_value: 0, filter_tag: '' }} />);
  expect(container).toMatchSnapshot('playback step node');
  expect(screen.getByTestId('flow-node-s')).toHaveAttribute('data-playback', 'true');
  rerender(<StepNode data={{ ...base, step_type: 'unknown' }} />);
  expect(screen.getByText('#1 · Formular')).toBeInTheDocument();
});

test('palette exposes all types and writes drag transfer metadata', () => {
  const { container } = render(<Palette />);
  expect(container).toMatchSnapshot('step palette');
  const transfer = { setData: jest.fn(), effectAllowed: '' };
  fireEvent.dragStart(screen.getByTestId('palette-item-decision'), { dataTransfer: transfer });
  expect(transfer.setData).toHaveBeenCalledWith('application/ihca-step-type', 'decision');
  expect(transfer.effectAllowed).toBe('copy');
});

test('condition modal handles hidden state, field/operator shapes, create, edit, cancel and delete', () => {
  const source = step('source', 1, { fields: [{ name: 'upload', label: '', field_type: 'multiupload', options: ['Passport'] }, { name: 'choice', label: 'Choice', field_type: 'selectbox', options: ['yes'] }] });
  const target = step('target', 2);
  const onCancel = jest.fn(); const onConfirm = jest.fn(); const onDelete = jest.fn();
  const { rerender, container } = render(<ConditionModal open={false} source={source} target={target} />);
  expect(container).toBeEmptyDOMElement();
  rerender(<ConditionModal open mode="create" source={source} target={target} onCancel={onCancel} onConfirm={onConfirm} />);
  expect(container).toMatchSnapshot('create condition modal');
  fireEvent.click(screen.getByTestId('condition-field-input'));
  fireEvent.change(screen.getByTestId('condition-operator-select'), { target: { value: 'one_of' } });
  expect(screen.getByTestId('condition-value-input')).toHaveAttribute('data-values', '["completed"]');
  fireEvent.click(screen.getByTestId('condition-value-input'));
  expect(screen.getByTestId('condition-value-input')).toHaveAttribute('data-values', '["a","b"]');
  fireEvent.change(screen.getByTestId('condition-operator-select'), { target: { value: 'empty' } });
  expect(screen.getByText('Kein Wert erforderlich')).toBeInTheDocument();
  expect(container).toMatchSnapshot('empty operator condition modal');
  fireEvent.change(screen.getByTestId('condition-operator-select'), { target: { value: 'equals' } });
  fireEvent.change(screen.getByTestId('condition-action-select'), { target: { value: 'block' } });
  fireEvent.click(screen.getByTestId('condition-confirm-btn'));
  expect(onConfirm).toHaveBeenCalledWith({ field: 'status', operator: 'equals', value: '', action: 'block' });
  fireEvent.click(screen.getByTestId('condition-cancel-btn'));
  expect(onCancel).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByTestId('condition-modal').parentElement);
  expect(onCancel).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByTestId('condition-modal'));
  expect(onCancel).toHaveBeenCalledTimes(2);
  rerender(<ConditionModal open mode="edit" source={source} target={target} initial={{ field: 'legacy', operator: 'equals', value: 'legacy', action: 'hide' }} onCancel={onCancel} onConfirm={onConfirm} onDelete={onDelete} />);
  expect(container).toMatchSnapshot('legacy condition modal');
  expect(screen.getByText('Regel bearbeiten')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('condition-delete-btn'));
  expect(onDelete).toHaveBeenCalled();

  rerender(<ConditionModal open mode="edit" source={source} target={target} initial={{ field: 'status', operator: 'one_of', value: '', action: 'hide' }} onCancel={onCancel} onConfirm={onConfirm} onDelete={onDelete} />);
  expect(container).toMatchSnapshot('status condition modal');
  fireEvent.click(screen.getByTestId('condition-value-input'));
  fireEvent.click(screen.getByTestId('condition-field-input'));
  fireEvent.change(screen.getByTestId('condition-operator-select'), { target: { value: 'not_one_of' } });
  expect(screen.getByTestId('condition-value-input')).toHaveAttribute('data-values');
  fireEvent.change(screen.getByTestId('condition-operator-select'), { target: { value: 'not_empty' } });
  expect(screen.getByText('Kein Wert erforderlich')).toBeInTheDocument();
  rerender(<ConditionModal open mode="edit" source={source} target={target} initial={{ field: 'upload', operator: 'equals', value: ['Passport'], action: 'hide' }} onCancel={onCancel} onConfirm={onConfirm} onDelete={onDelete} />);
  expect(container).toMatchSnapshot('upload condition modal');
  fireEvent.click(screen.getByTestId('condition-field-input'));
  fireEvent.change(screen.getByTestId('condition-operator-select'), { target: { value: 'contains' } });
  expect(screen.getByTestId('condition-value-input')).toHaveTextContent('select:completed');
  rerender(<ConditionModal open mode="edit" source={source} target={target} initial={{ field: '', operator: 'equals', value: '', action: 'hide' }} onCancel={onCancel} onConfirm={onConfirm} onDelete={onDelete} />);
  fireEvent.change(screen.getByTestId('condition-value-input'), { target: { value: 'typed' } });
  rerender(<ConditionModal open mode="edit" source={{ id: 's', order: 1, title: 'Sparse' }} target={target} initial={{ field: 'status', operator: 'one_of', value: 'completed' }} onCancel={onCancel} onConfirm={onConfirm} onDelete={onDelete} />);
  expect(container).toMatchSnapshot('sparse condition modal');
  fireEvent.click(screen.getByTestId('condition-value-input'));
  fireEvent.click(screen.getByTestId('condition-field-input'));
  rerender(<ConditionModal open mode="edit" source={source} target={target} initial={{ field: 'status', operator: 'one_of', value: '' }} onCancel={onCancel} onConfirm={onConfirm} onDelete={onDelete} />);
  rerender(<ConditionModal open mode="edit" source={source} target={target} initial={{ field: 'status', operator: 'equals', value: [] }} onCancel={onCancel} onConfirm={onConfirm} onDelete={onDelete} />);
  expect(screen.getByTestId('condition-value-input')).toHaveTextContent('select:');
  fireEvent.click(screen.getByTestId('condition-value-input'));
  expect(screen.getByTestId('condition-value-input')).toHaveTextContent('select:status');
  fireEvent.click(screen.getByTestId('condition-confirm-btn'));
  expect(onConfirm).toHaveBeenLastCalledWith({ action: 'hide', field: 'status', operator: 'equals', value: 'status' });
});

test('condition modal stores a free-text comparison value', () => {
  const onConfirm = jest.fn();
  render(<ConditionModal open mode="create" source={{ id: 'source', order: 1, title: 'Source', fields: [] }} target={{ id: 'target', order: 2, title: 'Target' }} onCancel={jest.fn()} onConfirm={onConfirm} />);
  fireEvent.change(screen.getByTestId('condition-value-input'), { target: { value: 'typed' } });
  expect(screen.getByTestId('condition-value-input')).toHaveTextContent('select:typed');
  fireEvent.click(screen.getByTestId('condition-confirm-btn'));
  expect(onConfirm).toHaveBeenCalledWith({ action: 'hide', field: '', operator: 'equals', value: 'typed' });
});

test('condition modal renders an empty scalar selection for an empty array value', () => {
  render(<ConditionModal open mode="edit" source={{ id: 'source', order: 1, title: 'Source', fields: [] }} target={{ id: 'target', order: 2, title: 'Target' }} initial={{ field: 'status', operator: 'equals', value: [] }} onCancel={jest.fn()} onConfirm={jest.fn()} />);
  expect(screen.getByTestId('condition-value-input')).toHaveTextContent(/^select:$/);
});

test('condition modal domain normalizes defaults, fields and configured values', () => {
  expect(createConditionForm()).toEqual({ action: 'hide', field: '', operator: 'equals', value: '' });
  expect(createConditionForm({ action: 'block', value: 0 })).toEqual({ action: 'block', field: '', operator: 'equals', value: 0 });
  const source = { fields: [{ name: 'plain' }, { name: 'choice', label: 'Choice', field_type: 'selectbox', options: ['yes', 2] }] };
  expect(conditionModalOptions(source, { field: 'choice', value: ['yes', 'legacy', 2] })).toEqual({
    fieldOptions: [
      { value: 'status', label: 'Schrittstatus', description: 'Systemfeld' },
      { value: 'plain', label: 'plain', description: 'plain · Feld' },
      { value: 'choice', label: 'Choice', description: 'choice · selectbox' },
    ],
    configuredValues: [{ value: 'yes', label: 'yes' }, { value: '2', label: '2' }, { value: 'legacy', label: 'legacy' }],
  });
  expect(conditionModalOptions({}, { field: 'legacy', value: '' })).toEqual({
    fieldOptions: [{ value: 'status', label: 'Schrittstatus', description: 'Systemfeld' }, { value: 'legacy', label: 'Bestehendes Feld: legacy' }], configuredValues: [],
  });
  expect(conditionModalOptions(source, { field: 'status', value: 'custom' }).configuredValues).toEqual([
    { value: 'pending', label: 'Ausstehend' }, { value: 'in_progress', label: 'In Bearbeitung' }, { value: 'completed', label: 'Abgeschlossen' }, { value: 'rejected', label: 'Abgelehnt' }, { value: 'custom', label: 'custom' },
  ]);
});

test('flow playback domain snapshots positions, simulation states and visible identities', () => {
  expect(flowPositionSnapshot([{ id: 'a', position: { x: 1, y: 2 } }, { id: 'b', position: { x: 3, y: 4 } }])).toEqual({ a: { x: 1, y: 2 }, b: { x: 3, y: 4 } });
  expect(flowStepId({ id: 'id', step_id: 'legacy' })).toBe('id');
  expect(flowStepId({ id: '', step_id: 'legacy' })).toBe('');
  expect(flowStepId({ step_id: 'legacy' })).toBe('legacy');
  const steps = [{ id: 'hidden', order: 4 }, { step_id: 'blocked', order: 2 }, { id: 'automatic', order: 3 }, { id: 'visible', order: 1 }];
  require('../features/steps').simulateJourney.mockReturnValueOnce({ hidden: new Set(['hidden']), blocked: new Set(['blocked']), autoComplete: new Set(['automatic']) });
  expect(simulatorStateMap(steps, { answer: true })).toEqual({ hidden: 'hidden', blocked: 'blocked', automatic: 'auto_complete', visible: 'visible' });
  expect(simulatorStateMap(steps, null)).toBeNull();
  const nodes = [{ id: 'a', data: { keep: true } }, { id: 'b', data: {} }];
  expect(decorateFlowNodes(nodes, { a: 'visible', b: 'blocked' }, 'b')).toEqual([
    { id: 'a', data: { keep: true, simState: 'visible' } }, { id: 'b', data: { simState: 'blocked', isPlayback: true } },
  ]);
  expect(decorateFlowNodes(nodes, null, null)).toEqual(nodes);
  expect(visiblePlaybackStepIds(steps, new Set(['hidden', 'blocked']))).toEqual(['visible', 'automatic']);
  expect(visiblePlaybackStepIds([{ id: 'visible', order: 1 }])).toEqual(['visible']);
  expect(visiblePlaybackStepIds([], new Set())).toEqual([]);
  expect(playbackFrame([{ id: 'a', duration_value: 48, duration_unit: 'hours' }], ['a'], 0)).toEqual({ days: 2, nextIndex: -1 });
  expect(playbackFrame([{ step_id: 'a', duration_value: 2, duration_unit: 'weeks' }], ['a', 'missing'], 0)).toEqual({ days: 14, nextIndex: 1 });
  expect(playbackFrame([{ id: 'other', duration_value: 99 }, { id: 'a', duration_value: 3, duration_unit: 'days' }], ['a'], 0)).toEqual({ days: 3, nextIndex: -1 });
  expect(playbackFrame([], ['missing'], 0)).toEqual({ days: 0, nextIndex: -1 });
  expect(playbackFrame([], [], -1)).toBeNull();
  expect(playbackFrame([], ['a'], 1)).toBeNull();
});

test('active playback identity distinguishes stopped, active and removed steps', () => {
  expect(activePlaybackId(['a'], -1)).toBeNull();
  expect(activePlaybackId(['a'], 0)).toBe('a');
  expect(activePlaybackId(['a'], 2)).toBeUndefined();
  expect(minimapNodeColor({ data: { step_type: 'form' } })).toBe('var(--brand-primary)');
  expect(minimapNodeColor({})).toBe('#94a3b8');
});

test('flow modal domain accepts only valid connections and condition edges', () => {
  const steps = [step('a', 1), step('b', 2)];
  expect(connectionModalState(steps, { source: 'a', target: 'b' })).toEqual({ mode: 'create', source: steps[0], target: steps[1], initial: null });
  expect(connectionModalState(steps, { source: 'a', target: 'b' }, true)).toBeNull();
  expect(connectionModalState(steps, { source: 'missing', target: 'b' })).toBeNull();
  expect(connectionModalState(steps, { source: 'a', target: 'missing' })).toBeNull();
  expect(connectionModalState(steps, { source: 'a', target: 'a' })).toBeNull();
  const edge = { source: 'a', target: 'b', data: { isCondition: true, condition: { action: 'hide' }, stepId: 'b', condIndex: 3 } };
  expect(edgeModalState(steps, edge)).toEqual({ mode: 'edit', source: steps[0], target: steps[1], initial: { action: 'hide' }, edgeData: { stepId: 'b', condIndex: 3 } });
  expect(edgeModalState(steps, null)).toBeNull();
  expect(edgeModalState(steps, {})).toBeNull();
  expect(edgeModalState(steps, { data: { isCondition: false } })).toBeNull();
  expect(edgeModalState(steps, { ...edge, source: 'missing' })).toBeNull();
  expect(edgeModalState(steps, { ...edge, target: 'missing' })).toBeNull();
});

test('flow layout and keyboard domain handles snapshots, statistics and shortcuts', () => {
  expect(isDependencyLayout('dependency')).toBe(true);
  expect(isDependencyLayout('editor')).toBe(false);
  expect(isDependencyLayout('')).toBe(false);
  expect(flowViewportCommand(true)).toEqual({ type: 'fit', options: { padding: 0.12, minZoom: 0.35, maxZoom: 0.9, duration: 200 } });
  expect(flowViewportCommand(false)).toEqual({ type: 'viewport', viewport: { x: 28, y: 245, zoom: 0.82 }, options: { duration: 200 } });
  require('../features/steps').simulateJourney.mockReturnValueOnce({ hidden: new Set(['a']), blocked: new Set(), autoComplete: new Set() });
  expect(playbackHiddenSteps([step('a', 1)], { profile: true })).toEqual(new Set(['a']));
  expect(playbackHiddenSteps([step('a', 1)], null)).toEqual(new Set());
  const nodes = [{ id: 'a', position: { x: 0, y: 0 } }, { id: 'b', position: { x: 1, y: 1 } }, { id: 'root', position: { x: 2, y: 2 } }];
  expect(nodeLayoutPatch({ id: 'a', position: { x: 4, y: 5 } })).toEqual({ a: { x: 4, y: 5 } });
  expect(nodeLayoutPatch(null)).toBeNull();
  expect(nodeLayoutPatch({ id: '', position: {} })).toBeNull();
  expect(nodeLayoutPatch({ id: 'a' })).toBeNull();
  expect(applyFlowSnapshot(nodes, { a: { x: 9, y: 8 } })).toEqual([{ id: 'a', position: { x: 9, y: 8 } }, nodes[1], nodes[2]]);
  expect(applyFlowSnapshot(nodes, null)).toBe(nodes);
  const edges = [{ source: 'a', target: 'b', data: { isDependency: true } }, { source: 'a', target: 'root', data: { isDependency: true } }, { source: 'b', target: 'root', data: {} }, { source: 'b', target: 'a' }];
  const steps = [step('a', 1, { conditions: [{ action: 'read_only' }, { action: 'hide' }] }), step('b', 2)];
  expect(dependencyGraphStats(edges, nodes, steps)).toEqual({ conditions: 2, readOnlyRules: 1, roots: 1, branches: 1 });
  expect(dependencyGraphStats([{ source: 'a', target: 'b', data: { isDependency: true } }], nodes, [{ id: 'a' }, { id: 'b', conditions: undefined }])).toEqual({ conditions: 1, readOnlyRules: 0, roots: 2, branches: 0 });
  const action = overrides => flowKeyboardAction({ ctrlKey: false, metaKey: false, shiftKey: false, key: 'x', target: {}, ...overrides });
  expect(action({ ctrlKey: true, key: 'z' })).toBe('undo');
  expect(action({ metaKey: true, key: 'z', shiftKey: true })).toBe('redo');
  expect(action({ ctrlKey: true, key: 'y' })).toBe('redo');
  expect(action({ ctrlKey: true, key: 'x' })).toBeNull();
  expect(action({ ctrlKey: true, key: 'x', shiftKey: true })).toBeNull();
  expect(action({ key: 'z' })).toBeNull();
  expect(action({ ctrlKey: true, key: 'z', target: undefined })).toBe('undo');
  for (const target of [{ tagName: 'input' }, { tagName: 'TEXTAREA' }, { tagName: 'SELECT' }, { isContentEditable: true }]) expect(action({ ctrlKey: true, key: 'z', target })).toBeNull();
});

test('default wrapper composes the flow provider and empty editor controls', () => {
  const add = jest.fn();
  const { container } = render(<StepsFlowBuilder steps={[]} onAddStep={add} onEdit={jest.fn()} onDelete={jest.fn()} />);
  expect(container).toMatchSnapshot('empty flow builder');
  expect(screen.getByTestId('steps-flow-builder')).toHaveAttribute('data-layout-mode', 'editor');
  expect(latestFlow()).toEqual(expect.objectContaining({ fitViewOptions: { padding: 0.12, minZoom: 0.35, maxZoom: 0.9 }, defaultViewport: { x: 28, y: 245, zoom: 0.82 } }));
  expect(screen.getByTestId('controls')).toHaveAttribute('data-props', '{"showInteractive":false}');
  expect(screen.getByTestId('minimap')).toHaveAttribute('data-props', '{"pannable":true,"zoomable":true}');
  expect(screen.getByTestId('minimap')).toHaveAttribute('data-form-color', 'var(--brand-primary)');
  expect(screen.getByTestId('minimap')).toHaveAttribute('data-fallback-color', '#94a3b8');
  fireEvent.click(screen.getByTestId('flow-add-step-btn'));
  fireEvent.click(screen.getByTestId('flow-empty-add-step-btn'));
  fireEvent.click(screen.getByTestId('minimap'));
  expect(add).toHaveBeenCalledTimes(2);
});

function latestFlow() {
  return mockFlowProps.mock.calls[mockFlowProps.mock.calls.length - 1][0];
}

test('editor flow handles simulation, connections, condition editing, drops, dragging, layout and history', () => {
  const callbacks = {
    onEdit: jest.fn(), onDelete: jest.fn(), onAddStep: jest.fn(), onAddStepWithType: jest.fn(),
    onConditionAdd: jest.fn(), onConditionUpdate: jest.fn(), onConditionDelete: jest.fn(), onSaveLayout: jest.fn(),
  };
  const steps = [
    step('a', 1, { duration_value: 24, duration_unit: 'hours', fields: [{ name: 'answer', options: ['yes'] }] }),
    step('b', 2, { duration_value: 1, duration_unit: 'weeks', conditions: [{ action: 'hide', source_step_order: 1, field: 'answer', operator: 'equals', value: 'yes' }] }),
    step('c', 3, { duration_value: 1, duration_unit: 'months' }),
    step('d', 4, { duration_value: 1, duration_unit: 'years' }),
  ];
  const { container } = render(<StepsFlowBuilder steps={steps} {...callbacks} />);
  expect(container).toMatchSnapshot('editor flow builder');
  fireEvent.click(screen.getByTestId('simulator'));
  expect(container).toMatchSnapshot('simulated flow builder');
  fireEvent.click(screen.getByTestId('flow-auto-layout-btn'));
  expect(callbacks.onSaveLayout).toHaveBeenCalledWith(linearLayout(steps));
  const nodeUpdater = mockSetNodes.mock.calls.find(call => typeof call[0] === 'function')?.[0];
  expect(nodeUpdater([{ id: 'a', position: { x: 0, y: 0 } }, { id: 'missing' }])[0].position).toEqual(expect.any(Object));

  act(() => latestFlow().onConnect({ source: 'a', target: 'b' }));
  expect(screen.getByTestId('condition-modal')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('condition-cancel-btn'));
  expect(screen.queryByTestId('condition-modal')).not.toBeInTheDocument();
  act(() => latestFlow().onConnect({ source: 'a', target: 'b' }));
  fireEvent.click(screen.getByTestId('condition-confirm-btn'));
  expect(callbacks.onConditionAdd).toHaveBeenCalledWith(steps[0], steps[1], { field: '', operator: 'equals', value: '', action: 'hide' });
  act(() => latestFlow().onConnect({ source: 'a', target: 'a' }));
  act(() => latestFlow().onConnect({ source: 'missing', target: 'b' }));
  act(() => latestFlow().onEdgeClick({}, null));
  act(() => latestFlow().onEdgeClick({}, { data: { isCondition: false } }));
  act(() => latestFlow().onEdgeClick({}, { source: 'missing', target: 'b', data: { isCondition: true } }));
  act(() => latestFlow().onEdgeClick({}, { source: 'a', target: 'b', data: { isCondition: true, condition: steps[1].conditions[0], stepId: 'b', condIndex: 0 } }));
  fireEvent.click(screen.getByTestId('condition-confirm-btn'));
  expect(callbacks.onConditionUpdate).toHaveBeenCalledWith('b', 0, { action: 'hide', source_step_order: 1, field: 'answer', operator: 'equals', value: 'yes' });
  act(() => latestFlow().onEdgeClick({}, { source: 'a', target: 'b', data: { isCondition: true, condition: steps[1].conditions[0], stepId: 'b', condIndex: 0 } }));
  fireEvent.click(screen.getByTestId('condition-delete-btn'));
  expect(callbacks.onConditionDelete).toHaveBeenCalledWith('b', 0);

  const transfer = { dropEffect: '', getData: jest.fn(() => ''), setData: jest.fn() };
  fireEvent.dragOver(screen.getByTestId('react-flow').parentElement, { dataTransfer: transfer });
  expect(transfer.dropEffect).toBe('copy');
  fireEvent.drop(screen.getByTestId('react-flow').parentElement, { dataTransfer: transfer, clientX: 10, clientY: 20 });
  expect(transfer.getData).toHaveBeenLastCalledWith('application/ihca-step-type');
  expect(callbacks.onAddStepWithType).not.toHaveBeenCalled();
  transfer.getData.mockReturnValue('decision');
  const dropTarget = screen.getByTestId('react-flow').parentElement;
  dropTarget.getBoundingClientRect = () => ({ left: 2, top: 3 });
  const dropEvent = new Event('drop', { bubbles: true, cancelable: true });
  Object.defineProperties(dropEvent, { dataTransfer: { value: transfer }, clientX: { value: 10 }, clientY: { value: 20 } });
  fireEvent(dropTarget, dropEvent);
  expect(transfer.getData).toHaveBeenLastCalledWith('application/ihca-step-type');
  expect(callbacks.onAddStepWithType).toHaveBeenCalledWith('decision', { x: 8, y: 17 });

  act(() => latestFlow().onNodeDragStart());
  const saveCountBeforeInvalidDrag = callbacks.onSaveLayout.mock.calls.length;
  act(() => latestFlow().onNodeDragStop({}, null));
  act(() => latestFlow().onNodeDragStop({}, { id: 'a' }));
  expect(callbacks.onSaveLayout).toHaveBeenCalledTimes(saveCountBeforeInvalidDrag);
  act(() => latestFlow().onNodeDragStop({}, { id: 'a', position: { x: 5, y: 6 } }));
  expect(callbacks.onSaveLayout).toHaveBeenCalledWith({ a: { x: 5, y: 6 } });
  mockHistory.undo.mockReturnValueOnce({ a: { x: 1, y: 2 } });
  mockHistory.redo.mockReturnValueOnce({ a: { x: 3, y: 4 } });
  fireEvent.click(screen.getByTestId('flow-undo-btn'));
  fireEvent.click(screen.getByTestId('flow-redo-btn'));
  const updaters = mockSetNodes.mock.calls.filter(call => typeof call[0] === 'function').map(call => call[0]);
  updaters.slice(-2).forEach(updater => updater([{ id: 'a', position: { x: 0, y: 0 } }, { id: 'b', position: { x: 0, y: 0 } }]));
  expect(updaters[updaters.length - 1]([{ id: 'a', position: { x: 0, y: 0 } }])).toEqual([{ id: 'a', position: { x: 3, y: 4 } }]);
  mockHistory.undo.mockReturnValueOnce(null);
  fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
  expect(mockHistory.undo).toHaveBeenCalledTimes(2);
  fireEvent.keyDown(window, { key: 'z', ctrlKey: true, shiftKey: true });
  expect(mockHistory.redo).toHaveBeenCalledTimes(2);
  fireEvent.keyDown(window, { key: 'y', metaKey: true });
  expect(mockHistory.redo).toHaveBeenCalledTimes(3);
  fireEvent.keyDown(window, { key: 'x', ctrlKey: true });
  fireEvent.keyDown(window, { key: 'x' });
  const controls = render(<><input data-testid="key-input" /><textarea data-testid="key-textarea" /><select data-testid="key-select" /><div data-testid="key-editable" contentEditable /></>);
  fireEvent.keyDown(screen.getByTestId('key-input'), { key: 'z', ctrlKey: true });
  fireEvent.keyDown(screen.getByTestId('key-textarea'), { key: 'z', ctrlKey: true });
  fireEvent.keyDown(screen.getByTestId('key-select'), { key: 'z', ctrlKey: true });
  fireEvent.keyDown(screen.getByTestId('key-editable'), { key: 'z', ctrlKey: true });
  controls.unmount();

  mockHistory.push.mockImplementationOnce(() => { throw new Error('layout'); });
  const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
  fireEvent.click(screen.getByTestId('flow-auto-layout-btn'));
  expect(warn).toHaveBeenCalledWith('Auto-layout failed:', expect.any(Error));
  warn.mockRestore();
  expect({
    setNodes: mockSetNodes.mock.calls,
    setEdges: mockSetEdges.mock.calls,
    viewport: mockSetViewport.mock.calls,
    fitView: mockFitView.mock.calls,
    historyPush: mockHistory.push.mock.calls,
    historyUndo: mockHistory.undo.mock.calls,
    historyRedo: mockHistory.redo.mock.calls,
    historyClear: mockHistory.clear.mock.calls,
  }).toMatchSnapshot('editor flow command trace');
});

test('fullscreen and playback controls cover start, stop, ETA completion and empty simulation', () => {
  jest.useFakeTimers();
  const requestFullscreen = jest.fn(() => Promise.reject(new Error('blocked')));
  Object.defineProperty(document, 'fullscreenElement', { configurable: true, writable: true, value: null });
  const { container, rerender } = render(<StepsFlowBuilder steps={[step('a', 1, { duration_value: 12, duration_unit: 'hours' }), step('b', 2)]} onEdit={jest.fn()} onDelete={jest.fn()} />);
  const root = screen.getByTestId('steps-flow-builder');
  root.requestFullscreen = requestFullscreen;
  fireEvent.click(screen.getByTestId('flow-fullscreen-btn'));
  expect(requestFullscreen).toHaveBeenCalled();
  document.fullscreenElement = root;
  document.exitFullscreen = jest.fn();
  fireEvent(document, new Event('fullscreenchange'));
  expect(root).toHaveAttribute('data-fullscreen', 'true');
  expect(container).toMatchSnapshot('fullscreen flow builder');
  fireEvent.click(screen.getByTestId('flow-fullscreen-btn'));
  expect(document.exitFullscreen).toHaveBeenCalled();
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  expect(screen.getByTestId('flow-playback-status')).toBeInTheDocument();
  expect(container).toMatchSnapshot('active playback flow builder');
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  expect(screen.queryByTestId('flow-playback-status')).not.toBeInTheDocument();
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  act(() => jest.advanceTimersByTime(1500));
  expect(screen.getByTestId('flow-playback-eta')).toHaveTextContent('1d');
  act(() => jest.advanceTimersByTime(1500));
  expect(screen.queryByTestId('flow-playback-status')).not.toBeInTheDocument();
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  fireEvent.click(screen.getByTestId('flow-playback-stop-btn'));
  rerender(<StepsFlowBuilder steps={[]} onEdit={jest.fn()} onDelete={jest.fn()} />);
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  expect({ setNodes: mockSetNodes.mock.calls, setEdges: mockSetEdges.mock.calls, viewport: mockSetViewport.mock.calls }).toMatchSnapshot('playback command trace');
  jest.useRealTimers();
});

test('dependency flow disables editing and reports graph statistics', () => {
  const steps = [step('a', 1), step('b', 2, { conditions: [{ action: 'block', source_step_order: 1 }, { action: 'read_only', source_step_order: 1 }] }), step('c', 3, { conditions: [{ action: 'hide', source_step_order: 1 }] })];
  const onSaveLayout = jest.fn();
  const { container } = render(<StepsFlowBuilder steps={steps} layoutMode="dependency" onEdit={jest.fn()} onDelete={jest.fn()} onSaveLayout={onSaveLayout} />);
  expect(container).toMatchSnapshot('dependency flow builder');
  expect(latestFlow()).toEqual(expect.objectContaining({ nodesConnectable: false, fitView: true, defaultViewport: undefined, minZoom: 0.25, proOptions: { hideAttribution: true } }));
  expect(screen.getByTestId('dependency-graph-stats')).toHaveTextContent('2 Kanten');
  expect(screen.queryByTestId('flow-palette')).not.toBeInTheDocument();
  act(() => latestFlow().onConnect({ source: 'a', target: 'b' }));
  act(() => latestFlow().onNodeDragStart());
  act(() => latestFlow().onNodeDragStop({}, { id: 'a', position: { x: 1, y: 2 } }));
  expect(mockHistory.push).not.toHaveBeenCalled();
  expect(onSaveLayout).not.toHaveBeenCalled();
  fireEvent.click(screen.getByTestId('flow-auto-layout-btn'));
  expect(mockFitView).toHaveBeenCalled();
  expect(mockHistory.push).toHaveBeenCalledTimes(1);
  expect(onSaveLayout).not.toHaveBeenCalled();
  const layoutUpdater = mockSetNodes.mock.calls.filter(call => typeof call[0] === 'function').at(-1)[0];
  const expectedPositions = dagreLayout(steps, buildGraph(steps, { onEdit: jest.fn(), onDelete: jest.fn() }, 'dependency').edges);
  const laidOut = layoutUpdater(steps.map(item => ({ id: item.id, position: { x: 0, y: 0 } })));
  expect(Object.fromEntries(laidOut.map(item => [item.id, item.position]))).toEqual(expectedPositions);
});

test('flow effects release browser listeners, animation frames and playback timers', () => {
  jest.useFakeTimers();
  const cancel = jest.fn();
  global.cancelAnimationFrame = cancel;
  const add = jest.spyOn(document, 'addEventListener');
  const remove = jest.spyOn(document, 'removeEventListener');
  const clear = jest.spyOn(global, 'clearTimeout');
  const { unmount } = render(<StepsFlowBuilder steps={[step('a', 1)]} onEdit={jest.fn()} onDelete={jest.fn()} />);
  expect(jest.getTimerCount()).toBe(1);
  expect(add).toHaveBeenCalledWith('fullscreenchange', expect.any(Function));
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  unmount();
  expect(remove).toHaveBeenCalledWith('fullscreenchange', expect.any(Function));
  expect(cancel).toHaveBeenCalledWith(expect.any(Number));
  expect(clear).toHaveBeenCalled();
  add.mockRestore();
  remove.mockRestore();
  clear.mockRestore();
  jest.useRealTimers();
});

test('playback supports profile filtering, step_id identities and a removed active step', () => {
  jest.useFakeTimers();
  const first = { step_id: 'legacy', id: '', order: 1, title: 'Legacy', step_type: 'form', duration_value: 1, duration_unit: 'days' };
  const second = step('second', 2);
  const { rerender } = render(<StepsFlowBuilder steps={[first, second]} onEdit={jest.fn()} onDelete={jest.fn()} />);
  fireEvent.click(screen.getByTestId('simulator'));
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  expect(screen.getByTestId('flow-playback-status')).toBeInTheDocument();
  rerender(<StepsFlowBuilder steps={[second]} onEdit={jest.fn()} onDelete={jest.fn()} />);
  act(() => jest.advanceTimersByTime(1500));
  fireEvent.click(screen.getByTestId('flow-playback-btn'));
  jest.useRealTimers();
});

test('fullscreen controls tolerate unavailable browser APIs and optional editor callbacks', () => {
  Object.defineProperty(document, 'fullscreenElement', { configurable: true, writable: true, value: null });
  render(<StepsFlowBuilder steps={[]} onEdit={jest.fn()} onDelete={jest.fn()} />);
  const root = screen.getByTestId('steps-flow-builder');
  root.requestFullscreen = undefined;
  fireEvent.click(screen.getByTestId('flow-fullscreen-btn'));
  fireEvent.click(screen.getByTestId('flow-add-step-btn'));
  fireEvent.click(screen.getByTestId('flow-empty-add-step-btn'));
  document.fullscreenElement = root;
  document.exitFullscreen = undefined;
  fireEvent.click(screen.getByTestId('flow-fullscreen-btn'));
});
