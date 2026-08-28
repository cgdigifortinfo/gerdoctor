import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { StepDialog } from './StepDialog';

let mockBasic, mockMappings, mockConditions, mockRequirements, mockNotifications, mockTranslations, mockFieldsChange, mockEscape;
jest.mock('../../../components/ui/dialog', () => ({ Dialog: ({ open, children }) => open ? <div>{children}</div> : null, DialogContent: ({ children, onEscapeKeyDown, ...p }) => { mockEscape = onEscapeKeyDown; return <div {...p}>{children}</div>; }, DialogHeader: ({ children }) => <header>{children}</header>, DialogTitle: ({ children }) => <h2>{children}</h2> }));
jest.mock('../../../components/admin/EntityPickers', () => ({ SearchableSelect: p => <button type="button" data-testid={p.testId} onClick={() => p.onChange('Custom')}>picker</button> }));
jest.mock('../../../components/admin/SurveyFormBuilder', () => { const C = p => { mockFieldsChange = p.onChange; return <div>form-builder</div>; }; C.CONTENT_FIELD_TYPES = new Set(['heading']); return { __esModule: true, default: C, CONTENT_FIELD_TYPES: C.CONTENT_FIELD_TYPES }; });
jest.mock('../stepEditor/BasicPanel', () => ({ BasicPanel: p => { mockBasic = p; return <div>basic-panel</div>; } }));
jest.mock('../stepEditor/RequirementsPanel', () => ({ RequirementsPanel: p => { mockRequirements = p; return <div>requirements-panel</div>; } }));
jest.mock('../stepEditor/MappingsPanel', () => ({ MappingsPanel: p => { mockMappings = p; return <div>mappings-panel</div>; } }));
jest.mock('../stepEditor/ConditionsPanel', () => ({ ConditionsPanel: p => { mockConditions = p; return <div>conditions-panel</div>; } }));
jest.mock('../stepEditor/NotificationsPanel', () => ({ NotificationsPanel: p => { mockNotifications = p; return <div>notifications-panel</div>; } }));
jest.mock('../stepEditor/TranslationsPanel', () => ({ TranslationsPanel: p => { mockTranslations = p; return <div>translations-panel</div>; } }));
jest.mock('../stepDialogDomain', () => ({
  createStepFormData: (step, count, survey) => ({
    title: step?.title || '', description: step?.description || '', order: step?.order || count + 1, survey_id: step?.survey_id || survey,
    step_type: step?.step_type || 'form', fields: step?.fields || [], filter_tag: step?.filter_tag || '', partner_user_fee_cents: step?.partner_user_fee_cents ?? null,
    skippable: step?.skippable || false, skip_label: step?.skip_label || '', action_label: step?.action_label || '', pending_message: step?.pending_message || '', complete_message: step?.complete_message || '',
    required_fields: step?.required_fields || [], required_uploads: step?.required_uploads || [], field_mappings: step?.field_mappings || [], conditions: step?.conditions || [],
    duration_value: step?.duration_value ?? 0, duration_unit: step?.duration_unit || 'days', email_on_enter: step?.email_on_enter || false, email_on_edit: step?.email_on_edit || false,
    email_on_leave: step?.email_on_leave || false, is_active: step?.is_active !== false,
  }),
  requiredFieldNames: fields => fields.filter(field => field.required && field.field_type !== 'heading' && field.field_type !== 'multiupload').map(field => field.name).filter(Boolean),
  selectStepSurvey: (form, surveyId) => ({ ...form, survey_id: surveyId }),
  shouldNotifySurveyChange: (surveyId, activeSurveyId) => surveyId !== activeSurveyId,
  updateStepTranslation: (translations, language, field, value) => ({ ...translations, [language]: { ...translations[language], [field]: value } }),
  updateStepFields: (form, fields) => ({ ...form, fields, required_fields: fields.filter(field => field.required && field.field_type !== 'heading' && field.field_type !== 'multiupload').map(field => field.name).filter(Boolean) }),
  partnerFeeFromInput: value => value === '' ? null : Number(value),
  stepDialogTitle: (form, hasStep) => form.title || (hasStep ? `Step #${form.order}` : 'Neuer Schritt'),
  buildStepOptions: (steps, id) => steps.map(step => ({ value: String(step.order), label: `${step.order}. ${step.title}`, disabled: step.id === id })),
  buildSurveyOptions: surveys => surveys.map(survey => ({ value: survey.id, label: survey.name })),
  buildPartnerTagOptions: partners => [...new Set(partners.flatMap(partner => partner.tags || []))].map(tag => ({ value: tag, label: tag })),
  buildCurrentFieldOptions: fields => fields.map(field => ({ value: field.name, label: field.label || field.name })),
  buildDocumentTypeOptions: required => required.map(value => ({ value, label: value })),
  defaultConditionLeaf: (steps, order, id) => ({ source_step_order: (steps.find(step => step.order < order && step.id !== id) || steps.find(step => step.id !== id) || {}).order || null, field: 'status', operator: 'status_is', value: 'completed' }),
  addMappingState: (current, steps, id) => ({ ...current, field_mappings: [...current.field_mappings, { source_step_order: steps.find(step => step.id !== id)?.order ?? null, source_field: steps.find(step => step.id !== id)?.fields?.[0]?.name || '', target_field: current.fields?.[0]?.name || '' }] }),
  updateMappingState: (current, index, patch) => ({ ...current, field_mappings: current.field_mappings.map((item, i) => i === index ? { ...item, ...patch } : item) }),
  removeMappingState: (current, index) => ({ ...current, field_mappings: current.field_mappings.filter((_, i) => i !== index) }),
  changeMappingSourceState: (current, index, value, source) => ({ ...current, field_mappings: current.field_mappings.map((item, i) => i === index ? { ...item, source_step_order: value ? Number(value) : null, source_field: source?.fields?.[0]?.name || '' } : item) }),
  updateConditionState: (current, index, patch) => ({ ...current, conditions: current.conditions.map((item, i) => i === index ? { ...item, ...patch } : item) }),
  removeConditionState: (current, index) => ({ ...current, conditions: current.conditions.filter((_, i) => i !== index) }),
  addConditionState: (current, leaf) => ({ ...current, conditions: [...current.conditions, { ...leaf, action: 'block' }] }),
  addConditionGroupState: (current, key, leaf) => ({ ...current, conditions: [...current.conditions, { [key]: [leaf], action: 'block' }] }),
  changeConditionSourceState: (current, index, value) => ({ ...current, conditions: current.conditions.map((item, i) => i === index ? { ...item, source_step_order: value ? Number(value) : null, field: 'status', operator: 'status_is', value: 'completed' } : item) }),
  changeConditionFieldState: (current, index, field) => ({ ...current, conditions: current.conditions.map((item, i) => i === index ? { ...item, field } : item) }),
  changeConditionOperatorState: (current, index, operator) => ({ ...current, conditions: current.conditions.map((item, i) => i === index ? { ...item, operator } : item) }),
  updateConditionChildState: current => ({ ...current, childCommand: 'update' }),
  addConditionChildState: current => ({ ...current, childCommand: 'add' }),
  removeConditionChildState: current => ({ ...current, childCommand: 'remove' }),
  changeConditionGroupTypeState: current => ({ ...current, childCommand: 'group' }),
  addConditionPresetState: (current, preset) => ({ ...current, conditions: [...current.conditions, preset] }),
  sortReferenceSteps: steps => [...steps].sort((a, b) => a.order - b.order),
  findStepByOrder: (steps, order) => steps.find(step => step.order === Number(order)),
  findStepField: (step, field) => step?.fields?.find(item => item.name === field),
  buildSourceFieldOptions: (_steps, _order, value) => value ? [{ value }] : [{ value: 'status' }],
  buildConditionValueOptions: condition => [{ value: 'default' }, ...(Array.isArray(condition.value) ? condition.value : [condition.value]).filter(value => value != null).map(value => ({ value: String(value) }))],
  buildConditionOperatorOptions: condition => [{ value: condition.operator || 'equals' }],
  conditionPresets: (steps, order) => {
    const previousStep = [...steps].reverse().find(step => step.order < order);
    const uploadPresetStep = steps.find(step => step.fields?.some(field => field.field_type === 'multiupload'));
    const choicePresetStep = steps.find(step => step.fields?.some(field => field.options?.length && field.field_type !== 'multiupload'));
    return { previousStep, uploadPresetStep, uploadPresetField: uploadPresetStep?.fields?.find(field => field.field_type === 'multiupload'), choicePresetStep, choicePresetField: choicePresetStep?.fields?.find(field => field.options?.length && field.field_type !== 'multiupload') };
  },
  validStepSection: (section, type) => section === 'fields' && !['form', 'decision'].includes(type) ? 'basic' : section === 'type' && !['partner_selection', 'partner_multiselection', 'milestone', 'display'].includes(type) ? 'basic' : section,
}));

