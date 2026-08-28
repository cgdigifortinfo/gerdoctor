import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PartnerDashboard from './PartnerDashboard';
import { filesAPI, formatApiError, partnerDashboardAPI } from '../lib/api';
import { toast } from 'sonner';
import { validatePartnerLogo } from '../features/partnerProfile/logo';

const mockNavigate = jest.fn();
let mockAuth;
let mockT;
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }), { virtual: true });
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => mockAuth }));
jest.mock('../contexts/LanguageContext', () => ({ useLanguage: () => ({ t: mockT }) }));
jest.mock('../lib/api', () => ({
  partnerDashboardAPI: {
    getProfile: jest.fn(), getSubmissions: jest.fn(), getOtherUsers: jest.fn(), getInsights: jest.fn(),
    getBilling: jest.fn(), getStripeStatus: jest.fn(), getStripeInvoices: jest.fn(), updateBilling: jest.fn(),
    createCheckout: jest.fn(), createBillingPortal: jest.fn(), updateProfile: jest.fn(), updatePartnerData: jest.fn(), uploadLogo: jest.fn(),
    getUserDetail: jest.fn(), reopenMilestone: jest.fn(), performStepAction: jest.fn(),
  },
  filesAPI: { upload: jest.fn(), getUrl: jest.fn((id) => `/files/${id}`) }, formatApiError: jest.fn(() => 'api error'),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../features/partnerProfile/logo', () => ({ validatePartnerLogo: jest.fn() }));
jest.mock('../features/steps', () => ({ filterVisibleSteps: (steps) => steps }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('../components/ThemeLangToggle', () => ({ ThemeLangToggle: () => <i /> }));
jest.mock('../components/Logo', () => ({ Logo: () => <i /> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, asChild, ...props }) => asChild ? <>{children}</> : <button {...props}>{children}</button> }));
jest.mock('../components/ui/select', () => ({
  Select: ({ children, value, onValueChange }) => <div>{children}<button data-testid={`select-${value}`} onClick={() => onValueChange('all')}>select</button></div>,
  SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => <i />,
}));
jest.mock('../components/ui/tabs', () => {
  const ReactLib = require('react');
  return {
    Tabs: ({ children, value, onValueChange }) => <div data-current-tab={value}>{ReactLib.Children.map(children, child => ReactLib.isValidElement(child) ? ReactLib.cloneElement(child, { onValueChange }) : child)}</div>,
    TabsList: ({ children, onValueChange }) => <div>{ReactLib.Children.map(children, child => ReactLib.isValidElement(child) ? ReactLib.cloneElement(child, { onValueChange }) : child)}</div>,
    TabsTrigger: ({ children, value, onValueChange, ...props }) => <button onClick={() => onValueChange?.(value)} {...props}>{children}</button>,
    TabsContent: ({ children }) => <section>{children}</section>,
  };
});
jest.mock('../components/ui/dialog', () => ({
  Dialog: ({ open, children, onOpenChange }) => open ? <div><button data-testid="dialog-close" onClick={onOpenChange}>close</button>{children}</div> : null,
  DialogContent: ({ children }) => <div>{children}</div>, DialogHeader: ({ children }) => <div>{children}</div>, DialogTitle: ({ children }) => <h2>{children}</h2>,
}));
jest.mock('../components/PaginationControls', () => ({ usePagination: (items) => ({ paginatedItems: items }), PaginationControls: () => <i /> }));

const activeProfile = { id: 'p', name: 'Ada', partner_name: 'School', email: 'school@example.com', registration_status: 'active', is_active: true, survey_ids: ['survey'], tags: ['Berlin'], logo_url: '/logo.png', category: 'Language', description: 'Description' };
const active = { id: 'sub1', user_id: 'u1', user_name: 'Doctor One', user_email: 'one@example.com', status: 'submitted', completion_pct: 50, field_of_study: 'Medicine', partner_work_completed: false };
const completed = { id: 'sub2', user_id: 'u2', user_name: 'Doctor Two', user_email: 'two@example.com', status: 'reviewed', completion_pct: 100, partner_work_completed: true, partner_work_completed_at: '2026-08-01' };
const other = { id: 'other', user_id: 'u3', user_name: 'Doctor Three', user_email: 'three@example.com', completion_pct: 0 };
const detail = {
  id: 'u1', completion_pct: 50, partner_managed_step_ids: ['m'], revisions: [{ step_id: 'm', revision: 2, step_title: 'Milestone', step_version: 1, configuration_changed: true, data: null }],
  steps: [
    { id: 'done', order: 1, title: 'Done', step_type: 'form', fields: [{ name: 'file', label: 'File', field_type: 'file' }, { name: 'multi', label: 'Multi', field_type: 'multiupload' }] },
    { id: 'm', order: 2, title: 'Milestone', step_type: 'milestone', fields: [{ name: 'plain', label: 'Plain', field_type: 'text' }] },
    { id: 'pending', order: 3, title: 'Pending', step_type: 'form' },
  ],
  progress: [
    { step_id: 'done', status: 'completed', configuration_changed: true, step_version: 1, current_step_version: 2, data: { skipped: true, file: 'f1', multi: [{ file_id: 'f2', filename: 'A', document_type: 'Doc' }, { filename: '' }], array: ['x', { a: 1 }], object: { x: 1 }, empty: '' } },
    { step_id: 'm', status: 'in_progress', step_snapshot: { fields: [{ name: 'removed', label: 'Removed', field_type: 'text' }] }, data: { plain: 'value', removed: 'old', partner_uploads: [{ file_id: 'p1', filename: '', document_type: '' }], partner_rejection: { reason: 'Reason' } } },
  ],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockT = (key) => key;
  window.history.replaceState({}, '', '/partner-dashboard?tab=billing');
  mockAuth = { user: { name: 'User', email: 'u@x.de' }, logout: jest.fn().mockResolvedValue(), impersonating: false, stopImpersonation: jest.fn() };
  formatApiError.mockReturnValue('api error'); validatePartnerLogo.mockReturnValue(null);
  partnerDashboardAPI.getProfile.mockResolvedValue({ data: activeProfile });
  partnerDashboardAPI.getSubmissions.mockResolvedValue({ data: [active, completed] });
  partnerDashboardAPI.getOtherUsers.mockResolvedValue({ data: [other] });
  partnerDashboardAPI.getInsights.mockResolvedValue({ data: { new_submissions_7d: 1, new_submissions_30d: 2, total_linked_users: 3, by_fachrichtung: [{ label: 'Med', count: 2 }], by_bundesland: [{ label: 'Berlin', count: 1 }], timeline_30d: [{ date: 'd', count: 1 }], conversion_funnel: { received: 3, accepted: 2, completed: 1 }, conversion_rate_pct: 33 } });
  partnerDashboardAPI.getBilling.mockResolvedValue({ data: { settings: { legal_name: 'School' }, usage: { pending_users: 1, pending_amount: 100, billed_users: 2, billed_amount: 200, currency: 'eur' }, pricing: [{ step_id: 'a', step_order: 1, step_title: 'A', source: 'partner_step', amount: 100, currency: 'eur' }, { step_id: 'b', step_order: 2, step_title: 'B', source: 'step', amount: 200 }, { step_id: 'c', step_order: 3, step_title: 'C', source: 'global', amount: 300 }] } });
  partnerDashboardAPI.getStripeStatus.mockResolvedValue({ data: { configured: true, customer_created: false, sandbox_mode: true } });
  partnerDashboardAPI.getStripeInvoices.mockResolvedValue({ data: [{ id: 'i', number: '', status: 'open', amount_due: 0, currency: '', hosted_invoice_url: '/invoice', invoice_pdf: '/pdf' }] });
  partnerDashboardAPI.updateBilling.mockResolvedValue({}); partnerDashboardAPI.createCheckout.mockResolvedValue({ data: { url: '/checkout' } }); partnerDashboardAPI.createBillingPortal.mockResolvedValue({ data: { url: '/portal' } });
  partnerDashboardAPI.updateProfile.mockResolvedValue({}); partnerDashboardAPI.updatePartnerData.mockResolvedValue({}); partnerDashboardAPI.uploadLogo.mockResolvedValue({ data: { logo_url: '/new-logo.png' } });
  partnerDashboardAPI.getUserDetail.mockResolvedValue({ data: detail }); partnerDashboardAPI.reopenMilestone.mockResolvedValue({}); partnerDashboardAPI.performStepAction.mockResolvedValue({ data: {} });
  filesAPI.upload.mockResolvedValue({ data: { id: 'new', filename: '' } });
});

async function renderDashboard(props = {}) {
  const view = render(<PartnerDashboard location={{ assign: jest.fn() }} {...props} />);
  await screen.findByText('Doctor One');
  return view;
}

test('active dashboard loads all panels, billing data and core navigation actions', async () => {
  const location = { assign: jest.fn() };
  render(<PartnerDashboard location={location} />);
  expect(screen.getByText('Loading...')).toBeInTheDocument();
  await screen.findByText('Doctor One');
  await waitFor(() => expect(partnerDashboardAPI.getBilling).toHaveBeenCalled());
  expect(screen.getByTestId('kpi-new-7d')).toHaveTextContent('1');
  expect(screen.getByTestId('partner-service-price-a')).toHaveTextContent('individueller Partnerpreis');
  expect(screen.getByTestId('partner-service-price-b')).toHaveTextContent('Step-Preis');
  expect(screen.getByTestId('partner-service-price-c')).toHaveTextContent('globaler Standardpreis');
  fireEvent.click(screen.getByTestId('partner-stripe-checkout'));
  await waitFor(() => expect(location.assign).toHaveBeenCalledWith('/checkout'));
  fireEvent.change(screen.getByDisplayValue('School'), { target: { value: 'School GmbH' } });
  const billingInputs = screen.getAllByRole('textbox').slice(-7);
  billingInputs.forEach(input => fireEvent.change(input, { target: { value: 'ABC' } }));
  fireEvent.click(screen.getByText('Einstellungen speichern'));
  await waitFor(() => expect(partnerDashboardAPI.updateBilling).toHaveBeenCalled());
  fireEvent.click(screen.getByTestId('partner-logout-btn'));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/'));
});

test('profile editing manages tags, logo validation/upload, cancellation and save failures/success', async () => {
  await renderDashboard();
  fireEvent.click(screen.getByTestId('edit-profile-btn'));
  fireEvent.change(screen.getByTestId('profile-name-input'), { target: { value: 'New Name' } });
  fireEvent.change(screen.getByTestId('profile-description-input'), { target: { value: 'New Description' } });
  fireEvent.change(screen.getByTestId('new-tag-input'), { target: { value: '  Bayern  ' } });
  fireEvent.keyDown(screen.getByTestId('new-tag-input'), { key: 'x' });
  fireEvent.keyDown(screen.getByTestId('new-tag-input'), { key: 'Enter' });
  expect(screen.getByTestId('tag-chip-Bayern')).toBeInTheDocument();
  fireEvent.change(screen.getByTestId('new-tag-input'), { target: { value: 'Bayern' } }); fireEvent.click(screen.getByTestId('add-tag-btn'));
  fireEvent.change(screen.getByTestId('new-tag-input'), { target: { value: '   ' } }); fireEvent.click(screen.getByTestId('add-tag-btn'));
  fireEvent.click(screen.getByTestId('remove-tag-Berlin'));
  fireEvent.click(screen.getByText('Baden-Württemberg'));
  const file = new File(['logo'], 'logo.png', { type: 'image/png' });
  validatePartnerLogo.mockReturnValueOnce('bad logo');
  fireEvent.change(screen.getByTestId('partner-logo-input'), { target: { files: [file] } });
  expect(toast.error).toHaveBeenCalledWith('bad logo');
  validatePartnerLogo.mockReturnValue(null);
  const originalReader = global.FileReader;
  global.FileReader = class { readAsDataURL() { this.result = 'data:image/png;base64,x'; this.onload(); } };
  fireEvent.change(screen.getByTestId('partner-logo-input'), { target: { files: [file] } });
  fireEvent.click(screen.getByTestId('partner-logo-upload-btn'));
  await waitFor(() => expect(partnerDashboardAPI.uploadLogo).toHaveBeenCalledWith(file));
  global.FileReader = originalReader;
  fireEvent.click(screen.getByTestId('save-profile-btn'));
  await waitFor(() => expect(partnerDashboardAPI.updateProfile).toHaveBeenCalledWith({ name: 'New Name' }));
  expect(partnerDashboardAPI.updatePartnerData).toHaveBeenCalled();
});

test('user detail renders every data shape, completes with upload, validates rejection and reopens', async () => {
  await renderDashboard();
  fireEvent.click(screen.getByTestId('view-user-u1'));
  expect(screen.getByText('loading')).toBeInTheDocument();
  await screen.findByTestId('detail-step-2');
  expect(screen.getByTestId('historical-config-done')).toBeInTheDocument();
  expect(screen.getByTestId('partner-rejection-2')).toHaveTextContent('Reason');
  expect(screen.getByTestId('partner-historical-revisions')).toBeInTheDocument();
  const pdf = new File(['pdf'], 'demo.pdf', { type: 'application/pdf' });
  fireEvent.change(screen.getByTestId('milestone-file-input-2'), { target: { files: [pdf] } });
  expect(screen.getByTestId('milestone-file-name-2')).toHaveTextContent('demo.pdf');
  fireEvent.click(screen.getByTestId('milestone-complete-btn-2'));
  await waitFor(() => expect(filesAPI.upload).toHaveBeenCalledWith(pdf));
  await waitFor(() => expect(partnerDashboardAPI.performStepAction).toHaveBeenCalledWith('u1', 'm', 'complete', '', expect.objectContaining({ partner_uploads: expect.any(Array) })));
  fireEvent.click(screen.getByTestId('milestone-reject-btn-2'));
  expect(toast.error).toHaveBeenCalledWith('Bitte geben Sie einen Grund für die Ablehnung an.');
  fireEvent.change(screen.getByTestId('milestone-rejection-reason-2'), { target: { value: ' Retry ' } });
  partnerDashboardAPI.performStepAction.mockResolvedValueOnce({ data: { reopened_step: { title: 'Previous' } } });
  fireEvent.click(screen.getByTestId('milestone-reject-btn-2'));
  await waitFor(() => expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Previous')));
  fireEvent.click(screen.getByTestId('reopen-user-u2'));
  await waitFor(() => expect(partnerDashboardAPI.reopenMilestone).toHaveBeenCalledWith('u2'));
  fireEvent.click(screen.getByTestId('dialog-close'));
});

test('pending activation limits navigation while preserving profile, billing and insights', async () => {
  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: { name: 'Pending', partner_name: '', registration_status: 'pending', is_active: false, survey_ids: [] } });
  partnerDashboardAPI.getInsights.mockResolvedValueOnce({ data: null });
  window.history.replaceState({}, '', '/partner-dashboard?tab=other-users');
  render(<PartnerDashboard location={{ assign: jest.fn() }} />);
  expect(await screen.findByTestId('partner-pending-activation')).toBeInTheDocument();
  expect(partnerDashboardAPI.getSubmissions).not.toHaveBeenCalled();
  fireEvent.click(screen.getByTestId('pending-open-profile'));
  fireEvent.click(screen.getByTestId('pending-open-billing'));
  await waitFor(() => expect(partnerDashboardAPI.getStripeStatus).toHaveBeenCalled());
  expect(screen.queryByTestId('tab-other-users')).not.toBeInTheDocument();
});

test('unlinked, impersonated and API error states remain recoverable', async () => {
  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: null });
  const unlinked = render(<PartnerDashboard />);
  expect(await screen.findByText('Account Not Linked')).toBeInTheDocument(); unlinked.unmount();
  mockAuth = { ...mockAuth, impersonating: true };
  const impersonated = await renderDashboard();
  await waitFor(() => expect(partnerDashboardAPI.getStripeStatus).toHaveBeenCalled());
  fireEvent.click(screen.getByTestId('stop-impersonation-btn'));
  expect(mockAuth.stopImpersonation).toHaveBeenCalled(); expect(mockNavigate).toHaveBeenCalledWith('/admin'); impersonated.unmount();
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  partnerDashboardAPI.getSubmissions.mockRejectedValueOnce({ response: { status: 400 } });
  render(<PartnerDashboard />);
  await waitFor(() => expect(error).toHaveBeenCalled());
  error.mockRestore();
});

