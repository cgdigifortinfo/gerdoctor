import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { BasicPanel } from './BasicPanel';
import { MappingsPanel } from './MappingsPanel';
import { NotificationsPanel } from './NotificationsPanel';
import { RequirementsPanel } from './RequirementsPanel';
import { TranslationsPanel } from './TranslationsPanel';

let mockCapturedSelects = [], mockCapturedSelectItems = [], mockCapturedSearchables = [], mockCapturedMultis = [], mockCapturedHelp = [];
jest.mock('../../../components/ui/select', () => ({ Select: (props) => { mockCapturedSelects.push(props); return <div>{props.children}<button data-testid="select-value" onClick={() => props.onValueChange('changed')}>change select</button></div>; }, SelectContent: ({ children }) => <>{children}</>, SelectItem: (props) => { mockCapturedSelectItems.push(props); return <span>{props.children}</span>; }, SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => null }));
jest.mock('../../../components/ui/switch', () => ({ Switch: ({ checked, onCheckedChange }) => <button data-testid="switch" onClick={() => onCheckedChange(!checked)}>{String(checked)}</button> }));
jest.mock('../../../components/admin/EntityPickers', () => ({
  SearchableSelect: (props) => { mockCapturedSearchables.push(props); return <button data-testid={props.testId} onClick={() => props.onChange('changed')}>select</button>; },
  SearchableMultiSelect: (props) => { mockCapturedMultis.push(props); return <button data-testid={props.testId} onClick={() => props.onChange(['field'])}>{props.placeholder}</button>; },
}));
jest.mock('../../../components/ui/help-tooltip', () => ({ HelpLabel: (props) => { mockCapturedHelp.push(props.help); return <>{props.children}</>; } }));
jest.mock('../../../components/admin/SurveyFormBuilder', () => ({ CONTENT_FIELD_TYPES: new Set(['heading']) }));
jest.mock('@phosphor-icons/react', () => ({ Plus: () => null, Trash: () => null }));

const t = key => key;
const basic = { survey_id: '', title: '', description: '', order: 1, step_type: 'form', is_active: true, skippable: false, skip_label: '', duration_value: 0, duration_unit: 'days' };

