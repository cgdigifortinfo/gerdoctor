import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import UserDashboard from './UserDashboard';
import { filesAPI, formatApiError, notificationAPI, partnersAPI, stepsAPI } from '../lib/api';
import { toast } from 'sonner';

const mockNavigate = jest.fn();
let mockAuth;
let mockLanguage;
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate, Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a> }), { virtual: true });
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => mockAuth }));
jest.mock('../contexts/LanguageContext', () => ({ useLanguage: () => mockLanguage }));
jest.mock('../lib/api', () => ({
  stepsAPI: { getBootstrap: jest.fn(), updateProgress: jest.fn() },
  partnersAPI: { getAll: jest.fn(), submit: jest.fn(), submitMulti: jest.fn() },
  filesAPI: { upload: jest.fn(), getUrl: jest.fn(id => `/files/${id}`) },
  notificationAPI: { updatePreferences: jest.fn() }, formatApiError: jest.fn(() => 'api error'),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('../components/ThemeLangToggle', () => ({ ThemeLangToggle: () => <i /> }));
jest.mock('../components/Logo', () => ({ Logo: () => <i /> }));
jest.mock('../components/JourneyProgressIndicator', () => ({ JourneyProgressIndicator: ({ currentStep }) => <div data-testid="journey">{currentStep}</div> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, asChild, ...props }) => asChild ? <>{children}</> : <button {...props}>{children}</button> }));
jest.mock('../components/ui/select', () => ({
  Select: ({ children, onValueChange }) => <div>{children}<button data-testid="mock-select" onClick={() => onValueChange('choice')}>select</button></div>,
  SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => <i />,
}));
jest.mock('../components/ui/switch', () => ({ Switch: ({ checked, onCheckedChange }) => <button data-testid="switch" onClick={() => onCheckedChange(!checked)}>{String(checked)}</button> }));

const fields = [
  { name: 'heading', field_type: 'heading', content: 'Heading' }, { name: 'paragraph', field_type: 'paragraph', content: 'Paragraph' },
  { name: 'html', field_type: 'html', content: '<b>HTML</b>' }, { name: 'image', field_type: 'image', image_url: '/image.png', caption: 'Caption' },
  { name: 'divider', field_type: 'divider' }, { name: 'select', field_type: 'select', options: ['A'], required: true, label: 'Select' },
  { name: 'radio', field_type: 'radio', options: ['R'], label: 'Radio' }, { name: 'checks', field_type: 'multiselect', options: ['C'], label: 'Checks' },
  { name: 'agree', field_type: 'checkbox', label: 'Agree' }, { name: 'notes', field_type: 'textarea', label: 'Notes' },
  { name: 'file', field_type: 'file', label: 'File' }, { name: 'multi', field_type: 'multiupload', label: 'Multi', document_types: ['Passport'] },
  { name: 'date', field_type: 'date', label: 'Date' }, { name: 'number', field_type: 'number', label: 'Number' }, { name: 'text', field_type: 'text', label: 'Text' },
];
const survey = { id: 'survey', order: 1, title: 'Survey', description: 'Description', step_type: 'form', duration_value: 1, fields, required_fields: ['select'], required_uploads: ['Passport'], skippable: true };

const bootstrap = (overrides = {}) => ({ data: {
  steps: [survey], progress: [], all_step_data: [{ order: 1, status: 'pending', data: {} }], history: [],
  estimated_completion: '2026-12-10', notification_preferences: { email_on_step_enter: true, email_on_step_edit: false, email_on_step_leave: true }, settings: {}, ...overrides,
} });

beforeAll(() => { HTMLElement.prototype.scrollIntoView = jest.fn(); });

beforeEach(() => {
  jest.clearAllMocks();
  mockAuth = { user: { name: 'Doctor' }, logout: jest.fn().mockResolvedValue(), impersonating: false, stopImpersonation: jest.fn() };
  mockLanguage = { t: key => key, lang: 'de', localize: (item, field) => item[field] || '' };
  formatApiError.mockReturnValue('api error');
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap()); stepsAPI.updateProgress.mockResolvedValue({});
  partnersAPI.getAll.mockResolvedValue({ data: [] }); partnersAPI.submit.mockResolvedValue({}); partnersAPI.submitMulti.mockResolvedValue({});
  filesAPI.upload.mockResolvedValue({ data: { id: 'file-id', filename: 'demo.pdf' } }); filesAPI.getUrl.mockImplementation(id => `/files/${id}`); notificationAPI.updatePreferences.mockResolvedValue({});
});

