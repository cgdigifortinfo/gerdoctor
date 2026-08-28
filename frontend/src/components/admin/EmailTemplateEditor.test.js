import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import EmailTemplateEditor from './EmailTemplateEditor';
import { buildPreviewVariables, copyTextSafely, invalidRecipients, parseRecipients, readCookie, renderLayoutPreview, writeCookie } from '../../features/admin/emailTemplateDomain';
import { adminAPI } from '../../lib/api';
import { toast } from 'sonner';

let mockLocationSearch = '';
jest.mock('react-router-dom', () => ({ useLocation: () => ({ search: mockLocationSearch }) }), { virtual: true });
jest.mock('../../lib/api', () => ({ adminAPI: {
  listEmailTemplates: jest.fn(), getUsers: jest.fn(), getSteps: jest.fn(), previewEmailTemplate: jest.fn(),
  previewNotificationTemplate: jest.fn(), updateEmailTemplate: jest.fn(), resetEmailTemplate: jest.fn(), sendTestEmail: jest.fn(),
} }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn(), warning: jest.fn() } }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('react-simple-wysiwyg', () => ({
  EditorProvider: ({ children }) => <>{children}</>, Toolbar: ({ children }) => <div>{children}</div>,
  Editor: ({ value, onChange, children }) => <div>{children}<textarea data-testid="wysiwyg-input" value={value} onChange={onChange} /></div>,
  BtnBold: () => <i />, BtnItalic: () => <i />, BtnUnderline: () => <i />, BtnLink: () => <i />,
  BtnBulletList: () => <i />, BtnNumberedList: () => <i />, BtnClearFormatting: () => <i />, BtnStyles: () => <i />, Separator: () => <i />,
}), { virtual: true });
jest.mock('../ui/button', () => ({ Button: ({ children, ...props }) => <button {...props}>{children}</button> }));
jest.mock('../ui/dialog', () => ({
  Dialog: ({ open, children }) => open ? <div>{children}</div> : null, DialogContent: ({ children, ...props }) => <div {...props}>{children}</div>,
  DialogHeader: ({ children }) => <div>{children}</div>, DialogTitle: ({ children }) => <h2>{children}</h2>,
  DialogDescription: ({ children }) => <p>{children}</p>, DialogFooter: ({ children }) => <div>{children}</div>,
}));
jest.mock('../ui/select', () => ({
  Select: ({ children, value, onValueChange }) => {
    const flatten = (node) => Array.isArray(node) ? node.map(flatten).join(' ') : node && typeof node === 'object' ? flatten(node.props?.children) : String(node || '');
    const content = flatten(children);
    let next = value;
    if (content.includes('Dummy-User')) next = value === 'default' ? 'u1' : 'default';
    else if (content.includes('Dummy-Step')) next = value === 'default' ? 's1' : 'default';
    else next = value === 'welcome' ? 'layout_header' : value === 'layout_header' ? 'partner_notice' : 'welcome';
    return <div>{children}<button data-testid={`select-action-${value}`} onClick={() => onValueChange(next)}>select</button></div>;
  },
  SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children, ...props }) => <span {...props}>{children}</span>,
  SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: ({ placeholder }) => <span>{placeholder}</span>,
}));

const templates = [
  { key: 'layout_header', category: 'layout', description: 'Header', body_html: '<b>{{user_name}}</b>{{unknown}}' },
  { key: 'partner_notice', category: 'partner', description: 'Partner' },
  { key: 'welcome', category: 'user', description: 'Welcome', subject: 'Hallo {{user_name}} {{unknown}}', body_html: '<p>Body</p>', notification_title: 'Titel', notification_body: 'Text' },
  { key: 'step_done', category: 'step', description: 'Step' },
];

const response = () => ({ data: { templates, variables: { user: ['user_name'], layout: ['user_name'] } } });

beforeEach(() => {
  jest.clearAllMocks();
  mockLocationSearch = '';
  document.cookie = 'email_tpl_test_recipients=; Max-Age=0; Path=/';
  adminAPI.listEmailTemplates.mockResolvedValue(response());
  adminAPI.getUsers.mockResolvedValue({ data: [{ id: 'p', role: 'partner' }, { id: 'u1', role: 'user', email: 'ada@example.com', partner_names: ['Partner A'] }] });
  adminAPI.getSteps.mockResolvedValue({ data: [{ id: 's2', order: 2, title: 'Two' }, { id: 's1', order: 1, title: 'One', description: '' }] });
  adminAPI.previewEmailTemplate.mockResolvedValue({ data: { html: '<p>preview</p>' } });
  adminAPI.previewNotificationTemplate.mockResolvedValue({ data: { title: 'Preview title', body: 'Preview body' } });
  adminAPI.updateEmailTemplate.mockResolvedValue({});
  adminAPI.resetEmailTemplate.mockResolvedValue({ data: {} });
  adminAPI.sendTestEmail.mockResolvedValue({ data: { sent: 1, failed: [], skipped: 0, recipients: ['a@b.de'] } });
});

