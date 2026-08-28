// Stryker disable all: tests provide coverage and are never mutation targets.
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
jest.mock('react-router-dom', () => ({ Link: ({ children, ...props }) => <a {...props}>{children}</a> }), { virtual: true });
import { AnalyticsTab } from './AnalyticsTab';
import { AuditTab } from './AuditTab';
import { CmsTab } from './CmsTab';
import { PartnersTab } from './PartnersTab';
import { SettingsTab } from './SettingsTab';

const mockInvokeChanged = (callback) => { if (callback) callback('changed'); };
const mockInvokeFalse = (callback) => { if (callback) callback(false); };
import { UsersTab } from './UsersTab';
import { StepsTab } from './StepsTab';

jest.mock('../../../components/ui/tabs', () => ({ TabsContent: ({ children }) => <section>{children}</section> }));
jest.mock('../../../components/ui/select', () => ({
  Select: ({ children, onValueChange }) => <div>{children}<button data-testid="select-change" onClick={() => mockInvokeChanged(onValueChange)}>select</button></div>,
  SelectContent: ({ children }) => <>{children}</>, SelectItem: ({ children }) => <span>{children}</span>,
  SelectTrigger: ({ children, ...p }) => <div {...p}>{children}</div>, SelectValue: () => null,
}));
jest.mock('../../../components/ui/switch', () => ({ Switch: ({ onCheckedChange, ...p }) => <button {...p} onClick={() => mockInvokeFalse(onCheckedChange)}>switch</button> }));
jest.mock('../AdminDashboardComponents/AdminPrimitives', () => ({ StatCard: ({ label, value }) => <div>{label}{value}</div>, AuditActionBadge: ({ action }) => <span>{action}</span>, ElementToggle: ({ id, onChange }) => <button type="button" data-testid={`mock-${id}`} onClick={() => mockInvokeFalse(onChange)}>element switch</button> }));
jest.mock('../../../components/PaginationControls', () => ({ PaginationControls: () => <div>pagination</div> }));
jest.mock('../../../components/admin/PermissionGroupsManager', () => () => <div>groups</div>);
let mockFlowProps;
jest.mock('../../../components/StepsFlowBuilder', () => p => { mockFlowProps = p; return <div>flow builder</div>; });
jest.mock('../../../lib/api', () => ({ adminAPI: { updateStep: jest.fn(), saveStepLayout: jest.fn() }, formatApiError: () => 'api error' }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../AdminDashboardComponents/AdminCmsSections', () => ({
  LandingPagesSection: p => <button onClick={() => { p.onChange({}); p.onTransChange({}); p.onSave(); }}>landing</button>,
  CmsSection: p => <button onClick={() => { p.onChange({}); p.onTransChange({}); p.onSave(); }}>{p.title}</button>,
}));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));

const pagination = items => ({ paginatedItems: items, totalCount: items.length, startIndex: 10, currentPage: 1, totalPages: 1, setCurrentPage: jest.fn() });
const fn = () => jest.fn();

test('analytics renders populated and empty variants', () => {
  const analytics = { total_users: 4, total_partners: 2, total_submissions: 3, recent_registrations: 1, partner_count: 2, admin_count: 1 };
  const { rerender } = render(<AnalyticsTab analytics={analytics} analyticsPagination={pagination([{ step_id: 's', order: 1, title: 'Start', completed: 2, total: 4, completion_rate: 50 }])} />);
  expect(screen.getByText('Start')).toBeInTheDocument();
  rerender(<AnalyticsTab analytics={null} analyticsPagination={pagination([])} />);
  expect(screen.queryByText('Start')).not.toBeInTheDocument();
});