test('renders and operates the complete survey field palette', async () => {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 500 });
  render(<UserDashboard />);
  expect(screen.getByText('loading')).toBeInTheDocument();
  await screen.findAllByText('Survey');
  expect(screen.getAllByTestId('content-field-html')[0]).toHaveTextContent('HTML');
  fireEvent.click(screen.getAllByTestId('mock-select')[0]);
  fireEvent.click(screen.getAllByLabelText('R')[0]);
  fireEvent.click(screen.getAllByLabelText('C')[0]);
  fireEvent.click(screen.getAllByLabelText('C')[0]);
  fireEvent.click(screen.getAllByTestId('form-field-agree')[0]);
  fireEvent.change(screen.getAllByTestId('form-field-notes')[0], { target: { value: 'notes' } });
  fireEvent.change(screen.getAllByTestId('form-field-text')[0], { target: { value: 'text' } });
  const pdf = new File(['x'], 'demo.pdf', { type: 'application/pdf' });
  fireEvent.change(screen.getAllByTestId('form-field-file')[0], { target: { files: [pdf] } });
  await waitFor(() => expect(filesAPI.upload).toHaveBeenCalled());
  fireEvent.click(screen.getAllByTestId('add-multiupload-multi')[0]);
  fireEvent.click(screen.getAllByTestId('complete-step-btn')[0]);
  expect(await screen.findAllByTestId('validation-errors')).not.toHaveLength(0);
  fireEvent.click(screen.getByTestId('timeline-btn'));
  expect(screen.getByTestId('timeline-panel')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('settings-btn'));
  fireEvent.click(screen.getAllByTestId('switch')[0]);
  fireEvent.click(screen.getByTestId('save-notif-prefs-btn'));
  await waitFor(() => expect(notificationAPI.updatePreferences).toHaveBeenCalled());
  fireEvent.click(screen.getByTestId('logout-btn'));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/'));
  await waitFor(() => expect(HTMLElement.prototype.scrollIntoView).toHaveBeenCalled(), { timeout: 600 });
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 });
});

test('renders alternate field configuration, translations and populated values', async () => {
  mockLanguage = { t: () => '', lang: 'en', localize: (item, field) => item[field] || '' };
  const alternate = { id: 'alternate', order: 1, title: 'Alternate', description: '', step_type: 'form', duration_value: 1,
    translations: { en: { field_labels: { translated: 'Translated label' } } },
    fields: [
      { name: 'low', field_type: 'heading', heading_level: 1, label: 'Low' }, { name: 'high', field_type: 'heading', heading_level: 9, label: 'High' },
      { name: 'paragraph', field_type: 'paragraph', label: 'Fallback paragraph' }, { name: 'image', field_type: 'image', image_url: 'data:image/png;base64,x' },
      { name: 'translated', field_type: 'selectbox', options: undefined, help_text: 'Select help' },
      { name: 'radio', field_type: 'radio', options: undefined, help_text: 'Radio help' }, { name: 'multi', field_type: 'multiselect', options: undefined, help_text: 'Multi help' },
      { name: 'check', field_type: 'checkbox', help_text: 'Check help' }, { name: 'area', field_type: 'textarea', rows: 0, help_text: 'Area help' },
      { name: 'upload', field_type: 'upload', multiple: true, help_text: 'Upload help' },
      { name: 'phone', field_type: 'phone' }, { name: 'email', field_type: 'email' }, { name: 'time', field_type: 'time' },
      { name: 'defaulted', field_type: 'text', default_value: 'Default' }, { name: 'third', field_type: 'text', width: 'third' }, { name: 'half', field_type: 'text', width: 'half' },
    ] };
  await renderStep(alternate, [{ step_id: 'alternate', status: 'in_progress', data: { multi: ['x'], check: true, upload: [{ id: 'a', filename: 'a.pdf' }], translated: 'x' } }]);
  expect(screen.getAllByText('Translated label')).not.toHaveLength(0);
  expect(screen.getAllByText('Fallback paragraph')).not.toHaveLength(0);
});

test('validates every empty required-value shape and missing field/upload arrays', async () => {
  const step = { id: 'matrix', order: 1, title: 'Validation Matrix', step_type: 'form', duration_value: 1,
    required_fields: ['undefinedValue', 'nullValue', 'emptyValue', 'blankValue', 'arrayValue', 'falseValue'], required_uploads: ['Passport'] };
  await renderStep(step, [{ step_id: 'matrix', status: 'in_progress', data: { nullValue: null, emptyValue: '', blankValue: '   ', arrayValue: [], falseValue: false } }]);
  fireEvent.click(screen.getAllByTestId('complete-step-btn')[0]);
  expect((await screen.findAllByTestId('validation-errors'))[0].querySelectorAll('li')).toHaveLength(7);
});

test('renders history, completed progress, restored form data and impersonation', async () => {
  mockAuth = { ...mockAuth, impersonating: true };
  stepsAPI.getBootstrap.mockResolvedValueOnce(bootstrap({
    progress: [{ step_id: 'survey', status: 'completed', data: { select: 'A', checks: ['C'] } }],
    history: [{ action: 'completed', step_title: 'Survey', step_order: 1, timestamp: '2026-01-01' }, { action: 'in_progress', step_title: 'Next', step_order: 2, timestamp: '2026-01-02' }, { action: 'edited', step_title: 'Edit', step_order: 3, timestamp: '2026-01-03' }],
  }));
  render(<UserDashboard />);
  await screen.findAllByText('Survey');
  fireEvent.click(screen.getByTestId('timeline-btn'));
  expect(screen.getByTestId('timeline-entry-2')).toHaveTextContent('edited');
  fireEvent.click(screen.getByTestId('stop-impersonation-btn'));
  expect(mockAuth.stopImpersonation).toHaveBeenCalled(); expect(mockNavigate).toHaveBeenCalledWith('/admin');
});

test('recovers from bootstrap and notification errors', async () => {
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  stepsAPI.getBootstrap.mockRejectedValueOnce(new Error('load'));
  render(<UserDashboard />);
  await waitFor(() => expect(error).toHaveBeenCalled());
  expect(screen.queryByText('loading')).not.toBeInTheDocument();
  error.mockRestore();
});