test('pure email helpers cover cookies, preview fallbacks and recipient validation', () => {
  expect(readCookie('absent')).toBe('');
  writeCookie('demo_cookie', 'a b');
  expect(readCookie('demo_cookie')).toBe('a b');
  document.cookie = 'empty_cookie=';
  expect(readCookie('empty_cookie')).toBe('');
  expect(parseRecipients(' a@b.de, ;bad\nc@d.de ')).toEqual(['a@b.de', 'bad', 'c@d.de']);
  expect(parseRecipients()).toEqual([]);
  expect(invalidRecipients(['a@b.de', 'bad'])).toEqual(['bad']);
  expect(invalidRecipients(['prefix a@b.de suffix', 'a@b.d', 'a@b.de'])).toEqual(['prefix a@b.de suffix']);
  expect(invalidRecipients(['bad good@b.de', 'good@b.de bad'])).toEqual(['bad good@b.de', 'good@b.de bad']);
  expect(invalidRecipients(['ab@b.de', 'a@bc.de'])).toEqual([]);
  const defaults = buildPreviewVariables([], [], '', '', 'https://test');
  expect(defaults.user_name).toContain('Mustermann');
  const named = buildPreviewVariables([{ id: 'u', name: 'Ada', email: 'a@b.de', partner_names: ['First'] }], [{ id: 's', title: 'Step', order: 3, description: 'Desc' }], 'u', 's', 'https://test');
  expect(named).toEqual(expect.objectContaining({ user_name: 'Ada', partner_name: 'First', step_description: 'Desc', open_user_link: 'https://test/partner-dashboard?openUser=u' }));
  expect(buildPreviewVariables([{ id: 'u', email: 'fallback@b.de', partner_name: 'Legacy' }], [{ id: 's', title: 'S', order: 1 }], 'u', 's').step_description).toBe('');
  expect(buildPreviewVariables([], [{ id: 'wrong', title: 'Wrong' }, { id: 'target', title: 'Target', order: 2 }], '', 'target').step_title).toBe('Target');
  expect(buildPreviewVariables([{ id: 'u', email: 'x@y.de' }], [], 'u', '').partner_name).toBe('ILS Berlin');
  expect(renderLayoutPreview('{{user_name}}/{{missing}}', { user_name: 'Ada' })).toContain('Ada/');
  expect(renderLayoutPreview('{{missing}}/{{empty}}', { empty: null })).not.toContain('undefined');
  expect(renderLayoutPreview('', {})).toContain('background');
});

test('clipboard writes always settle without leaking browser failures', async () => {
  await expect(copyTextSafely(undefined, 'x')).resolves.toBeUndefined();
  await expect(copyTextSafely({ writeText: () => Promise.reject(new Error('denied')) }, 'x')).resolves.toBeUndefined();
  await expect(copyTextSafely({ writeText: () => { throw new Error('off'); } }, 'x')).resolves.toBeUndefined();
  await expect(copyTextSafely({ writeText: jest.fn().mockResolvedValue('done') }, 'x')).resolves.toBe('done');
});

async function renderEditor(search = '') {
  mockLocationSearch = search;
  render(<EmailTemplateEditor />);
  await screen.findByTestId('email-template-editor');
  await screen.findByTestId('email-template-item-layout_header');
}