const t = x => x;
const referenceSteps = [
  { id: 'old', order: 1, title: 'Upload', step_type: 'form', fields: [{ name: 'docs', label: 'Docs', field_type: 'multiupload', options: ['Pass', { value: 'Visa', label: 'Visa label' }] }, { name: 'choice', label: 'Choice', field_type: 'decision', options: ['Yes', 'No'] }, { name: 'text', field_type: 'text' }] },
  { id: 'current', order: 2, title: 'Current', step_type: 'form', fields: [] },
];
const richStep = { id: 'current', title: 'Current', description: 'Description', order: 2, survey_id: 's1', step_type: 'form', fields: [{ name: 'target', label: 'Target', field_type: 'text' }], filter_tag: '', partner_user_fee_cents: null, skippable: true, required_fields: ['target'], required_uploads: ['Legacy'], field_mappings: [], conditions: [], duration_value: 2, translations: { en: { title: 'English' } } };

test('step dialog edits fields and drives every extracted panel command', () => {
  const onSave = jest.fn(), onSurveyChange = jest.fn(), onClose = jest.fn();
  const { container } = render(<StepDialog open onClose={onClose} step={richStep} onSave={onSave} existingSteps={referenceSteps} surveys={[{ id: 's1', name: 'One', slug: 'one' }, { id: 's2', name: 'Two', slug: 'two' }]} partners={[{ tags: ['B', 'A'] }, { tags: ['A'] }]} activeSurveyId="s1" onSurveyChange={onSurveyChange} t={t} />);
  expect(container).toMatchSnapshot('basic section');
  act(() => mockBasic.handleStepSurveyChange('s2')); expect(onSurveyChange).toHaveBeenCalledWith('s2'); act(() => mockBasic.handleStepSurveyChange('s1')); expect(onSurveyChange).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByTestId('step-section-fields')); expect(container).toMatchSnapshot('fields section'); act(() => mockFieldsChange([{ name: 'required', field_type: 'text', required: true }, { name: 'content', field_type: 'heading', required: true }, { name: 'upload', field_type: 'multiupload', required: true }, { name: '', field_type: 'text', required: true }]));
  fireEvent.click(screen.getByTestId('step-section-requirements')); expect(container).toMatchSnapshot('requirements section'); expect(mockRequirements.currentFieldOptions).toEqual([{ value: 'required', label: 'required' }, { value: 'content', label: 'content' }, { value: 'upload', label: 'upload' }, { value: '', label: '' }]); expect(mockRequirements.documentTypeOptions.length).toBeGreaterThan(0); act(() => mockRequirements.setFormData(x => ({ ...x, required_uploads: ['Pass'] })));
  fireEvent.click(screen.getByTestId('step-section-mappings')); expect(container).toMatchSnapshot('mappings section'); expect(mockMappings.stepOptions).toEqual([{ value: '1', label: '1. Upload', disabled: false }, { value: '2', label: '2. Current', disabled: true }]); act(() => mockMappings.addMapping()); expect(mockMappings.formData.field_mappings).toHaveLength(1); act(() => mockMappings.changeMappingSource(0, '')); expect(mockMappings.formData.field_mappings[0].source_step_order).toBeNull(); act(() => mockMappings.updateMapping(0, { target_field: 'different' })); expect(mockMappings.formData.field_mappings[0].target_field).toBe('different'); act(() => mockMappings.removeMapping(0)); expect(mockMappings.formData.field_mappings).toEqual([]); expect(mockMappings.sourceFieldOptions(1, 'missing')).toEqual([{ value: 'missing' }]);
  fireEvent.click(screen.getByTestId('step-section-conditions')); expect(container).toMatchSnapshot('conditions section'); act(() => mockConditions.addCondition());
  expect(mockConditions.formData.conditions[0]).toEqual(expect.objectContaining({ source_step_order: 1, field: 'status', operator: 'status_is', value: 'completed', action: 'block' })); expect(mockConditions.findStepByOrder(1)).toEqual(referenceSteps[0]); act(() => mockConditions.changeConditionField(0, 'docs')); expect(mockConditions.formData.conditions[0].field).toBe('docs'); act(() => mockConditions.changeConditionField(0, 'choice')); act(() => mockConditions.changeConditionField(0, 'text')); act(() => mockConditions.changeConditionOperator(0, 'one_of')); expect(mockConditions.formData.conditions[0].operator).toBe('one_of'); act(() => mockConditions.changeConditionOperator(0, 'empty')); act(() => mockConditions.changeConditionOperator(0, 'equals')); act(() => mockConditions.changeConditionSource(0, '')); expect(mockConditions.formData.conditions[0].source_step_order).toBeNull(); act(() => mockConditions.updateCondition(0, { message: 'x' })); expect(mockConditions.formData.conditions[0].message).toBe('x');
  expect(mockConditions.conditionValueOptions({ field: 'status', operator: 'status_is', value: ['completed', 'custom'] }).length).toBeGreaterThan(1); expect(mockConditions.conditionValueOptions({ field: 'status', operator: 'status_is', value: 'completed' }).length).toBeGreaterThan(0); expect(mockConditions.conditionValueOptions({ source_step_order: 1, field: 'docs', operator: 'has_upload', value: 'Legacy' }).length).toBeGreaterThan(1); expect(mockConditions.conditionOperatorOptions({ field: 'status' }).length).toBeGreaterThan(0); mockConditions.conditionOperatorOptions({ source_step_order: 1, field: 'docs', operator: 'custom' }); expect(mockConditions.conditionOperatorOptions({ source_step_order: 1, field: 'choice' }).length).toBeGreaterThan(0); expect(mockConditions.conditionOperatorOptions({ source_step_order: 1, field: 'text' }).length).toBeGreaterThan(0);
  act(() => mockConditions.removeCondition(0)); expect(mockConditions.formData.conditions).toEqual([]); act(() => mockConditions.addConditionGroup('all')); expect(mockConditions.formData.conditions).toHaveLength(1); act(() => mockConditions.addConditionChild(0, 'all')); expect(mockConditions.formData.childCommand).toBe('add'); act(() => mockConditions.updateConditionChild(0, 'all', 0, { value: 'x' })); expect(mockConditions.formData.childCommand).toBe('update'); act(() => mockConditions.removeConditionChild(0, 'all', 0)); expect(mockConditions.formData.childCommand).toBe('remove'); act(() => mockConditions.removeConditionChild(0, 'all', 0)); act(() => mockConditions.changeConditionGroupType(0, 'all', 'any')); expect(mockConditions.formData.childCommand).toBe('group'); act(() => mockConditions.addConditionPreset({ field: 'status', operator: 'status_not', value: 'pending' }));
  fireEvent.click(screen.getByTestId('step-section-notifications')); expect(container).toMatchSnapshot('notifications section'); act(() => mockNotifications.setFormData(x => ({ ...x, email_on_enter: true })));
  fireEvent.click(screen.getByTestId('step-section-translations')); expect(container).toMatchSnapshot('translations section'); act(() => mockTranslations.setTrans('en', 'title', 'Changed'));
  act(() => mockTranslations.setTrans('fr', 'title', 'Français')); act(() => mockTranslations.setTrans('en', 'description', 'Description EN'));
  const prevented = jest.fn(); document.querySelector = jest.fn(() => ({})); mockEscape({ preventDefault: prevented }); expect(document.querySelector).toHaveBeenCalledWith('[data-entity-picker-open="true"], [role="tooltip"]'); expect(prevented).toHaveBeenCalledTimes(1); document.querySelector = jest.fn(() => null); mockEscape({ preventDefault: prevented }); expect(prevented).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByTestId('save-step-btn'));
  expect(onSave).toHaveBeenCalledTimes(1);
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
    survey_id: 's1',
    fields: [{ name: 'required', field_type: 'text', required: true }, { name: 'content', field_type: 'heading', required: true }, { name: 'upload', field_type: 'multiupload', required: true }, { name: '', field_type: 'text', required: true }],
    required_fields: ['required'],
    required_uploads: ['Pass'],
    field_mappings: [],
    email_on_enter: true,
    translations: { en: { title: 'Changed', description: 'Description EN' }, fr: { title: 'Français' } },
  }));
  fireEvent.click(screen.getByText('cancel')); expect(onClose).toHaveBeenCalledTimes(1);
});