test.each([null, {}])('normalizes an empty bootstrap payload %#', async (payload) => {
  stepsAPI.getBootstrap.mockResolvedValueOnce({ data: payload });
  render(<UserDashboard />);
  await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument());
  expect(screen.queryByTestId('step-card-0')).not.toBeInTheDocument();
});

async function renderStep(step, progress = [], allStepData = [{ order: 1, status: 'pending', data: { fachrichtung_gewuenscht: 'Cardiology', anerkennungsverfahren_bundesland: 'Berlin', source: 'mapped' } }]) {
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [step], progress, all_step_data: allStepData, estimated_completion: null }));
  render(<UserDashboard />);
  await screen.findAllByText(step.title);
}

test('handles primary preview and completes a regular decision', async () => {
  const step = { id: 'decision', order: 1, title: 'Decision', step_type: 'decision', duration_value: 1, content: '<p>Choose</p>', fields: [{ field_type: 'decision', options: [
    { value: 'fast', label: 'Fast', primary: true, info_title: 'Fast info', info_body: '<p>Info</p>' },
    { value: 'normal', label: 'Normal' },
  ] }] };
  await renderStep(step);
  fireEvent.click(screen.getByTestId('decision-option-0'));
  expect(screen.getAllByTestId('decision-step-info')).not.toHaveLength(0);
  fireEvent.click(screen.getAllByTestId('fastlane-back-btn')[0]);
  fireEvent.click(screen.getByTestId('decision-option-1'));
  await waitFor(() => expect(stepsAPI.updateProgress).toHaveBeenCalledWith('decision', 'completed', { decision: 'normal' }));
});

test('selects, filters, submits and skips a single partner', async () => {
  const step = { id: 'partner', order: 2, title: 'Partner', step_type: 'partner_selection', duration_value: 1, skippable: true, filter_tag: 'language' };
  partnersAPI.getAll.mockResolvedValue({ data: [
    { id: 'p1', name: 'Alpha', category: 'Cardiology', tags: ['Cardiology', 'Berlin'], logo_url: '/logo', description: 'A' },
    { id: 'p2', name: 'Beta', tags: ['Bayern'], description: 'B' },
  ] });
  await renderStep(step);
  await screen.findAllByTestId('partner-select-p1');
  fireEvent.click(screen.getAllByTestId('skip-step-btn')[0]);
  await waitFor(() => expect(stepsAPI.updateProgress).toHaveBeenCalledWith('partner', 'completed', { skipped: true }));
  stepsAPI.updateProgress.mockClear();
  fireEvent.click(screen.getAllByTestId('partner-select-p1')[0]);
  fireEvent.click(screen.getAllByTestId('confirm-partner-btn')[0]);
  await waitFor(() => expect(partnersAPI.submit).toHaveBeenCalled());
  fireEvent.click(screen.getAllByTestId('mock-select')[0]);
});

test('toggles and submits multiple partners', async () => {
  const step = { id: 'multi-partner', order: 2, title: 'Partners', step_type: 'partner_multiselection', duration_value: 1, skippable: true };
  partnersAPI.getAll.mockResolvedValue({ data: [{ id: 'p1', name: 'Alpha', category: 'Cardiology', tags: ['Berlin'], description: 'A' }, { id: 'p2', name: 'Beta', category: 'Other', tags: ['Bayern'], description: 'B' }] });
  await renderStep(step);
  await screen.findAllByTestId('partner-multiselect-p1');
  fireEvent.click(screen.getAllByTestId('partner-multiselect-p1')[0]);
  fireEvent.click(screen.getAllByTestId('partner-multiselect-p2')[0]);
  fireEvent.click(screen.getAllByTestId('partner-multiselect-p2')[0]);
  fireEvent.click(screen.getAllByTestId('confirm-multipartner-btn')[0]);
  await waitFor(() => expect(partnersAPI.submitMulti).toHaveBeenCalledWith(['p1'], expect.any(Object)));
  fireEvent.click(screen.getAllByTestId('mock-select')[0]);
});

test('renders a workflow milestone document', async () => {
  const workflow = { id: 'work', order: 1, title: 'Workflow', step_type: 'milestone', duration_value: 1, document_workflow: true, documents: [{ file_id: 'f', document_type: 'Proof', filename: 'proof.pdf' }] };
  const first = renderStep(workflow);
  await first;
  expect(screen.getAllByTestId('workflow-document-0').find(element => element.tagName === 'A')).toHaveAttribute('href', '/files/f');
});

test('renders pending and completed milestone states', async () => {
  const step = { id: 'mile', order: 1, title: 'Milestone', step_type: 'milestone', duration_value: 1, pending_message: 'Please wait', complete_message: 'Finished' };
  await renderStep(step);
  expect(screen.getAllByText('Please wait')).not.toHaveLength(0);
});

test('renders and completes a mapped display step', async () => {
  const step = { id: 'display', order: 1, title: 'Display', step_type: 'display', duration_value: 1, content: '<p>Display body</p>', action_label: 'Continue', link_url: 'https://example.test', link_label: 'External', field_mappings: [{ source_step_order: 1, source_field: 'source', target_field: 'Copied' }] };
  await renderStep(step);
  expect(screen.getAllByTestId('step-external-link')[0]).toHaveAttribute('href', 'https://example.test');
  expect(screen.getAllByText('mapped')[0]).toBeInTheDocument();
  fireEvent.click(screen.getAllByTestId('display-action-btn')[0]);
  await waitFor(() => expect(stepsAPI.updateProgress).toHaveBeenCalledWith('display', 'completed', expect.any(Object)));
});