test('audit filters and renders complete and empty rows', () => {
  const p = { t: x => x, auditLogs: [{}], auditActionTypes: ['role_change'], auditFilter: 'all', setAuditFilter: fn(), auditDateFrom: '', setAuditDateFrom: fn(), auditDateTo: '', setAuditDateTo: fn(), handleAuditFilter: fn(), handleClearAuditFilter: fn() };
  const logs = [{ timestamp: '2026-01-01', actor_email: 'a@b.de', action: 'role_change', target_type: 'user', target_id: '123456789', details: { role: 'admin' } }, { actor_email: 'x', action: null, target_type: 'other' }];
  const { rerender } = render(<AuditTab {...p} auditPagination={pagination(logs)} />);
  fireEvent.change(screen.getByTestId('audit-date-from'), { target: { value: '2026-01-01' } });
  fireEvent.change(screen.getByTestId('audit-date-to'), { target: { value: '2026-01-02' } });
  fireEvent.click(screen.getByTestId('select-change')); fireEvent.click(screen.getByTestId('audit-apply-filter')); fireEvent.click(screen.getByTestId('audit-clear-filter'));
  expect(p.setAuditFilter).toHaveBeenCalled(); expect(screen.getByText(/role:/)).toBeInTheDocument();
  rerender(<AuditTab {...p} auditLogs={[]} auditPagination={pagination([])} />);
  expect(screen.getByText('No audit logs yet')).toBeInTheDocument();
});

test('CMS delegates all content changes and save commands', () => {
  const p = { surveys: [], cmsHome: {}, setCmsHome: fn(), cmsAbout: {}, setCmsAbout: fn(), cmsPartners: {}, setCmsPartners: fn(), cmsLandingPages: {}, setCmsLandingPages: fn(), cmsHomeTrans: {}, setCmsHomeTrans: fn(), cmsAboutTrans: {}, setCmsAboutTrans: fn(), cmsPartnersTrans: {}, setCmsPartnersTrans: fn(), cmsLandingPagesTrans: {}, setCmsLandingPagesTrans: fn(), cmsSaving: false, handleSaveCms: fn() };
  render(<CmsTab {...p} />);
  ['landing', 'Home / Hero Section', 'About Us Section', 'Partners Section'].forEach(label => fireEvent.click(screen.getByText(label)));
  expect(p.handleSaveCms).toHaveBeenCalledTimes(4); expect(p.setCmsHome).toHaveBeenCalled(); expect(p.setCmsLandingPagesTrans).toHaveBeenCalled();
});

test('partners covers pending, linked, unlinked, active and editing actions', () => {
  const p = { users: [{ id: 'u1', name: 'Linked' }], partners: [], setEditingPartner: fn(), setShowPartnerDialog: fn(), setShowLinkDialog: fn(), partnerView: 'active', setPartnerView: fn(), handleDeletePartner: fn(), handleUnlinkUser: fn() };
  const partners = [
    { id: 'p1', user_id: 'u1', name: 'Pending', contact_email: 'p@x', logo_url: '/x', service_steps: [{ order: 1, title: 'A' }], registration_source: 'self_service', registration_status: 'pending', pending_registrations: 2, category: 'School', tags: ['new'] },
    { id: 'p2', name: 'Inactive', contact_email: 'i@x', is_active: false, pending_registrations: 0, service_steps: [], tags: [] },
    { id: 'p3', name: 'Active', contact_email: 'a@x', is_active: true },
    { id: 'p4', name: 'Single', contact_email: 's@x', is_active: true, pending_registrations: 1 },
  ];
  render(<PartnersTab {...p} partners={partners} partnersPagination={pagination(partners)} />);
  fireEvent.click(screen.getByText(/Add Partner/)); fireEvent.click(screen.getByTestId('edit-partner-p1')); fireEvent.click(screen.getByTestId('delete-partner-p1')); fireEvent.click(screen.getByTestId('unlink-partner-p1')); fireEvent.click(screen.getByTestId('link-partner-p2'));
  expect(p.setShowPartnerDialog).toHaveBeenCalledTimes(2); expect(p.handleDeletePartner).toHaveBeenCalledWith('p1'); expect(screen.getByText('Wartet auf Survey')).toBeInTheDocument();
});