test('reports billing, Stripe, profile, logo, detail, reopen and step-action failures', async () => {
  const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
  await renderDashboard();
  await waitFor(() => expect(partnerDashboardAPI.getStripeStatus).toHaveBeenCalled());
  partnerDashboardAPI.updateBilling.mockRejectedValueOnce(new Error('save billing'));
  fireEvent.click(screen.getByText('Einstellungen speichern'));
  partnerDashboardAPI.createCheckout.mockRejectedValueOnce(new Error('checkout'));
  fireEvent.click(screen.getByTestId('partner-stripe-checkout'));
  fireEvent.click(screen.getByTestId('edit-profile-btn'));
  partnerDashboardAPI.updatePartnerData.mockRejectedValueOnce(new Error('profile'));
  fireEvent.click(screen.getByTestId('save-profile-btn'));
  validatePartnerLogo.mockReturnValueOnce('missing');
  fireEvent.click(screen.getByTestId('partner-logo-upload-btn'));
  partnerDashboardAPI.getUserDetail.mockRejectedValueOnce(new Error('detail'));
  fireEvent.click(screen.getByTestId('view-user-u1'));
  partnerDashboardAPI.reopenMilestone.mockRejectedValueOnce(new Error('reopen'));
  fireEvent.click(screen.getByTestId('reopen-user-u2'));
  await waitFor(() => expect(toast.error).toHaveBeenCalled());
  consoleError.mockRestore();
});