test('loads requested email template, reference data, previews and supports editing and clipboard variants', async () => {
  await renderEditor('?template=welcome&channel=email');
  expect(screen.getByTestId('email-template-wysiwyg')).toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId('email-preview-subject')).toHaveTextContent('Dr. Maria Mustermann'));
  fireEvent.change(screen.getByTestId('email-template-subject-input'), { target: { value: 'Changed' } });
  fireEvent.change(screen.getByTestId('wysiwyg-input'), { target: { value: '<p>Changed</p>' } });
  fireEvent.click(screen.getByTestId('email-template-toggle-source'));
  fireEvent.change(screen.getByTestId('email-template-body-textarea'), { target: { value: '<b>Source</b>' } });
  fireEvent.click(screen.getByTestId('email-template-toggle-source'));
  fireEvent.click(screen.getAllByTestId('select-action-default')[0]);
  fireEvent.click(screen.getAllByTestId('select-action-default')[0]);
  fireEvent.click(screen.getByTestId('select-action-u1'));
  fireEvent.click(screen.getByTestId('select-action-s1'));
  await waitFor(() => expect(adminAPI.previewEmailTemplate).toHaveBeenCalled());

  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: jest.fn(() => Promise.reject(new Error('denied'))) } });
  fireEvent.click(screen.getByTestId('email-template-var-user_name'));
  expect(toast.success).toHaveBeenCalledWith('{{user_name}} in die Zwischenablage kopiert');
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: jest.fn(() => { throw new Error('off'); }) } });
  fireEvent.click(screen.getByTestId('email-template-var-user_name'));
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });
  fireEvent.click(screen.getByTestId('email-template-var-user_name'));
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: jest.fn(() => ({})) } });
  fireEvent.click(screen.getByTestId('email-template-var-user_name'));
});

test('switches notification and layout channels and handles preview success and failure', async () => {
  await renderEditor('?template=welcome&channel=notification');
  expect(screen.getByTestId('notification-message-editor')).toBeInTheDocument();
  await waitFor(() => expect(adminAPI.previewNotificationTemplate).toHaveBeenCalled());
  expect(await screen.findAllByText('Preview title')).toHaveLength(2);
  fireEvent.change(screen.getByTestId('notification-title-input'), { target: { value: 'New title' } });
  fireEvent.change(screen.getByTestId('notification-body-input'), { target: { value: 'New body' } });
  adminAPI.previewNotificationTemplate.mockRejectedValueOnce(new Error('preview'));
  fireEvent.change(screen.getByTestId('notification-body-input'), { target: { value: 'Fail preview' } });
  await waitFor(() => expect(screen.getAllByText('Notification-Titel').length).toBeGreaterThan(0));
  fireEvent.click(screen.getByTestId('message-channel-email'));
  expect(screen.getByTestId('email-message-editor')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('message-channel-notification'));
  fireEvent.click(screen.getByTestId('select-action-welcome'));
  await waitFor(() => expect(screen.getByText('Header')).toBeInTheDocument());
  expect(screen.queryByTestId('message-channel-toggle')).not.toBeInTheDocument();
  expect(screen.getByTestId('email-template-body-textarea')).toBeInTheDocument();
  expect(screen.getByTestId('email-preview-iframe').srcdoc).toContain('Dr. Maria Mustermann');
  fireEvent.click(screen.getByTestId('select-action-layout_header'));
  await waitFor(() => expect(screen.getByText('Partner')).toBeInTheDocument());
});