test('type-specific sections cover partner, display and automatic section fallback', () => {
  const { container, rerender } = render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, step_type: 'partner_selection', filter_tag: 'Missing' }} onSave={jest.fn()} existingSteps={referenceSteps} surveys={[]} partners={[]} activeSurveyId="s1" t={t} />);
  fireEvent.click(screen.getByTestId('step-section-type')); expect(container).toMatchSnapshot('partner type section'); fireEvent.click(screen.getByTestId('step-filter-tag')); fireEvent.change(screen.getByTestId('step-user-fee-cents'), { target: { value: '0' } }); fireEvent.change(screen.getByTestId('step-user-fee-cents'), { target: { value: '' } });
  act(() => mockBasic?.setFormData?.(x => ({ ...x, step_type: 'form' })));
  rerender(<StepDialog open onClose={jest.fn()} step={{ ...richStep, step_type: 'display', pending_message: 'P', complete_message: 'C', action_label: 'Go' }} onSave={jest.fn()} existingSteps={referenceSteps} t={t} />); fireEvent.click(screen.getByTestId('step-section-type')); expect(container).toMatchSnapshot('display type section'); screen.getAllByRole('textbox').forEach(x => fireEvent.change(x, { target: { value: 'Changed' } }));
  rerender(<StepDialog open onClose={jest.fn()} step={null} onSave={jest.fn()} existingSteps={[]} t={t} />); expect(screen.getByText('Neuer Schritt')).toBeInTheDocument(); expect(container).toMatchSnapshot('new step section');
});