test('renders read-only and blocked steps', async () => {
  const readonly = { id: 'read', order: 1, title: 'Readonly', step_type: 'form', duration_value: 1, read_only: true };
  await renderStep(readonly, [{ step_id: 'read', status: 'in_progress', data: { value: { nested: true }, _step_id: 'read' } }]);
  expect(screen.getAllByTestId('step-read-only')[0]).toHaveTextContent('nested');
});

test('renders a completed milestone', async () => {
  const milestone = { id: 'mile', order: 1, title: 'Complete Milestone', step_type: 'milestone', duration_value: 1, complete_message: 'Finished' };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [milestone], progress: [{ step_id: 'mile', status: 'completed', data: {} }], all_step_data: [] }));
  render(<UserDashboard />);
  await screen.findAllByText('Finished');
  expect(screen.queryByTestId('milestone-next-btn')).not.toBeInTheDocument();
});

test('supports multi-file and multiupload editing plus upload failures', async () => {
  const step = { id: 'uploads', order: 1, title: 'Uploads', step_type: 'form', duration_value: 1, fields: [
    { name: 'files', label: 'Files', field_type: 'file', multiple: true },
    { name: 'documents', label: 'Documents', field_type: 'multiupload', options: ['Passport'] },
  ] };
  await renderStep(step);
  const a = new File(['a'], 'a.pdf'); const b = new File(['b'], 'b.pdf');
  fireEvent.change(screen.getAllByTestId('form-field-files')[0], { target: { files: [a, b] } });
  await waitFor(() => expect(filesAPI.upload).toHaveBeenCalledTimes(2));
  fireEvent.click(screen.getAllByTestId('add-multiupload-documents')[0]);
  const entry = await screen.findAllByTestId('multiupload-entry-0');
  const entryFile = entry[0].querySelector('input[type="file"]');
  fireEvent.change(entryFile, { target: { files: [a] } });
  await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Datei hochgeladen'));
  const entryButtons = entry[0].querySelectorAll('button');
  fireEvent.click(entryButtons[0]);
  fireEvent.click(entryButtons[entryButtons.length - 1]);
  fireEvent.click(screen.getAllByTestId('save-progress-btn')[0]);
  await waitFor(() => expect(stepsAPI.updateProgress).toHaveBeenCalledWith('uploads', 'in_progress', expect.any(Object)));
  filesAPI.upload.mockRejectedValueOnce(new Error('upload'));
  fireEvent.change(screen.getAllByTestId('form-field-files')[0], { target: { files: [a, b] } });
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Fehler beim Hochladen'));
});

test('reports a multiupload entry failure and enables required uploaded documents', async () => {
  const step = { id: 'required-upload', order: 1, title: 'Required Upload', step_type: 'form', duration_value: 1, required_uploads: ['Passport'], fields: [{ name: 'documents', label: 'Documents', field_type: 'multiupload', required: true, options: ['Passport'] }] };
  await renderStep(step, [{ step_id: 'required-upload', status: 'in_progress', data: { documents: [{ file_id: 'old', filename: 'old.pdf', document_type: 'Passport' }] } }]);
  expect(screen.getAllByTestId('complete-step-btn')[0]).not.toBeDisabled();
  fireEvent.click(screen.getAllByTestId('complete-step-btn')[0]);
  await waitFor(() => expect(stepsAPI.updateProgress).toHaveBeenCalledWith('required-upload', 'completed', expect.any(Object)));
  await waitFor(() => expect(stepsAPI.getBootstrap).toHaveBeenCalledTimes(2));
  fireEvent.click(screen.getAllByTestId('add-multiupload-documents')[0]);
  const entries = await screen.findAllByTestId('multiupload-entry-1');
  filesAPI.upload.mockRejectedValueOnce(new Error('entry'));
  fireEvent.change(entries[0].querySelector('input[type="file"]'), { target: { files: [new File(['x'], 'x.pdf')] } });
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Fehler beim Hochladen'));
});