test('settings exercises editable fields, toggles, Stripe audit and billing variants', () => {
  const siteSettings = { site_title: 'Site', meta_description: 'Meta', logo_bold_part: 'GER', logo_light_part: 'doctor', contact_email: 'x@y.de', primary_color: '#112233', footer_text: 'Footer', stripe_sandbox_mode: true, stripe_partner_user_fee_cents: 25, stripe_partner_user_fee_currency: 'eur' };
  const setSiteSettings = jest.fn(updater => typeof updater === 'function' ? updater(siteSettings) : updater), handleSaveSettings = fn(), auditStripeConnections = fn(), repairStripeConnection = fn(), repairAllStripeConnections = fn();
  const stripeAudit = { defective: 2, repairable: 1, entries: [{ partner_id: 'p1', partner_name: 'Fix', emails: ['x@y.de'], issues: ['missing'], repairable: true, proposed_customer_id: 'cus', proposed_subscription_id: 'sub', proposed_billing_status: 'active' }, { partner_id: 'p2', partner_name: 'Manual', emails: [], issues: [], repairable: false }] };
  const adminBilling = { totals: { pending_users: 1, pending_amount: 25, billed_users: 2, billed_amount: 50 }, partners: [{ partner_id: 'p1', partner_name: 'Fix', usage: { pending_users: 1 }, invoices: [{ id: 'i1', number: 'R1', status: 'paid', amount_due: 50, currency: 'eur', hosted_invoice_url: '/view', invoice_pdf: '/pdf' }, { id: 'i2', status: 'open' }] }, { partner_id: 'p2', partner_name: 'None', usage: { pending_users: 0 }, invoices: [] }] };
  const { rerender, container } = render(<SettingsTab t={x => x} adminBilling={adminBilling} stripeAudit={stripeAudit} stripeAuditLoading={false} siteSettings={siteSettings} setSiteSettings={setSiteSettings} settingsSaving={false} handleSaveSettings={handleSaveSettings} auditStripeConnections={auditStripeConnections} repairStripeConnection={repairStripeConnection} repairAllStripeConnections={repairAllStripeConnections} />);
  container.querySelectorAll('input:not(:disabled)').forEach(input => fireEvent.change(input, { target: { value: input.type === 'color' ? '#445566' : input.type === 'number' ? '12' : 'changed' } }));
  fireEvent.change(container.querySelector('input[type="number"]'), { target: { value: '' } });
  ['ui_show_journey_indicator','ui_show_eta_header','ui_show_progress_percentage'].forEach(id => fireEvent.click(screen.getByTestId(`mock-${id}`))); screen.getAllByRole('button', { name: 'switch' }).forEach(button => fireEvent.click(button));
  fireEvent.click(screen.getByText('Stripe Tax automatisch').closest('label').querySelector('button')); fireEvent.click(screen.getByText('Aktionscodes erlauben').closest('label').querySelector('button'));
  fireEvent.click(screen.getByText('Verbindungen prüfen')); fireEvent.click(screen.getByText('Alle reparierbaren Einträge reparieren')); fireEvent.click(screen.getByText('Eintrag reparieren')); fireEvent.click(screen.getByTestId('save-settings-btn'));
  expect(setSiteSettings).toHaveBeenCalled(); expect(repairStripeConnection).toHaveBeenCalledWith('p1'); expect(handleSaveSettings).toHaveBeenCalled();
  rerender(<SettingsTab t={x => x} adminBilling={{}} stripeAudit={{ defective: 0, repairable: 0, entries: [] }} stripeAuditLoading siteSettings={{}} setSiteSettings={setSiteSettings} settingsSaving handleSaveSettings={handleSaveSettings} auditStripeConnections={auditStripeConnections} repairStripeConnection={repairStripeConnection} repairAllStripeConnections={repairAllStripeConnections} />);
  expect(screen.getByText('Keine fehlerhaften Stripe-Verbindungen gefunden.')).toBeInTheDocument(); expect(screen.getByText('Prüft…')).toBeDisabled();
  rerender(<SettingsTab t={x => x} adminBilling={{}} stripeAudit={{ defective: 0, repairable: 0 }} stripeAuditLoading={false} siteSettings={{}} setSiteSettings={setSiteSettings} settingsSaving={false} handleSaveSettings={handleSaveSettings} auditStripeConnections={auditStripeConnections} repairStripeConnection={repairStripeConnection} repairAllStripeConnections={repairAllStripeConnections} />); expect(screen.getByText('Keine fehlerhaften Stripe-Verbindungen gefunden.')).toBeInTheDocument();
});