test('reports a billing-load failure and tolerates an invoice-load failure', async () => {
  partnerDashboardAPI.getBilling.mockRejectedValueOnce(new Error('billing'));
  partnerDashboardAPI.getStripeInvoices.mockRejectedValueOnce(new Error('invoices'));
  await renderDashboard();
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
});

test('opens a deep-linked user and clears the URL', async () => {
  window.history.replaceState({}, '', '/partner-dashboard?openUser=u1');
  const replace = jest.spyOn(window.history, 'replaceState');
  const view = render(<PartnerDashboard />);
  await waitFor(() => expect(partnerDashboardAPI.getUserDetail).toHaveBeenCalledWith('u1'));
  expect(screen.getByTestId('detail-user-name')).toHaveTextContent('Doctor One');
  expect(document.querySelector('[data-current-tab]')).toHaveAttribute('data-current-tab', 'my-users');
  expect(replace).toHaveBeenCalled();
  view.unmount();
  replace.mockRestore();
});

test('reports a missing deep link and supports Stripe portal/error branches', async () => {
  window.history.replaceState({}, '', '/partner-dashboard?openUser=missing&tab=billing');
  partnerDashboardAPI.getStripeStatus.mockResolvedValueOnce({ data: { configured: true, customer_created: true, sandbox_mode: false } });
  const location = { assign: jest.fn() };
  render(<PartnerDashboard location={location} />);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('User nicht in Ihrem Dashboard gefunden'));
  partnerDashboardAPI.createBillingPortal.mockRejectedValueOnce(new Error('portal'));
  fireEvent.click(screen.getByTestId('partner-stripe-portal'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
});

test('opens the successful Stripe billing portal', async () => {
  partnerDashboardAPI.getStripeStatus.mockResolvedValueOnce({ data: { configured: true, customer_created: true } });
  const location = { assign: jest.fn() };
  await renderDashboard({ location });
  await waitFor(() => expect(screen.getByTestId('partner-stripe-portal')).toBeInTheDocument());
  fireEvent.click(screen.getByTestId('partner-stripe-portal'));
  await waitFor(() => expect(location.assign).toHaveBeenCalledWith('/portal'));
});

test('covers empty defaults, cancellation and upload/action failures', async () => {
  window.history.replaceState({}, '', '/partner-dashboard');
  partnerDashboardAPI.getBilling.mockResolvedValueOnce({ data: {} });
  partnerDashboardAPI.getStripeStatus.mockResolvedValueOnce({ data: {} });
  partnerDashboardAPI.getStripeInvoices.mockRejectedValueOnce(new Error('ignored'));
  partnerDashboardAPI.getInsights.mockRejectedValueOnce(new Error('ignored'));
  const emptyProfile = { ...activeProfile, name: undefined, description: undefined, tags: undefined, logo_url: undefined, category: undefined };
  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: emptyProfile });
  await renderDashboard();
  expect(screen.getByTestId('stripe-not-configured')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('edit-profile-btn'));
  expect(screen.getByText('Noch kein Logo')).toBeInTheDocument();
  fireEvent.click(screen.getByText('cancel'));
  fireEvent.click(screen.getByTestId('edit-profile-btn'));
  const file = new File(['x'], 'x.png', { type: 'image/png' });
  const originalReader = global.FileReader;
  global.FileReader = class { readAsDataURL() { this.result = null; this.onload(); } };
  fireEvent.change(screen.getByTestId('partner-logo-input'), { target: { files: [file] } });
  partnerDashboardAPI.uploadLogo.mockRejectedValueOnce(new Error('upload'));
  await waitFor(() => expect(screen.getByTestId('partner-logo-upload-btn')).not.toBeDisabled());
  fireEvent.click(screen.getByTestId('partner-logo-upload-btn'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
  global.FileReader = originalReader;
  fireEvent.click(screen.getByTestId('view-user-u1'));
  await screen.findByTestId('detail-step-2');
  partnerDashboardAPI.performStepAction.mockRejectedValueOnce(new Error('action'));
  fireEvent.change(screen.getByTestId('milestone-rejection-reason-2'), { target: { value: 'No' } });
  fireEvent.click(screen.getByTestId('milestone-reject-btn-2'));
  await waitFor(() => expect(partnerDashboardAPI.performStepAction).toHaveBeenCalled());
});

test('uses profile and insight fallbacks when both optional loads fail', async () => {
  partnerDashboardAPI.getProfile.mockRejectedValueOnce(new Error('profile unavailable'));
  partnerDashboardAPI.getInsights.mockRejectedValueOnce(new Error('insights unavailable'));
  render(<PartnerDashboard />);
  expect(await screen.findByTestId('partner-pending-activation')).toBeInTheDocument();
  expect(screen.getAllByText('User')).not.toHaveLength(0);
});

test('normalizes every empty billing response section after opening billing', async () => {
  window.history.replaceState({}, '', '/partner-dashboard');
  partnerDashboardAPI.getBilling.mockResolvedValueOnce({ data: {} });
  partnerDashboardAPI.getStripeStatus.mockResolvedValueOnce({ data: null });
  partnerDashboardAPI.getStripeInvoices.mockResolvedValueOnce({ data: null });
  await renderDashboard();
  fireEvent.click(screen.getByTestId('tab-billing'));
  await waitFor(() => expect(partnerDashboardAPI.getBilling).toHaveBeenCalled());
  expect(screen.getByTestId('stripe-not-configured')).toBeInTheDocument();
});

test('reports an unlinked 400 profile load and resets failed milestone upload state', async () => {
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: activeProfile });
  partnerDashboardAPI.getSubmissions.mockRejectedValueOnce({ response: { status: 400 } });
  render(<PartnerDashboard />);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Your account is not linked to a partner'));
  error.mockRestore();

  partnerDashboardAPI.getSubmissions.mockResolvedValue({ data: [active, completed] });
  await renderDashboard();
  fireEvent.click(screen.getAllByTestId('view-user-u1').slice(-1)[0]);
  await screen.findAllByTestId('detail-step-2');
  partnerDashboardAPI.performStepAction.mockRejectedValueOnce(new Error('failed action'));
  fireEvent.change(screen.getAllByTestId('milestone-rejection-reason-2').slice(-1)[0], { target: { value: 'Retry' } });
  fireEvent.click(screen.getAllByTestId('milestone-reject-btn-2').slice(-1)[0]);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
});