test('reports progress, skip, partner and notification API failures', async () => {
  const step = { id: 'failure', order: 1, title: 'Failure Form', step_type: 'form', duration_value: 1, fields: [], skippable: true };
  stepsAPI.updateProgress.mockRejectedValue(new Error('save'));
  await renderStep(step);
  fireEvent.click(screen.getAllByTestId('save-progress-btn')[0]);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
  fireEvent.click(screen.getByTestId('settings-btn'));
  notificationAPI.updatePreferences.mockRejectedValueOnce(new Error('prefs'));
  fireEvent.click(screen.getByTestId('save-notif-prefs-btn'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Fehler'));
});

test('validates an unknown required field and reports a single upload failure', async () => {
  const step = { id: 'validation', order: 1, title: 'Validation', step_type: 'form', duration_value: 1, required_fields: ['missing'], fields: [{ name: 'file', label: 'File', field_type: 'file' }] };
  await renderStep(step);
  fireEvent.click(screen.getAllByTestId('complete-step-btn')[0]);
  expect((await screen.findAllByTestId('validation-errors'))[0]).toHaveTextContent('missing ist ein Pflichtfeld');
  filesAPI.upload.mockRejectedValueOnce(new Error('single'));
  fireEvent.change(screen.getAllByTestId('form-field-file')[0], { target: { files: [new File(['x'], 'x.pdf')] } });
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Fehler beim Hochladen'));
});

test('reports skip and partner submission failures', async () => {
  const step = { id: 'partner-fail', order: 1, title: 'Partner Failure', step_type: 'partner_selection', duration_value: 1, skippable: true };
  partnersAPI.getAll.mockResolvedValue({ data: [{ id: 'p', name: 'Partner', tags: [] }] });
  await renderStep(step);
  await screen.findAllByTestId('partner-select-p');
  stepsAPI.updateProgress.mockRejectedValueOnce(new Error('skip'));
  fireEvent.click(screen.getAllByTestId('skip-step-btn')[0]);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
  partnersAPI.submit.mockRejectedValueOnce(new Error('partner'));
  fireEvent.click(screen.getAllByTestId('partner-select-p')[0]);
  fireEvent.click(screen.getAllByTestId('confirm-partner-btn')[0]);
  await waitFor(() => expect(partnersAPI.submit).toHaveBeenCalled());
});

test('reports multi-partner submission failures', async () => {
  const step = { id: 'multi-fail', order: 1, title: 'Multi Failure', step_type: 'partner_multiselection', duration_value: 1 };
  partnersAPI.getAll.mockResolvedValue({ data: [{ id: 'p', name: 'Partner', tags: [] }] });
  await renderStep(step);
  await screen.findAllByTestId('partner-multiselect-p');
  partnersAPI.submitMulti.mockRejectedValueOnce(new Error('multi'));
  fireEvent.click(screen.getAllByTestId('partner-multiselect-p')[0]);
  fireEvent.click(screen.getAllByTestId('confirm-multipartner-btn')[0]);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
});

test('restores saved single and multiple partner selections on navigation', async () => {
  const intro = { id: 'intro', order: 1, title: 'Intro', step_type: 'display', duration_value: 1 };
  const single = { id: 'single', order: 2, title: 'Single', step_type: 'partner_selection', duration_value: 1 };
  const multi = { id: 'multi', order: 3, title: 'Multi', step_type: 'partner_multiselection', duration_value: 1 };
  const partnerList = [{ id: 'p1', name: 'Alpha', tags: [] }, { id: 'p2', name: 'Beta', tags: [] }];
  partnersAPI.getAll.mockResolvedValue({ data: partnerList });
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({
    steps: [intro, single, multi],
    progress: [{ step_id: 'intro', status: 'completed', data: {} }, { step_id: 'single', status: 'completed', data: { selected_partner_id: 'p1' } }, { step_id: 'multi', status: 'completed', data: { selected_partner_ids: ['p2'] } }],
    all_step_data: [],
  }));
  render(<UserDashboard />);
  await screen.findAllByText('Intro');
  fireEvent.click(screen.getByTestId('step-card-1'));
  await waitFor(() => expect(partnersAPI.getAll).toHaveBeenCalled());
  fireEvent.click(screen.getByTestId('step-card-2'));
  await waitFor(() => expect(screen.getAllByTestId('partner-multiselect-p2')).not.toHaveLength(0));
});

test('tolerates partner list failures during initial load and saved-selection navigation', async () => {
  const intro = { id: 'intro-fail', order: 1, title: 'Intro Failure', step_type: 'display', duration_value: 1 };
  const single = { id: 'single-fail', order: 2, title: 'Single Failure', step_type: 'partner_selection', duration_value: 1 };
  const multi = { id: 'multi-fail-nav', order: 3, title: 'Multi Nav Failure', step_type: 'partner_multiselection', duration_value: 1 };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [intro, single, multi], progress: [
    { step_id: 'intro-fail', status: 'completed', data: {} },
    { step_id: 'single-fail', status: 'completed', data: { selected_partner_id: 'p' } },
    { step_id: 'multi-fail-nav', status: 'completed', data: { selected_partner_ids: ['p'] } },
  ], all_step_data: [] }));
  partnersAPI.getAll.mockRejectedValue(new Error('partners'));
  render(<UserDashboard />);
  await screen.findAllByText('Intro Failure');
  fireEvent.click(screen.getByTestId('step-card-1'));
  fireEvent.click(screen.getByTestId('step-card-2'));
  await waitFor(() => expect(partnersAPI.getAll).toHaveBeenCalled());
});

test('handles absent and unresolved saved partner selections', async () => {
  const partnerStep = { id: 'saved-single', order: 1, title: 'Saved Single', step_type: 'partner_selection', duration_value: 1, filter_tag: 'tag' };
  partnersAPI.getAll.mockResolvedValue({ data: [{ id: 'actual', name: 'Actual', tags: [] }] });
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [partnerStep], progress: [
    { step_id: 'saved-single', status: 'in_progress', data: { selected_partner_id: 'missing' } },
  ] }));
  render(<UserDashboard />);
  await screen.findAllByText('Saved Single');
  fireEvent.click(screen.getByTestId('step-card-0'));
  const confirm = await screen.findAllByTestId('confirm-partner-btn');
  expect(confirm[0]).toBeDisabled();
});