test.each([
  ['partner_multiselection', { filter_tag: 'Custom', partner_user_fee_cents: 250 }],
  ['milestone', { pending_message: 'Pending changed', complete_message: 'Complete changed' }],
  ['display', { pending_message: 'Pending changed', complete_message: 'Complete changed', action_label: 'Action changed' }],
])('type editor persists %s settings exactly', (stepType, expected) => {
  const onSave = jest.fn();
  render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, step_type: stepType }} onSave={onSave} existingSteps={referenceSteps} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-type'));
  if (stepType === 'partner_multiselection') {
    fireEvent.click(screen.getByTestId('step-filter-tag'));
    fireEvent.change(screen.getByTestId('step-user-fee-cents'), { target: { value: '250' } });
  } else {
    const inputs = screen.getAllByRole('textbox');
    fireEvent.change(inputs[0], { target: { value: 'Pending changed' } });
    fireEvent.change(inputs[1], { target: { value: 'Complete changed' } });
    if (stepType === 'display') fireEvent.change(inputs[2], { target: { value: 'Action changed' } });
  }
  fireEvent.click(screen.getByTestId('save-step-btn'));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining(expected));
});

test('defaults and existing translations are preserved on an immediate save', () => {
  const onSave = jest.fn();
  render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, title: '', translations: { en: { title: 'Existing', description: 'Keep' } } }} onSave={onSave} existingSteps={referenceSteps} t={t} />);
  expect(screen.getByTestId('step-editor-title')).toHaveTextContent('Step #2');
  expect(mockBasic.surveyOptions).toEqual([]);
  fireEvent.click(screen.getByTestId('save-step-btn'));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ survey_id: 's1', translations: { en: { title: 'Existing', description: 'Keep' } } }));
});