test('basic panel exposes every field, select and switch command', () => {
  mockCapturedSelects = []; mockCapturedSelectItems = []; mockCapturedSearchables = []; mockCapturedHelp = [];
  const setFormData = jest.fn(); const survey = jest.fn();
  const { rerender } = render(<BasicPanel surveyOptions={[]} formData={basic} activeSurveyId="active" handleStepSurveyChange={survey} t={t} setFormData={setFormData} />);
  fireEvent.click(screen.getByTestId('step-survey-select'));
  fireEvent.change(screen.getByTestId('step-title-input'), { target: { value: 'Title' } });
  fireEvent.change(screen.getByTestId('step-description-input'), { target: { value: 'Description' } });
  const numbers = screen.getAllByRole('spinbutton'); fireEvent.change(numbers[0], { target: { value: '3' } }); fireEvent.change(numbers[1], { target: { value: '' } }); fireEvent.change(numbers[1], { target: { value: '5' } });
  screen.getAllByTestId('select-value').forEach(button => fireEvent.click(button));
  screen.getAllByTestId('switch').forEach(button => fireEvent.click(button));
  expect(survey).toHaveBeenCalledWith('changed');
  expect(setFormData.mock.calls.map(([value]) => value)).toEqual([
    { ...basic, title: 'Title' },
    { ...basic, description: 'Description' },
    { ...basic, order: 3 },
    { ...basic, duration_value: 0 },
    { ...basic, duration_value: 5 },
    { ...basic, step_type: 'changed' },
    { ...basic, duration_unit: 'changed' },
    { ...basic, is_active: false },
    { ...basic, skippable: true },
  ]);
  rerender(<BasicPanel surveyOptions={[]} formData={{ ...basic, survey_id: 'own', skippable: true }} activeSurveyId="active" handleStepSurveyChange={survey} t={t} setFormData={setFormData} />);
  fireEvent.change(screen.getByPlaceholderText('Vorerst überspringen'), { target: { value: 'Skip' } });
  expect(setFormData).toHaveBeenCalledWith(expect.objectContaining({ skip_label: 'Skip' }));
  expect(screen.getByText('step_skip_label')).toBeInTheDocument();
  expect(mockCapturedSearchables[0]).toMatchObject({ options: [], value: 'active', placeholder: 'Survey wählen', searchPlaceholder: 'Survey nach Name oder URL suchen …', testId: 'step-survey-select' });
  expect(mockCapturedSearchables.at(-1).value).toBe('own');
  expect(mockCapturedSelects.slice(0, 2).map(({ value }) => value)).toEqual(['form', 'days']);
  expect(mockCapturedSelectItems.slice(0, 10).map(({ value, children }) => [value, children])).toEqual([
    ['form', 'step_type_form'], ['decision', 'Entscheidung (2 Buttons)'], ['partner_selection', 'step_type_partner'], ['partner_multiselection', 'step_type_partner_multi'], ['milestone', 'step_type_milestone'], ['display', 'step_type_display'],
    ['days', 'step_days'], ['weeks', 'step_weeks'], ['months', 'step_months'], ['years', 'step_years'],
  ]);
  expect(mockCapturedHelp.slice(0, 8)).toEqual([
    'Ordnet den Step einem Survey zu. Reihenfolge, Progress und Conditions gelten nur innerhalb dieses Surveys.',
    'Sichtbarer Name in Journey, Navigation, Adminansicht und E-Mails.',
    'Erklärt Nutzern Ziel und Inhalt des Steps. Die Beschreibung kann auch in Benachrichtigungen verwendet werden.',
    'Position innerhalb des aktiven Surveys. Conditions referenzieren Steps über diese Nummer.',
    'Formular sammelt Daten; Entscheidung zeigt Auswahlkarten; Partner-Typen vermitteln Partner; Meilenstein bildet Status ab; Anzeige zeigt Information.',
    'Inaktive Steps werden nicht ausgeliefert und zählen nicht zum Fortschritt.',
    'Erlaubt Nutzern, den Step ohne reguläre Eingaben als übersprungen abzuschließen.',
    'Schätzwert für die ETA-Berechnung. Freischaltungen werden ausschließlich über Conditions gesteuert.',
  ]);
  ['step_title', 'step_description', 'step_order', 'step_type', 'step_active', 'step_skippable', 'step_duration', 'step_duration_desc', 'step_duration_value', 'step_duration_unit'].forEach(label => expect(screen.getAllByText(label).length).toBeGreaterThan(0));
});

test('requirements panel handles fallback options, required flags and uploads', () => {
  mockCapturedMultis = [];
  const setFormData = jest.fn();
  let formData = { fields: [], required_fields: ['missing'], required_uploads: [] };
  const { rerender } = render(<RequirementsPanel formData={formData} currentFieldOptions={[]} setFormData={setFormData} documentTypeOptions={[]} />);
  expect(screen.getByTestId('step-required-fields')).toHaveTextContent('Noch keine Formularfelder definiert');
  expect(mockCapturedMultis.find(({ testId }) => testId === 'step-required-fields')).toMatchObject({ options: [{ value: 'missing', label: 'Bestehender Wert: missing' }], values: ['missing'], placeholder: 'Noch keine Formularfelder definiert' });
  formData = { fields: [{ name: 'field', field_type: 'text' }, { name: 'head', field_type: 'heading' }, { name: 'files', field_type: 'multiupload' }], required_fields: [], required_uploads: [] };
  rerender(<RequirementsPanel formData={formData} currentFieldOptions={[{ value: 'field', label: 'Field' }]} setFormData={setFormData} documentTypeOptions={[]} />);
  expect(mockCapturedMultis.filter(({ testId }) => testId === 'step-required-fields').at(-1)).toMatchObject({ options: [{ value: 'field', label: 'Field' }], placeholder: 'Pflichtfelder auswählen' });
  fireEvent.click(screen.getByTestId('step-required-fields'));
  const updater = setFormData.mock.calls.at(-1)[0];
  expect(updater(formData).fields).toEqual([{ name: 'field', field_type: 'text', required: true }, formData.fields[1], formData.fields[2]]);
  fireEvent.click(screen.getByTestId('step-required-uploads'));
  expect(setFormData).toHaveBeenCalledWith(expect.objectContaining({ required_uploads: ['field'] }));
});