test('handles saved partner progress without a selection key', async () => {
  const partnerStep = { id: 'saved-empty', order: 1, title: 'Saved Empty', step_type: 'partner_selection', duration_value: 1 };
  partnersAPI.getAll.mockResolvedValue({ data: [] });
  await renderStep(partnerStep, [{ step_id: 'saved-empty', status: 'in_progress', data: { note: 'x' } }]);
  expect(screen.getAllByText('Keine Partner verfuegbar')).not.toHaveLength(0);
});

test('renders an unknown step type', async () => {
  await renderStep({ id: 'unknown', order: 1, title: 'Unknown', step_type: 'custom', duration_value: 0 });
  expect(screen.getAllByText('Unbekannter Schritttyp')).toHaveLength(2);
});

test('renders a blocked current step and invalid image safely', async () => {
  const blocked = { id: 'blocked', order: 1, title: 'Blocked', step_type: 'form', duration_value: 1, fields: [{ name: 'bad', field_type: 'image', image_url: 'javascript:bad' }], conditions: [{ source_step_order: 1, field: 'flag', operator: 'equals', value: 'yes', action: 'block', message: 'Blocked message' }] };
  await renderStep(blocked, [], [{ order: 1, status: 'pending', data: { flag: 'yes' } }]);
  expect(screen.getAllByText('Blocked message')).not.toHaveLength(0);
});

test('drops an unsafe image and covers empty progress calculations and empty file selection', async () => {
  const step = { id: 'empty', order: 1, title: 'Empty', step_type: 'form', duration_value: 0, fields: [{ name: 'bad', field_type: 'image', image_url: 'javascript:bad' }, { name: 'file', field_type: 'file' }] };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [step], estimated_completion: '2026-01-01', all_step_data: [] }));
  render(<UserDashboard />);
  await screen.findAllByText('Empty');
  expect(screen.queryByTestId('content-field-bad')).not.toBeInTheDocument();
  fireEvent.change(screen.getAllByTestId('form-field-file')[0], { target: { files: [] } });
});

test('calculates header progress for an empty journey', async () => {
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [], progress: [], all_step_data: [], estimated_completion: '2026-01-01' }));
  render(<UserDashboard />);
  await waitFor(() => expect(screen.getByTestId('header-completion-pct')).toHaveTextContent('0%'));
});

test('uses the default display action and supports previous/mobile navigation', async () => {
  const first = { id: 'first', order: 1, title: 'First', step_type: 'display', duration_value: 1 };
  const second = { id: 'second', order: 2, title: 'Second', step_type: 'display', duration_value: 1, pending_message: 'Pending content' };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [first, second], progress: [{ step_id: 'first', status: 'completed', data: { regular: true } }], all_step_data: [] }));
  render(<UserDashboard />);
  await screen.findAllByText('Second');
  fireEvent.click(screen.getAllByTestId('display-next-btn')[0]);
  await waitFor(() => expect(stepsAPI.updateProgress).toHaveBeenCalledWith('second', 'completed', expect.any(Object)));
  fireEvent.click(screen.getByTestId('prev-step-btn'));
  fireEvent.click(screen.getByTestId('step-nav-0'));
});

test('navigates back to a completed milestone and advances again', async () => {
  const milestone = { id: 'mile-nav', order: 1, title: 'Milestone Nav', step_type: 'milestone', duration_value: 1 };
  const next = { id: 'after', order: 2, title: 'After', step_type: 'display', duration_value: 1 };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [milestone, next], progress: [{ step_id: 'mile-nav', status: 'completed', data: {} }], all_step_data: [] }));
  render(<UserDashboard />);
  await screen.findAllByText('After');
  fireEvent.click(screen.getByTestId('step-card-0'));
  fireEvent.click(screen.getAllByTestId('milestone-next-btn')[0]);
  expect(screen.getAllByText('After')).not.toHaveLength(0);
});

test('advances again from a completed document workflow milestone', async () => {
  const milestone = {
    id: 'document-mile-nav', order: 1, title: 'Document Milestone Nav',
    step_type: 'milestone', duration_value: 1, document_workflow: true,
    documents: [{ file_id: 'file-1', document_type: 'Antrag', filename: 'antrag.pdf' }],
  };
  const next = { id: 'selection-after', order: 2, title: 'Selection After', step_type: 'decision', duration_value: 1, fields: [{ options: [] }] };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({
    steps: [milestone, next],
    progress: [{ step_id: 'document-mile-nav', status: 'completed', data: {} }],
    all_step_data: [],
  }));
  render(<UserDashboard />);
  await screen.findAllByText('Selection After');
  fireEvent.click(screen.getByTestId('step-card-0'));
  expect(screen.getAllByTestId('workflow-document-0')[0]).toHaveTextContent('antrag.pdf');
  fireEvent.click(screen.getAllByTestId('milestone-next-btn')[0]);
  expect(screen.getAllByText('Selection After')).not.toHaveLength(0);
});