test('saves and resets with confirmation, success, sparse payloads and failures', async () => {
  await renderEditor('?template=welcome');
  fireEvent.click(screen.getByTestId('email-template-save-btn'));
  await waitFor(() => expect(adminAPI.updateEmailTemplate).toHaveBeenCalled());
  expect(toast.success).toHaveBeenCalledWith('Vorlage gespeichert');
  window.confirm = jest.fn(() => false);
  fireEvent.click(screen.getByTestId('email-template-reset-btn'));
  expect(adminAPI.resetEmailTemplate).not.toHaveBeenCalled();
  window.confirm.mockReturnValue(true);
  fireEvent.click(screen.getByTestId('email-template-reset-btn'));
  await waitFor(() => expect(adminAPI.resetEmailTemplate).toHaveBeenCalled());
  expect(toast.success).toHaveBeenCalledWith('Vorlage zurückgesetzt');
  adminAPI.updateEmailTemplate.mockRejectedValueOnce(new Error('save'));
  fireEvent.click(screen.getByTestId('email-template-save-btn'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Speichern fehlgeschlagen'));
  adminAPI.resetEmailTemplate.mockRejectedValueOnce(new Error('reset'));
  fireEvent.click(screen.getByTestId('email-template-reset-btn'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Zurücksetzen fehlgeschlagen'));
});

async function sendWith(result, recipients = 'a@b.de') {
  const previousCalls = adminAPI.sendTestEmail.mock.calls.length;
  adminAPI.sendTestEmail.mockImplementationOnce(result);
  fireEvent.click(screen.getByTestId('email-template-test-btn'));
  fireEvent.change(screen.getByTestId('email-test-recipients-input'), { target: { value: recipients } });
  fireEvent.click(screen.getByTestId('email-test-send-btn'));
  await waitFor(() => expect(adminAPI.sendTestEmail).toHaveBeenCalledTimes(previousCalls + 1));
  await waitFor(() => {
    const sendButton = screen.queryByTestId('email-test-send-btn');
    if (sendButton) expect(sendButton).not.toBeDisabled();
  });
}

test('validates and reports every test-email outcome and cookie prefill', async () => {
  writeCookie('email_tpl_test_recipients', 'saved@b.de');
  await renderEditor('?template=welcome');
  fireEvent.click(screen.getByTestId('email-template-test-btn'));
  expect(screen.getByTestId('email-test-recipients-input')).toHaveValue('saved@b.de');
  fireEvent.click(screen.getByTestId('email-test-cancel-btn'));
  fireEvent.click(screen.getByTestId('email-template-test-btn'));
  fireEvent.change(screen.getByTestId('email-test-recipients-input'), { target: { value: 'invalid' } });
  fireEvent.click(screen.getByTestId('email-test-send-btn'));
  expect(toast.error).toHaveBeenCalledWith('Ungültige Adressen: invalid');
  fireEvent.click(screen.getByTestId('email-test-cancel-btn'));
  await sendWith(() => Promise.resolve({ data: { sent: 1, recipients: ['a@b.de'] } }));
  await waitFor(() => expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('1 Empfänger')));
  await sendWith(() => Promise.resolve({ data: { sent: 0, skipped: 1 } }));
  await waitFor(() => expect(toast.warning).toHaveBeenCalled());
  await sendWith(() => Promise.resolve({ data: { sent: 0, skipped: 0, failed: [{ email: 'a@b.de' }] } }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Versand fehlgeschlagen: a@b.de'));
  await sendWith(() => Promise.resolve({ data: {} }));
  await waitFor(() => expect(adminAPI.sendTestEmail).toHaveBeenCalledTimes(4));
  await sendWith(() => Promise.resolve({}));
  await waitFor(() => expect(adminAPI.sendTestEmail).toHaveBeenCalledTimes(5));
  await sendWith(() => Promise.reject({ response: { data: { detail: 'Backend detail' } } }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Backend detail'));
  await sendWith(() => Promise.reject(new Error('network')));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Versand fehlgeschlagen'));
});

test('renders empty/loading states and survives template and reference loading failures', async () => {
  adminAPI.listEmailTemplates.mockRejectedValueOnce(new Error('templates'));
  adminAPI.getUsers.mockRejectedValueOnce(new Error('references'));
  render(<EmailTemplateEditor />);
  expect(screen.getAllByText('Lade Vorlagen...')).toHaveLength(2);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Vorlagen konnten nicht geladen werden'));
  expect(screen.getByText('Wählen Sie oben eine Vorlage aus.')).toBeInTheDocument();
  expect(screen.getByTestId('select-action-')).toBeInTheDocument();
});

test('uses sparse API fallbacks and ignores an unknown requested template', async () => {
  adminAPI.listEmailTemplates.mockResolvedValueOnce({ data: {} });
  adminAPI.getUsers.mockResolvedValueOnce({});
  adminAPI.getSteps.mockResolvedValueOnce({});
  render(<EmailTemplateEditor />);
  expect(await screen.findByText('Wählen Sie oben eine Vorlage aus.')).toBeInTheDocument();
});

test('keeps the current template on reload and covers empty preview payloads', async () => {
  adminAPI.previewEmailTemplate.mockResolvedValue({ data: {} });
  adminAPI.previewNotificationTemplate.mockResolvedValue({});
  await renderEditor('?template=unknown&channel=other');
  expect(screen.getByText('Header')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('select-action-layout_header'));
  await waitFor(() => expect(screen.getByText('Partner')).toBeInTheDocument());
  await waitFor(() => expect(adminAPI.previewEmailTemplate).toHaveBeenCalled());
  fireEvent.click(screen.getByTestId('message-channel-notification'));
  await waitFor(() => expect(adminAPI.previewNotificationTemplate).toHaveBeenCalled());
  fireEvent.click(screen.getByTestId('message-channel-email'));
  fireEvent.click(screen.getByTestId('email-template-save-btn'));
  await waitFor(() => expect(adminAPI.listEmailTemplates).toHaveBeenCalledTimes(2));
  expect(screen.getByText('Partner')).toBeInTheDocument();
});

test('clears notification preview when its backend preview fails', async () => {
  adminAPI.previewNotificationTemplate.mockRejectedValue(new Error('preview unavailable'));
  await renderEditor('?template=welcome&channel=notification');
  await waitFor(() => expect(adminAPI.previewNotificationTemplate).toHaveBeenCalled());
  expect(screen.getByTestId('notification-preview-title')).toHaveTextContent('Notification-Titel');
});