test('mappings panel covers empty and populated mapping commands', () => {
  mockCapturedSearchables = []; mockCapturedHelp = [];
  const callbacks = { addMapping: jest.fn(), removeMapping: jest.fn(), changeMappingSource: jest.fn(), updateMapping: jest.fn(), sourceFieldOptions: jest.fn(() => [{ value: 'status' }, { value: 'name' }]) };
  const props = { ...callbacks, formData: { field_mappings: [] }, stepOptions: [], currentFieldOptions: [] };
  const { rerender } = render(<MappingsPanel {...props} />);
  expect(screen.getByText(/Keine Mappings/)).toBeInTheDocument(); fireEvent.click(screen.getByTestId('add-field-mapping'));
  rerender(<MappingsPanel {...props} formData={{ field_mappings: [{ source_step_order: null, source_field: '', target_field: '' }, { source_step_order: 2, source_field: 'missing', target_field: 'target' }] }} />);
  expect(screen.getByTestId('field-mapping-0')).toBeInTheDocument(); expect(screen.getByTestId('field-mapping-1')).toBeInTheDocument();
  expect(screen.getByText('Mapping 1')).toBeInTheDocument(); expect(screen.getByText('Mapping 2')).toBeInTheDocument(); expect(screen.queryByText(/Keine Mappings konfiguriert/)).not.toBeInTheDocument();
  const mappingPickers = mockCapturedSearchables.slice(-6);
  expect(mappingPickers.map(({ testId, value }) => [testId, value])).toEqual([
    ['mapping-source-step-0', ''], ['mapping-source-field-0', ''], ['mapping-target-field-0', ''],
    ['mapping-source-step-1', '2'], ['mapping-source-field-1', 'missing'], ['mapping-target-field-1', 'target'],
  ]);
  expect(mappingPickers[3].options).toEqual([{ value: '2', label: 'Nicht gefundener Schritt: 2' }]);
  expect(mappingPickers[4].options).toEqual([{ value: 'name' }]);
  expect(mappingPickers[5].options).toEqual([{ value: 'target', label: 'Nicht gefundenes Feld: target' }]);
  fireEvent.click(screen.getAllByText('Entfernen')[0]);
  fireEvent.click(screen.getByTestId('mapping-source-step-0')); fireEvent.click(screen.getByTestId('mapping-source-field-0')); fireEvent.click(screen.getByTestId('mapping-target-field-0'));
  fireEvent.click(screen.getByTestId('mapping-source-step-1')); fireEvent.click(screen.getByTestId('mapping-source-field-1')); fireEvent.click(screen.getByTestId('mapping-target-field-1'));
  expect(callbacks.removeMapping).toHaveBeenCalledWith(0); expect(callbacks.changeMappingSource).toHaveBeenCalledWith(0, 'changed');
  expect(callbacks.updateMapping).toHaveBeenCalledWith(0, { source_field: 'changed' });
  expect(callbacks.changeMappingSource).toHaveBeenCalledWith(1, 'changed');
  expect(callbacks.updateMapping).toHaveBeenCalledWith(1, { source_field: 'changed' });
  expect(callbacks.updateMapping).toHaveBeenCalledWith(1, { target_field: 'changed' });
  expect(mockCapturedHelp.slice(-7)).toEqual([
    'Mappings lesen einen gespeicherten Wert aus dem Quell-Step und schreiben ihn als Vorbelegung in das Zielfeld dieses Steps.',
    'Step, dessen bereits gespeicherte Nutzerdaten gelesen werden.', 'Technischer Feldname, aus dem der Wert übernommen wird.', 'Feld dieses Steps, das mit dem gelesenen Wert vorbelegt wird.',
    'Step, dessen bereits gespeicherte Nutzerdaten gelesen werden.', 'Technischer Feldname, aus dem der Wert übernommen wird.', 'Feld dieses Steps, das mit dem gelesenen Wert vorbelegt wird.',
  ]);
});