test('shows forward navigation on completed read-only uploads but hides it for a blocked next step', async () => {
  const upload = { id: 'locked-upload', order: 1, title: 'Locked Upload', step_type: 'form', duration_value: 1, read_only: true };
  const next = { id: 'next-choice', order: 2, title: 'Next Choice', step_type: 'decision', duration_value: 1, fields: [{ options: [] }] };
  const completed = [{ step_id: 'locked-upload', status: 'completed', data: { documents: [{ file_id: 'f' }] } }];
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [upload, next], progress: completed, all_step_data: [
    { step_id: 'locked-upload', order: 1, status: 'completed', data: { documents: [{ file_id: 'f' }] } },
    { step_id: 'next-choice', order: 2, status: 'pending', data: {} },
  ] }));
  const view = render(<UserDashboard />);
  await screen.findAllByText('Next Choice');
  fireEvent.click(screen.getByTestId('step-card-0'));
  fireEvent.click(screen.getAllByTestId('step-next-btn')[0]);
  expect(screen.getAllByText('Next Choice')).not.toHaveLength(0);

  view.unmount();
  const blockedNext = { ...next, conditions: [{ action: 'block', source_step_order: 1, operator: 'status_is', value: 'completed' }] };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [upload, blockedNext], progress: completed, all_step_data: [
    { step_id: 'locked-upload', order: 1, status: 'completed', data: {} },
    { step_id: 'next-choice', order: 2, status: 'pending', data: {} },
  ] }));
  render(<UserDashboard />);
  await screen.findAllByText('Locked Upload');
  expect(screen.queryByTestId('step-next-btn')).not.toBeInTheDocument();
});

test('renders decision fallbacks and an already active choice', async () => {
  const step = { id: 'decision-fallback', order: 1, title: 'Decision Fallback', step_type: 'decision', duration_value: 1, pending_message: '<p>Pending choice</p>', fields: [{ options: [
    { value: 'primary', label: 'Primary', primary: true }, { value: 'chosen', label: 'Chosen' },
  ] }] };
  await renderStep(step, [{ step_id: 'decision-fallback', status: 'in_progress', data: { decision: 'chosen' } }]);
  fireEvent.click(screen.getByTestId('decision-option-0'));
  expect(screen.getAllByTestId('decision-step-info')[0]).toHaveTextContent('Primary');
  fireEvent.click(screen.getAllByTestId('fastlane-back-btn')[0]);
  expect(screen.getByTestId('decision-option-1').className).toContain('shadow-md');
});

test('renders a decision without fields or options', async () => {
  await renderStep({ id: 'empty-decision', order: 1, title: 'Empty Decision', step_type: 'decision', duration_value: 1 });
  expect(screen.getAllByTestId('decision-step')).toHaveLength(2);
});

test('renders disabled UI feature flags independently', async () => {
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ settings: { ui_show_journey_indicator: false, ui_show_eta_header: false, ui_show_progress_percentage: false } }));
  render(<UserDashboard />);
  await screen.findAllByText('Survey');
  expect(screen.queryByTestId('journey')).not.toBeInTheDocument();
  expect(screen.queryByTestId('header-progress-wrapper')).not.toBeInTheDocument();
});

test('renders default milestone and display texts, mapping objects and missing mappings', async () => {
  const display = { id: 'display-defaults', order: 1, title: 'Display Defaults', step_type: 'display', duration_value: 1, pending_message: 'Pending only', link_url: '/external', field_mappings: [
    { source_step_order: 1, source_field: 'object', target_field: 'Object' }, { source_step_order: 1, source_field: 'missing', target_field: 'Missing' },
  ] };
  await renderStep(display, [], [{ order: 1, status: 'pending', data: { object: { value: 1 } } }]);
  expect(screen.getAllByText('Pending only')).not.toHaveLength(0);
  expect(screen.getAllByText('{"value":1}')).not.toHaveLength(0);
  expect(screen.getAllByTestId('step-external-link')[0]).toHaveTextContent('/external');
});

test('uses default pending and completed milestone messages', async () => {
  const pending = { id: 'pending-default', order: 1, title: 'Pending Default', step_type: 'milestone', duration_value: 1 };
  await renderStep(pending);
  expect(screen.getAllByText('dash_waiting')).not.toHaveLength(0);
});

test('renders remaining form presentation and fallback variants', async () => {
  const step = { id: 'variants', order: 1, title: 'Variants', step_type: 'form', duration_value: 1, fields: [
    { id: 'select-id', name: 'select', field_type: 'select', label: 'Select required', required: true, options: [{ value: 'x', label: 'X' }] },
    { name: 'empty-image', field_type: 'image' },
    { name: 'radio', field_type: 'radio', label: 'Radio required', required: true, options: [{ value: 'x', label: 'X' }] },
    { name: 'multi', field_type: 'multiselect', label: 'Multi required', required: true, options: [{ value: 'x', label: 'X' }] },
    { name: 'check', field_type: 'checkbox', label: 'Check required', required: true },
    { name: 'area', field_type: 'textarea', label: 'Area required', required: true },
    { name: 'upload', field_type: 'upload', label: 'Upload required', required: true },
    { field_type: 'text', label: 'Unnamed required', required: true, validation_pattern: '[A-Z]+', help_text: 'Text help' },
  ] };
  await renderStep(step);
  fireEvent.click(screen.getAllByTestId('complete-step-btn')[0]);
  expect((await screen.findAllByTestId('validation-errors'))[0]).toBeInTheDocument();
  fireEvent.click(screen.getAllByLabelText('X')[0]);
  fireEvent.click(screen.getAllByLabelText('X')[1]);
  fireEvent.click(screen.getAllByTestId('form-field-check')[0]);
  fireEvent.change(screen.getAllByTestId('form-field-area')[0], { target: { value: 'value' } });
  fireEvent.change(screen.getAllByTestId('form-field-upload')[0], { target: { files: [new File(['x'], 'unnamed.pdf')] } });
  await waitFor(() => expect(filesAPI.upload).toHaveBeenCalled());
});