test('users covers rows, permissions, bulk actions, groups and empty results', () => {
  const calls = { setUserSearch: fn(), setUserRoleFilter: fn(), setShowCreateUserDialog: fn(), setUserManagementView: fn(), setSelectedUserIds: fn(), setBulkRole: fn(), handleImpersonate: fn(), loadPermissionData: fn(), handleViewUser: fn(), handleUpdateUserRole: fn(), toggleUserSelection: fn(), toggleSelectAll: fn(), handleBulkRoleUpdate: fn(), handleExportCsv: fn() };
  const users = [
    { id: 'u1', name: 'Partner', email: 'p@x', role: 'partner', partner_registration_status: 'pending', pending_registrations: 1, permission_groups: [{ id: 'g', name: 'Group' }], partner_names: ['School'], orphaned_partner_references: [{ value: 'old' }], completion_pct: 50, estimated_completion: '2026-02-01', created_at: '2026-01-01' },
    { id: 'u2', name: 'Doctor', email: 'd@x', role: 'user', pending_registrations: 2 },
    { id: 'u3', name: 'Admin', email: 'a@x', role: 'admin', pending_registrations: 0 }, { id: 'u4', name: 'Empty', email: 'e@x', role: 'user' }, { id: 'u5', name: 'Multiple', email: 's@x', role: 'partner', pending_registrations: 2 },
  ];
  const props = { t: x => x, users, userSearch: '', userRoleFilter: 'all', userManagementView: 'users', permissionGroups: [], permissionCatalog: {}, selectedUserIds: ['u1'], bulkRole: 'user', can: () => true, filteredUsers: users, usersPagination: pagination(users), ...calls };
  const { rerender } = render(<UsersTab {...props} />);
  fireEvent.change(screen.getByTestId('user-search-input'), { target: { value: 'doc' } });
  fireEvent.click(screen.getByTestId('create-user-btn')); fireEvent.click(screen.getByTestId('export-csv-btn')); fireEvent.click(screen.getByTestId('bulk-apply-btn')); fireEvent.click(screen.getByText('Clear'));
  fireEvent.click(screen.getByTestId('select-all-users')); fireEvent.click(screen.getByTestId('select-user-u1')); fireEvent.click(screen.getByTestId('view-user-u1')); fireEvent.click(screen.getByTestId('impersonate-user-u1'));
  screen.getAllByTestId('select-change').forEach(button => fireEvent.click(button));
  expect(calls.handleViewUser).toHaveBeenCalledWith('u1'); expect(calls.toggleUserSelection).toHaveBeenCalledWith('u1'); expect(screen.getByText('NEUER PARTNER')).toBeInTheDocument();
  rerender(<UsersTab {...props} userManagementView="groups" />); expect(screen.getByText('groups')).toBeInTheDocument();
  rerender(<UsersTab {...props} users={[]} filteredUsers={[]} usersPagination={pagination([])} selectedUserIds={[]} can={() => false} />); expect(screen.getByText('No users found')).toBeInTheDocument();
});