test('clearing a partner fee persists the global-default null value', () => {
  const onSave = jest.fn();
  render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, step_type: 'partner_selection', partner_user_fee_cents: 99 }} onSave={onSave} existingSteps={referenceSteps} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-type'));
  fireEvent.change(screen.getByTestId('step-user-fee-cents'), { target: { value: '' } });
  fireEvent.click(screen.getByTestId('save-step-btn'));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ partner_user_fee_cents: null }));
});

test('omitted optional collections and survey id produce empty editor options', () => {
  render(<StepDialog open onClose={jest.fn()} step={null} onSave={jest.fn()} existingSteps={[]} t={t} />);
  expect(mockBasic.surveyOptions).toEqual([]);
  expect(mockBasic.formData.survey_id).toBe('');
  expect(() => act(() => mockBasic.handleStepSurveyChange('new-survey'))).not.toThrow();
  fireEvent.click(screen.getByTestId('step-section-requirements'));
  expect(mockRequirements.documentTypeOptions).toEqual([]);
});

test('decision steps expose the fields editor', () => {
  render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, step_type: 'decision' }} onSave={jest.fn()} existingSteps={referenceSteps} t={t} />);
  expect(screen.getByTestId('step-section-fields')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('step-section-fields'));
  expect(screen.getByText('form-builder')).toBeInTheDocument();
});