test('covers partner list fallbacks, recommendation labels, filtering and logos', async () => {
  mockLanguage = { ...mockLanguage, t: () => '' };
  const single = { id: 'partner-variants', order: 1, title: 'Partner Variants', step_type: 'partner_selection', duration_value: 1 };
  partnersAPI.getAll.mockResolvedValue({ data: [
    { id: 'category', name: 'Category', category: 'Cardiology', tags: undefined },
    { id: 'tagged', name: 'Tagged', tags: ['Berlin', 'Hamburg'], logo_url: '/logo' },
  ] });
  await renderStep(single, [], [{ order: 1, status: 'pending', data: { fachrichtung_gewuenscht: 'Cardiology' } }]);
  await screen.findAllByTestId('recommended-badge-category');
  fireEvent.click(screen.getAllByTestId('mock-select')[0]);
  await waitFor(() => expect(screen.getAllByText('Keine Partner verfuegbar')).not.toHaveLength(0));
});

test('covers multi-partner category filtering and recommendation fallbacks', async () => {
  mockLanguage = { ...mockLanguage, t: () => '' };
  const multi = { id: 'multi-variants', order: 1, title: 'Multi Variants', step_type: 'partner_multiselection', duration_value: 1 };
  partnersAPI.getAll.mockResolvedValue({ data: [
    { id: 'category', name: 'Category', category: 'Cardiology', tags: undefined, logo_url: '/logo' },
    { id: 'tagged', name: 'Tagged', tags: ['Berlin', 'Hamburg'] },
  ] });
  await renderStep(multi, [], [{ order: 1, status: 'pending', data: { fachrichtung_gewuenscht: 'Cardiology' } }]);
  await screen.findAllByTestId('recommended-badge-category');
  fireEvent.click(screen.getAllByTestId('mock-select')[0]);
  await waitFor(() => expect(screen.getAllByText('Keine Partner verfuegbar')).not.toHaveLength(0));
});

test('handles document workflow without a document list and empty translated header labels', async () => {
  mockLanguage = { ...mockLanguage, t: () => '' };
  const step = { id: 'empty-workflow', order: 1, title: 'Empty Workflow', step_type: 'milestone', duration_value: 1, document_workflow: true };
  stepsAPI.getBootstrap.mockResolvedValue(bootstrap({ steps: [step], estimated_completion: '2026-01-01' }));
  render(<UserDashboard />);
  await screen.findAllByText('Empty Workflow');
  expect(screen.getAllByText('Dieser Schritt wird von Ihrem Partner bearbeitet.')).not.toHaveLength(0);
  expect(screen.getByTestId('header-completion-pct-wrapper')).toHaveAttribute('title', 'Fortschritt');
});

test('validates missing required document types with absent multiupload data', async () => {
  const step = { id: 'missing-upload', order: 1, title: 'Missing Upload', step_type: 'form', duration_value: 1,
    required_uploads: ['Passport'], fields: [{ name: 'documents', field_type: 'multiupload', label: 'Documents', help_text: 'Upload help' }] };
  await renderStep(step);
  const complete = screen.getAllByTestId('complete-step-btn')[0];
  expect(complete).not.toBeDisabled();
  fireEvent.click(complete);
  expect((await screen.findAllByTestId('validation-errors'))[0]).toHaveTextContent('Dokument erforderlich: Passport');
});

test('disables completion while a required multiupload has no file', async () => {
  const step = { id: 'disabled-upload', order: 1, title: 'Disabled Upload', step_type: 'form', duration_value: 1,
    fields: [{ name: 'documents', field_type: 'multiupload', label: 'Documents', required: true }] };
  await renderStep(step);
  const complete = screen.getAllByTestId('complete-step-btn')[0];
  expect(complete).toBeDisabled();
  expect(complete).toHaveAttribute('title', 'Bitte laden Sie mindestens ein Dokument hoch');
  expect(complete).toHaveTextContent('Upload erforderlich');
});

test('renders saved uploads without filenames and read-only scalar or absent data', async () => {
  const upload = { id: 'saved-upload', order: 1, title: 'Saved Upload', step_type: 'form', duration_value: 1,
    fields: [{ name: 'documents', field_type: 'multiupload', label: 'Documents' }] };
  await renderStep(upload, [{ step_id: 'saved-upload', status: 'in_progress', data: { documents: [{ file_id: 'file' }] } }]);
  expect(screen.getAllByText('Hochgeladen')).not.toHaveLength(0);
  const scalar = { id: 'scalar-read', order: 1, title: 'Scalar Read', step_type: 'form', duration_value: 1, read_only: true };
  await renderStep(scalar, [{ step_id: 'scalar-read', status: 'in_progress', data: { answer: 'yes' } }]);
  expect(screen.getAllByText('yes')).not.toHaveLength(0);
  const absent = { id: 'absent-read', order: 1, title: 'Absent Read', step_type: 'form', duration_value: 1, read_only: true };
  await renderStep(absent);
  expect(screen.getAllByTestId('step-read-only')).not.toHaveLength(0);
});