test('steps covers templates, list operations and flow callbacks', async () => {
  const { adminAPI } = require('../../../lib/api');
  const calls = { setEditingStep: fn(), setShowStepDialog: fn(), setShowTemplatesPanel: jest.fn(updater => typeof updater === 'function' ? updater(false) : updater), setStepsView: fn(), loadData: fn(), handleCreateSurvey: fn(), handleSurveyChange: fn(), handleDeleteStep: fn(), handleMoveStep: fn(), handleSaveStepAsTemplate: fn(), handleApplyTemplate: fn(), handleDeleteTemplate: fn() };
  const steps = [{ id: 's1', order: 1, title: 'One', description: 'First', step_type: 'form', is_active: true, fields: [{}], duration_value: 0, email_on_enter: true, email_on_edit: true, email_on_leave: true, conditions: [] }, { id: 's2', order: 2, title: 'Two', description: 'Second', step_type: 'upload', is_active: false, duration_value: 2, duration_unit: 'days', survey_id: 'survey', conditions: [{ source_step_order: 1 }] }];
  const templates = [{ id: 't1', name: 'Template', description: '', config: { step_type: 'form' } }, { id: 't2', name: 'Other', config: {} }];
  const base = { t: x => x, steps, surveys: [{ id: 'survey', name: 'Survey', slug: 'doctors' }], activeSurveyId: 'survey', stepTemplates: templates, showTemplatesPanel: true, stepsView: 'list', sortedSteps: steps, templatesPagination: pagination(templates), stepsPagination: pagination(steps), ...calls };
  const { rerender } = render(<StepsTab {...base} />);
  fireEvent.click(screen.getByTestId('create-survey-btn')); fireEvent.click(screen.getByTestId('toggle-templates-panel-btn')); fireEvent.click(screen.getByTestId('add-step-btn')); fireEvent.click(screen.getByTestId('apply-template-t1')); fireEvent.click(screen.getByTestId('delete-template-t1'));
  fireEvent.click(screen.getByTestId('edit-step-s1')); fireEvent.click(screen.getByTestId('save-template-s1')); fireEvent.click(screen.getByTestId('delete-step-s1')); fireEvent.click(screen.getByTestId('step-move-down-s1')); fireEvent.click(screen.getByTestId('step-move-up-s2'));
  expect(calls.handleMoveStep).toHaveBeenCalledTimes(2); expect(screen.getByText('step_instant')).toBeInTheDocument(); expect(screen.getByText('2 step_days')).toBeInTheDocument();
  rerender(<StepsTab {...base} showTemplatesPanel stepTemplates={[]} templatesPagination={pagination([])} steps={[]} sortedSteps={[]} stepsPagination={pagination([])} />); fireEvent.click(screen.getByTestId('steps-list-empty-add-step-btn'));
  rerender(<StepsTab {...base} stepsView="flow" />);
  mockFlowProps.onEdit(steps[0]); mockFlowProps.onDelete(steps[0]); mockFlowProps.onAddStep(); mockFlowProps.onAddStepWithType('decision');
  await mockFlowProps.onConditionAdd(steps[0], steps[1], { action: 'redirect', operator: 'equals' });
  await mockFlowProps.onConditionUpdate('s2', 0, { action: 'redirect', operator: 'equals' });
  await mockFlowProps.onConditionDelete('s2', 0); await mockFlowProps.onSaveLayout([{ id: 's1' }]);
  await mockFlowProps.onConditionUpdate('missing', 0, {}); await mockFlowProps.onConditionDelete('missing', 0);
  expect(adminAPI.updateStep).toHaveBeenCalledTimes(3); expect(adminAPI.saveStepLayout).toHaveBeenCalled();
  rerender(<StepsTab {...base} stepsView="dependency" />); expect(mockFlowProps.layoutMode).toBe('dependency');
  adminAPI.updateStep.mockRejectedValueOnce(new Error('fail')); await mockFlowProps.onConditionAdd(steps[0], steps[1], { action: 'hide', operator: 'equals' });
  adminAPI.updateStep.mockRejectedValueOnce(new Error('fail')); await mockFlowProps.onConditionUpdate('s2', 0, { action: 'hide', operator: 'equals' });
  adminAPI.updateStep.mockRejectedValueOnce(new Error('fail')); await mockFlowProps.onConditionDelete('s2', 0);
  adminAPI.saveStepLayout.mockRejectedValueOnce(new Error('fail')); await mockFlowProps.onSaveLayout([]);
  const bareTarget = { id: 'bare', order: 3, title: 'Bare' }; await mockFlowProps.onConditionAdd(steps[0], bareTarget, { action: 'hide', operator: 'equals', value: null });
  const sparse = { id: 'sparse', order: 4, title: 'Sparse', conditions: [{}] }; rerender(<StepsTab {...base} steps={[sparse]} sortedSteps={[sparse]} stepsView="flow" />); await mockFlowProps.onConditionUpdate('sparse', 0, { action: 'hide', operator: 'equals', value: null });
  const twoConditions = { ...sparse, conditions: [{}, {}] }; rerender(<StepsTab {...base} steps={[twoConditions]} sortedSteps={[twoConditions]} stepsView="flow" />); await mockFlowProps.onConditionDelete('sparse', 0);
  rerender(<StepsTab {...base} steps={[]} sortedSteps={[]} stepsView="flow" />); mockFlowProps.onAddStepWithType('form');
});