test('notification panel toggles triggers and edits all optional templates', () => {
  mockCapturedHelp = [];
  const setFormData = jest.fn(); const off = { email_on_enter: false, email_on_edit: false, email_on_leave: false };
  const { rerender } = render(<NotificationsPanel formData={off} setFormData={setFormData} />);
  expect(screen.getAllByTestId('switch')).toHaveLength(3);
  ['Bei Schritt-Eintritt', 'Bei Bearbeitung', 'Bei Schritt-Abschluss'].forEach(text => expect(screen.getByText(text)).toBeInTheDocument());
  expect(mockCapturedHelp.slice(-3)).toEqual(['Sendet beim ersten Öffnen beziehungsweise Starten dieses Steps.', 'Sendet bei späteren Änderungen gespeicherter Step-Daten, sofern Nutzer dies erlaubt haben.', 'Sendet unmittelbar beim erfolgreichen Abschluss dieses Steps.']);
  expect(screen.getByText('Verfügbare Variablen für E-Mail-Vorlagen:')).toBeInTheDocument();
  expect(screen.getAllByText(/^{{.*}}$/).map(node => node.textContent)).toEqual(['{{user_name}}', '{{user_email}}', '{{step_title}}', '{{step_order}}', '{{step_description}}']);
  screen.getAllByTestId('switch').forEach(button => fireEvent.click(button));
  expect(setFormData.mock.calls.map(([value]) => value)).toEqual([{ ...off, email_on_enter: true }, { ...off, email_on_edit: true }, { ...off, email_on_leave: true }]);
  rerender(<NotificationsPanel formData={{ email_on_enter: true, email_on_edit: true, email_on_leave: true }} setFormData={setFormData} />);
  ['email-subject-enter', 'email-body-enter', 'email-subject-edit', 'email-body-edit', 'email-subject-leave', 'email-body-leave'].forEach(id => expect(screen.getByTestId(id)).toHaveValue(''));
  const enabled = { email_on_enter: true, email_on_edit: true, email_on_leave: true, email_subject_enter: 'Enter subject', email_body_enter: 'Enter body', email_subject_edit: 'Edit subject', email_body_edit: 'Edit body', email_subject_leave: 'Leave subject', email_body_leave: 'Leave body' };
  rerender(<NotificationsPanel formData={enabled} setFormData={setFormData} />);
  expect(['E-Mail bei Eintritt', 'E-Mail bei Bearbeitung', 'E-Mail bei Abschluss'].map(text => screen.getByText(text).textContent)).toEqual(['E-Mail bei Eintritt', 'E-Mail bei Bearbeitung', 'E-Mail bei Abschluss']);
  expect([
    ['email-subject-enter', 'Enter subject', 'Schritt gestartet: {{step_title}}'], ['email-body-enter', 'Enter body', '<p>Hallo {{user_name}}, Sie haben {{step_title}} begonnen.</p>'],
    ['email-subject-edit', 'Edit subject', 'Schritt aktualisiert: {{step_title}}'], ['email-body-edit', 'Edit body', '<p>Hallo {{user_name}}, {{step_title}} wurde aktualisiert.</p>'],
    ['email-subject-leave', 'Leave subject', 'Schritt abgeschlossen: {{step_title}}'], ['email-body-leave', 'Leave body', '<p>Hallo {{user_name}}, herzlichen Glückwunsch! {{step_title}} ist abgeschlossen.</p>'],
  ].map(([id, value, placeholder]) => [screen.getByTestId(id).value, screen.getByTestId(id).placeholder])).toEqual([
    ['Enter subject', 'Schritt gestartet: {{step_title}}'], ['Enter body', '<p>Hallo {{user_name}}, Sie haben {{step_title}} begonnen.</p>'],
    ['Edit subject', 'Schritt aktualisiert: {{step_title}}'], ['Edit body', '<p>Hallo {{user_name}}, {{step_title}} wurde aktualisiert.</p>'],
    ['Leave subject', 'Schritt abgeschlossen: {{step_title}}'], ['Leave body', '<p>Hallo {{user_name}}, herzlichen Glückwunsch! {{step_title}} ist abgeschlossen.</p>'],
  ]);
  setFormData.mockClear();
  for (const input of screen.getAllByRole('textbox')) fireEvent.change(input, { target: { value: 'message' } });
  expect(setFormData.mock.calls.map(([value]) => value)).toEqual(['email_subject_enter', 'email_body_enter', 'email_subject_edit', 'email_body_edit', 'email_subject_leave', 'email_body_leave'].map(key => ({ ...enabled, [key]: 'message' })));
});