test('saves a profile without optional user and partner fields and handles an empty logo selection', async () => {
  const sparse = { ...activeProfile, name: undefined, description: undefined, tags: undefined, logo_url: undefined };
  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: sparse });
  await renderDashboard();
  fireEvent.click(screen.getByTestId('edit-profile-btn'));
  fireEvent.change(screen.getByTestId('partner-logo-input'), { target: { files: [] } });
  fireEvent.change(screen.getByTestId('new-tag-input'), { target: { value: 'New' } });
  fireEvent.click(screen.getByTestId('add-tag-btn'));
  fireEvent.click(screen.getByTestId('save-profile-btn'));
  await waitFor(() => expect(partnerDashboardAPI.updatePartnerData).toHaveBeenCalledWith({ description: '', tags: ['New'] }));
  expect(partnerDashboardAPI.updateProfile).not.toHaveBeenCalled();
});

test('renders legacy and removed detail shapes and completes without prior partner uploads', async () => {
  const legacyDetail = {
    id: 'u1', completion_pct: 10, partner_managed_step_ids: null, partner_step_id: 'legacy-milestone', revisions: [],
    steps: [
      { id: 'legacy-milestone', order: 1, title: 'Legacy milestone', step_type: 'milestone' },
      { id: 'removed-data', order: 2, title: 'Removed data', step_type: 'form', fields: [] },
      { id: 'no-data', order: 3, title: 'No data', step_type: 'form' },
    ],
    progress: [
      { step_id: 'legacy-milestone', status: 'in_progress', data: {} },
      { step_id: 'removed-data', status: 'completed', step_snapshot: { fields: [
        { name: 'old_file', label: 'Old file', field_type: 'file' }, { name: 'old_multi', label: 'Old multi', field_type: 'multiupload' },
      ] }, data: { old_file: 'file', old_multi: [{ file_id: 'multi', filename: '' }], empty_array: [] } },
      { step_id: 'no-data', status: 'in_progress', data: {} },
    ],
  };
  partnerDashboardAPI.getUserDetail.mockResolvedValue({ data: legacyDetail });
  await renderDashboard();
  fireEvent.click(screen.getByTestId('view-user-u1'));
  await screen.findByTestId('detail-step-1');
  expect(screen.getAllByText('Feld inzwischen gelöscht')).not.toHaveLength(0);
  expect(screen.getByTestId('step-data-2-empty_array')).toHaveTextContent('-');
  expect(screen.getAllByText('dash_no_data')).not.toHaveLength(0);
  fireEvent.change(screen.getByTestId('milestone-file-input-1'), { target: { files: [] } });
  const file = new File(['proof'], 'proof.pdf', { type: 'application/pdf' });
  fireEvent.change(screen.getByTestId('milestone-file-input-1'), { target: { files: [file] } });
  fireEvent.click(screen.getByTestId('milestone-complete-btn-1'));
  await waitFor(() => expect(partnerDashboardAPI.performStepAction).toHaveBeenCalledWith('u1', 'legacy-milestone', 'complete', '', expect.objectContaining({ partner_uploads: expect.any(Array) })));
  fireEvent.change(screen.getByTestId('milestone-rejection-reason-1'), { target: { value: 'Reject' } });
  partnerDashboardAPI.performStepAction.mockResolvedValueOnce({ data: {} });
  fireEvent.click(screen.getByTestId('milestone-reject-btn-1'));
  await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Step abgelehnt und User informiert.'));
});