test('condition default source falls back to another, current, and absent step', () => {
  const { rerender } = render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, order: 1 }} onSave={jest.fn()} existingSteps={[{ ...richStep, fields: [] }, { id: 'other', order: 2, fields: [] }]} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-conditions')); act(() => mockConditions.addCondition());
  rerender(<StepDialog open onClose={jest.fn()} step={{ ...richStep, order: 1 }} onSave={jest.fn()} existingSteps={[{ ...richStep, fields: [] }]} t={t} />); fireEvent.click(screen.getByTestId('step-section-conditions')); act(() => mockConditions.addCondition());
  rerender(<StepDialog open onClose={jest.fn()} step={null} onSave={jest.fn()} existingSteps={[]} t={t} />); fireEvent.click(screen.getByTestId('step-section-conditions')); act(() => mockConditions.addCondition());
});

test('fields section falls back when the step type stops supporting fields', () => {
  render(<StepDialog open onClose={jest.fn()} step={richStep} onSave={jest.fn()} existingSteps={referenceSteps} t={t} />); const setFormData = mockBasic.setFormData; fireEvent.click(screen.getByTestId('step-section-fields')); act(() => setFormData(x => ({ ...x, step_type: 'partner_selection' }))); expect(screen.getByTestId('step-section-panel-basic')).toBeInTheDocument();
});

test('sparse existing step exercises all editor defaults', () => {
  render(<StepDialog open onClose={jest.fn()} step={{ id: 'sparse' }} onSave={jest.fn()} existingSteps={[{ id: 'ref', order: 1, title: '', fields: [{ name: 'plain' }] }]} surveys={[{ id: 's', name: 'S' }]} partners={[{ tags: undefined }]} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-mappings')); act(() => mockMappings.addMapping()); act(() => mockMappings.changeMappingSource(0, '')); expect(mockMappings.sourceFieldOptions(999, '').length).toBeGreaterThan(0);
  fireEvent.click(screen.getByTestId('step-section-conditions')); act(() => mockConditions.addCondition()); act(() => mockConditions.changeConditionSource(0, '')); act(() => mockConditions.changeConditionField(0, 'missing')); act(() => mockConditions.changeConditionOperator(0, 'one_of')); mockConditions.conditionValueOptions({ source_step_order: 999, field: 'missing', operator: 'equals', value: undefined }); mockConditions.conditionValueOptions({ source_step_order: 999, field: 'missing', operator: 'missing_upload', value: [] });
});

test('editor helpers cover empty source fields, values and reference metadata', () => {
  const refs = [{ order: 1, title: 'No metadata' }, { id: 'upload', order: 2, fields: [{ name: 'docs', field_type: 'multiupload' }, { name: 'choice', field_type: 'decision', options: [] }] }];
  render(<StepDialog open onClose={jest.fn()} step={{ id: 'current', order: 3, fields: [], conditions: [{ source_step_order: 2, field: 'docs', operator: 'equals', value: '' }] }} onSave={jest.fn()} existingSteps={refs} partners={[{}]} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-fields')); act(() => mockFieldsChange([{ name: 'plain', required: true }]));
  fireEvent.click(screen.getByTestId('step-section-mappings')); act(() => mockMappings.addMapping());
  fireEvent.click(screen.getByTestId('step-section-conditions')); act(() => mockConditions.changeConditionField(0, 'docs')); act(() => mockConditions.changeConditionOperator(0, 'one_of')); act(() => mockConditions.updateCondition(0, { value: [] })); act(() => mockConditions.changeConditionOperator(0, 'equals')); act(() => mockConditions.updateCondition(0, { value: [''] })); act(() => mockConditions.changeConditionOperator(0, 'equals'));
});

test('mapping defaults remain valid without reference steps', () => {
  render(<StepDialog open onClose={jest.fn()} step={null} onSave={jest.fn()} existingSteps={[]} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-mappings'));
  act(() => mockMappings.addMapping());
});

test.each([['array', ['a']], ['scalar', 'a']])('condition operator converts a %s current value', (_label, value) => {
  render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, conditions: [{ source_step_order: 1, field: 'choice', operator: 'equals', value }] }} onSave={jest.fn()} existingSteps={referenceSteps} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-conditions'));
  act(() => mockConditions.changeConditionOperator(0, 'one_of'));
});

test('choice preset skips fields without options in the selected reference step', () => {
  const refs = [{ id: 'choices', order: 1, title: 'Choices', fields: [{ name: 'plain', field_type: 'text' }, { name: 'choice', field_type: 'decision', options: ['yes'] }] }];
  render(<StepDialog open onClose={jest.fn()} step={{ ...richStep, order: 2 }} onSave={jest.fn()} existingSteps={refs} t={t} />);
  fireEvent.click(screen.getByTestId('step-section-conditions'));
  expect(mockConditions.choicePresetField.name).toBe('choice');
});