test('translations panel covers fallbacks, milestone/display fields and skip label', () => {
  const setTrans = jest.fn();
  const formData = { title: 'DE', description: 'Beschreibung', step_type: 'form', skippable: false };
  const { rerender } = render(<TranslationsPanel translations={{}} setTrans={setTrans} formData={formData} />);
  ['EN', 'English Translation', 'Title (EN)', 'Description (EN)', 'Deutsche Texte (DE) werden im Tab "Basis" gepflegt. Hier nur die englische Uebersetzung eingeben.'].forEach(text => expect(screen.getByText(text)).toBeInTheDocument());
  expect(screen.getByTestId('trans-en-title')).toHaveValue(''); expect(screen.getByTestId('trans-en-title')).toHaveAttribute('placeholder', 'DE');
  expect(screen.getByTestId('trans-en-description')).toHaveValue(''); expect(screen.getByTestId('trans-en-description')).toHaveAttribute('placeholder', 'Beschreibung');
  expect(screen.queryByText('Pending Message (EN)')).not.toBeInTheDocument();
  fireEvent.change(screen.getByTestId('trans-en-title'), { target: { value: 'EN' } }); fireEvent.change(screen.getByTestId('trans-en-description'), { target: { value: 'Desc' } });
  rerender(<TranslationsPanel translations={{ en: { title: 'Title', description: 'Description', pending_message: 'Pending', action_label: 'Action', skip_label: 'Skip' } }} setTrans={setTrans} formData={{ ...formData, step_type: 'display', skippable: true, pending_message: 'P', action_label: 'A', skip_label: 'S' }} />);
  ['Pending Message (EN)', 'Action Label (EN)', 'Skip Label (EN)'].forEach(text => expect(screen.getByText(text)).toBeInTheDocument());
  expect(screen.getAllByRole('textbox').map(node => [node.value, node.placeholder])).toEqual([['Title', 'DE'], ['Description', 'Beschreibung'], ['Pending', 'P'], ['Action', 'A'], ['Skip', 'S']]);
  setTrans.mockClear();
  screen.getAllByRole('textbox').forEach(input => fireEvent.change(input, { target: { value: 'changed' } }));
  expect(setTrans.mock.calls).toEqual([['en', 'title', 'changed'], ['en', 'description', 'changed'], ['en', 'pending_message', 'changed'], ['en', 'action_label', 'changed'], ['en', 'skip_label', 'changed']]);
  rerender(<TranslationsPanel translations={{ en: {} }} setTrans={setTrans} formData={{ ...formData, step_type: 'form', skippable: true }} />);
  expect(screen.getAllByRole('textbox').at(-1)).toHaveValue('');
  rerender(<TranslationsPanel translations={{}} setTrans={setTrans} formData={{ ...formData, step_type: 'form', skippable: true }} />);
  expect(screen.getAllByRole('textbox').at(-1)).toHaveValue('');
  rerender(<TranslationsPanel translations={{}} setTrans={setTrans} formData={{ ...formData, step_type: 'milestone' }} />);
  expect(screen.getAllByRole('textbox')).toHaveLength(4);
  expect(screen.getAllByRole('textbox').map(node => node.value)).toEqual(['', '', '', '']);
});