test('renders detail steps when no partner-managed identifiers exist', async () => {
  partnerDashboardAPI.getUserDetail.mockResolvedValueOnce({ data: { id: 'u1', completion_pct: 0, partner_managed_step_ids: null, partner_step_id: null, revisions: [], steps: [{ id: 'plain', order: 1, title: 'Plain', step_type: 'form' }], progress: [] } });
  await renderDashboard();
  fireEvent.click(screen.getByTestId('view-user-u1'));
  expect(await screen.findByTestId('detail-step-1')).toBeInTheDocument();
});

test('evaluates activation without survey IDs, logs ordinary load failures and saves undefined tags', async () => {
  const noSurvey = { ...activeProfile, survey_ids: undefined };
  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: noSurvey });
  const pending = render(<PartnerDashboard />);
  expect(await screen.findByTestId('partner-pending-activation')).toBeInTheDocument();
  pending.unmount();

  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: activeProfile });
  partnerDashboardAPI.getSubmissions.mockRejectedValueOnce(new Error('ordinary failure'));
  const failed = render(<PartnerDashboard />);
  await waitFor(() => expect(error).toHaveBeenCalled());
  failed.unmount();
  error.mockRestore();

  partnerDashboardAPI.getProfile.mockResolvedValueOnce({ data: { ...activeProfile, name: 'Fallback name', partner_name: '', tags: undefined, description: undefined, logo_url: '/logo' } });
  await renderDashboard();
  fireEvent.click(screen.getByTestId('edit-profile-btn'));
  fireEvent.click(screen.getByTestId('save-profile-btn'));
  await waitFor(() => expect(partnerDashboardAPI.updatePartnerData).toHaveBeenCalledWith({ description: '', tags: [] }));
});

test('uses email in deep-link feedback and empty translations and billing currencies', async () => {
  mockT = () => '';
  window.history.replaceState({}, '', '/partner-dashboard?openUser=u3&tab=billing');
  partnerDashboardAPI.getOtherUsers.mockResolvedValueOnce({ data: [{ id: 'other-email', user_id: 'u3', user_name: '', user_email: 'three@example.com' }] });
  partnerDashboardAPI.getBilling.mockResolvedValueOnce({ data: { settings: {}, usage: { pending_users: 0, pending_amount: 0, billed_users: 0, billed_amount: 0, currency: '' }, pricing: [] } });
  render(<PartnerDashboard />);
  await waitFor(() => expect(toast.success).toHaveBeenCalledWith('three@example.com geöffnet'));
  expect(screen.getAllByText('Match')).not.toHaveLength(0);
});
