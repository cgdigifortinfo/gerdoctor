import { act, renderHook, waitFor } from '@testing-library/react';
import { useAdminDashboardController } from './useAdminDashboardController';

let mockUser = { name: 'Admin', permissions: ['*'] };
let mockLocation = { search: '?survey=survey&tab=steps&step=2' };
const mockNavigate = jest.fn(), mockLogout = jest.fn(), mockImpersonate = jest.fn();
let mockUserCommandDeps, mockStepCommandDeps, mockPartnerCommandDeps, mockCmsCommandDeps, mockBillingCommandDeps;
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate, useLocation: () => mockLocation }), { virtual: true });
jest.mock('../../contexts/AuthContext', () => ({ useAuth: () => ({ user: mockUser, logout: mockLogout, impersonate: mockImpersonate }) }));
jest.mock('../../contexts/LanguageContext', () => ({ useLanguage: () => ({ t: x => x }) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

jest.mock('../../lib/api', () => {
  const resolved = data => jest.fn().mockResolvedValue({ data });
  return { adminAPI: { getSurveys: resolved([]), getUsers: resolved([]), getSteps: resolved([]), getPartners: resolved([]), getAnalytics: resolved(null), getCmsContent: resolved({}), getAuditLog: resolved({ logs: [], action_types: [] }), listStepTemplates: resolved([]), getPermissionGroups: resolved([]), getPermissionCatalog: resolved({}), getBilling: resolved({}) }, settingsAPI: { getAdmin: resolved({}) }, formatApiError: () => 'error' };
});
const { adminAPI: mockAdminAPI, settingsAPI: mockSettingsAPI } = require('../../lib/api');

function mockCommand(name) { return { [name]: jest.fn() }; }
jest.mock('./hooks/useAdminUserCommands', () => ({ useAdminUserCommands: deps => { mockUserCommandDeps = deps; return ({ ...mockCommand('handleImpersonate'), ...mockCommand('handleViewUser'), ...mockCommand('handleSaveUserPermissions'), ...mockCommand('handleUpdateUserRole'), ...mockCommand('handleUpdateUserProgress'), ...mockCommand('toggleUserSelection'), ...mockCommand('toggleSelectAll'), ...mockCommand('handleBulkRoleUpdate'), ...mockCommand('handleExportCsv'), ...mockCommand('handleCreateUser') }); } }));
jest.mock('./hooks/useAdminStepCommands', () => ({ useAdminStepCommands: deps => { mockStepCommandDeps = deps; return ({ ...mockCommand('handleSaveStep'), ...mockCommand('handleCreateSurvey'), ...mockCommand('handleSurveyChange'), ...mockCommand('handleDeleteStep'), ...mockCommand('handleMoveStep'), ...mockCommand('handleSaveStepAsTemplate'), ...mockCommand('handleApplyTemplate'), ...mockCommand('handleDeleteTemplate') }); } }));
jest.mock('./hooks/useAdminPartnerCommands', () => ({ useAdminPartnerCommands: deps => { mockPartnerCommandDeps = deps; return ({ ...mockCommand('handleSavePartner'), ...mockCommand('handleDeletePartner'), ...mockCommand('handleLinkUser'), ...mockCommand('handleUnlinkUser') }); } }));
jest.mock('./hooks/useAdminCmsCommands', () => ({ useAdminCmsCommands: deps => { mockCmsCommandDeps = deps; return mockCommand('handleSaveCms'); } }));
jest.mock('./hooks/useAdminBillingCommands', () => ({ useAdminBillingCommands: deps => { mockBillingCommandDeps = deps; return ({ ...mockCommand('handleSaveSettings'), ...mockCommand('auditStripeConnections'), ...mockCommand('repairStripeConnection'), ...mockCommand('repairAllStripeConnections') }); } }));

beforeEach(() => {
  jest.clearAllMocks(); mockUser = { name: 'Admin', permissions: ['*'] }; mockLocation = { search: '?survey=survey&tab=steps&step=2' };
  window.requestAnimationFrame = cb => cb(); document.querySelector = jest.fn(() => ({ scrollIntoView: jest.fn() }));
  Object.values(mockAdminAPI).forEach(mock => mock.mockClear?.());
  mockAdminAPI.getSurveys.mockResolvedValue({ data: [{ id: 'survey', slug: 'survey', is_default: true }] }); mockAdminAPI.getUsers.mockResolvedValue({ data: [{ id: 'u' }] }); mockAdminAPI.getSteps.mockResolvedValue({ data: [{ id: 's2', order: 2 }] }); mockAdminAPI.getPartners.mockResolvedValue({ data: [{ id: 'p' }] }); mockAdminAPI.getAnalytics.mockResolvedValue({ data: { step_analytics: [{ step_id: 's' }] } }); mockAdminAPI.getAuditLog.mockResolvedValue({ data: { logs: [{ id: 'a' }], action_types: ['role_change'] } }); mockAdminAPI.listStepTemplates.mockResolvedValue({ data: [{ id: 't' }] }); mockAdminAPI.getPermissionGroups.mockResolvedValue({ data: [{ id: 'g' }] }); mockAdminAPI.getPermissionCatalog.mockResolvedValue({ data: { categories: [], all_permissions: [] } }); mockAdminAPI.getBilling.mockResolvedValue({ data: { partners: [], totals: {} } });
  mockAdminAPI.getCmsContent.mockImplementation(section => Promise.resolve({ data: { content: section === 'landing_pages' ? { pages: [] } : { section }, translations: { en: {} } } })); mockSettingsAPI.getAdmin.mockResolvedValue({ data: { site_title: 'Site' } });
});

test('controller exposes its integration contract', async () => {
  const { result, rerender } = renderHook(() => useAdminDashboardController());
  expect(result.current.auditLogs).toEqual([]); expect(result.current.auditActionTypes).toEqual([]); expect(result.current.auditFilter).toBe(''); expect(result.current.auditDateFrom).toBe(''); expect(result.current.auditDateTo).toBe('');
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current).toEqual(expect.objectContaining({
    loadData: expect.any(Function), handleSaveStep: expect.any(Function), stepsPagination: expect.any(Object),
  }));
  act(() => { mockUser = { permissions: [] }; rerender(); }); expect(result.current.can('anything')).toBe(false);
  await waitFor(() => expect(result.current.loading).toBe(false));
});

test('controller loads steps when a survey id matches the ref mutation sentinel', async () => {
  mockUser = { permissions: ['surveys.view', 'steps.view'] }; mockLocation = { search: '?survey=Stryker%20was%20here!' };
  mockAdminAPI.getSurveys.mockResolvedValue({ data: [{ id: 'Stryker was here!' }] });
  const { result } = renderHook(() => useAdminDashboardController());
  await waitFor(() => expect(result.current.loading).toBe(false));
  await waitFor(() => expect(mockAdminAPI.getSteps).toHaveBeenCalledWith('Stryker was here!'));
});

test('controller loads all permitted data, filters audit and logs out', async () => {
  const { result } = renderHook(() => useAdminDashboardController());
  await waitFor(() => expect(result.current.users).toEqual([{ id: 'u' }]));
  expect(mockStepCommandDeps).toEqual(expect.objectContaining({ activeSurveyId: 'survey', steps: [{ id: 's2', order: 2 }], navigate: mockNavigate }));
  expect(mockUserCommandDeps).toEqual(expect.objectContaining({ impersonate: mockImpersonate, navigate: mockNavigate }));
  expect(mockPartnerCommandDeps).toEqual(expect.objectContaining({ loadData: expect.any(Function), setConfirmDialog: expect.any(Function) }));
  expect(mockCmsCommandDeps).toEqual(expect.objectContaining({ setCmsSaving: expect.any(Function), loadData: expect.any(Function) }));
  expect(mockBillingCommandDeps).toEqual(expect.objectContaining({ siteSettings: expect.objectContaining({ site_title: 'Site' }), loadData: expect.any(Function) }));
  expect(result.current.loading).toBe(false); expect(result.current.can('anything')).toBe(true); expect(result.current.activeTab).toBe('steps');
  expect(result.current.adminBilling).toEqual({ partners: [], totals: {} });
  expect(result.current.auditActionTypes).toEqual(['role_change']); expect(result.current.stepTemplates).toEqual([{ id: 't' }]); expect(result.current.permissionGroups).toEqual([{ id: 'g' }]); expect(result.current.permissionCatalog).toEqual({ categories: [], all_permissions: [] });
  expect(result.current.cmsPartners).toEqual({ section: 'partners' }); expect(result.current.cmsPartnersTrans).toEqual({ en: {} }); expect(result.current.cmsLandingPages).toEqual({ pages: [] }); expect(result.current.cmsLandingPagesTrans).toEqual({ en: {} });
  mockAdminAPI.getPermissionGroups.mockResolvedValueOnce({ data: [{ id: 'reloaded' }] }); mockAdminAPI.getPermissionCatalog.mockResolvedValueOnce({ data: { all_permissions: ['fresh'] } });
  await act(() => result.current.loadPermissionData()); expect(mockAdminAPI.getPermissionGroups).toHaveBeenCalled(); expect(result.current.permissionGroups).toEqual([{ id: 'reloaded' }]); expect(result.current.permissionCatalog).toEqual({ all_permissions: ['fresh'] });
  act(() => { result.current.setAuditFilter('all'); result.current.setAuditDateFrom('2026-01-01'); result.current.setAuditDateTo('2026-01-02'); });
  await act(() => result.current.handleAuditFilter());
  expect(mockAdminAPI.getAuditLog).toHaveBeenLastCalledWith(0, 0, '', '2026-01-01', '2026-01-02');
  expect(result.current.auditLogs).toEqual([{ id: 'a' }]);
  await act(() => result.current.handleClearAuditFilter());
  expect(mockAdminAPI.getAuditLog).toHaveBeenLastCalledWith(0, 0); expect(result.current.auditFilter).toBe(''); expect(result.current.auditDateFrom).toBe(''); expect(result.current.auditDateTo).toBe('');
  mockAdminAPI.getSteps.mockResolvedValueOnce({ data: [{ id: 'other', order: 3 }] }); act(() => result.current.setActiveSurveyId('other')); await waitFor(() => expect(result.current.steps).toEqual([{ id: 'other', order: 3 }]));
  mockAdminAPI.getSteps.mockRejectedValueOnce(new Error('steps')); act(() => result.current.setActiveSurveyId('broken')); await waitFor(() => expect(require('sonner').toast.error).toHaveBeenCalledWith('Failed to load steps'));
  await act(() => result.current.handleLogout()); expect(mockLogout).toHaveBeenCalled(); expect(mockNavigate).toHaveBeenCalledWith('/');
});

test('controller handles restricted user, groups fallback and API errors', async () => {
  mockUser = { permissions: ['groups.view'] }; mockLocation = { search: '?tab=forbidden' };
  mockAdminAPI.getCmsContent.mockRejectedValueOnce(new Error('load'));
  const { result } = renderHook(() => useAdminDashboardController());
  await waitFor(() => expect(result.current.loading).toBe(false)); expect(result.current.can('users.view')).toBe(false); expect(result.current.userManagementView).toBe('groups'); expect(result.current.activeTab).toBe('users'); expect(require('sonner').toast.error).toHaveBeenCalledWith('Failed to load data');
  mockAdminAPI.getAuditLog.mockRejectedValueOnce(new Error('audit')); await act(() => result.current.handleAuditFilter());
  expect(require('sonner').toast.error).toHaveBeenCalledWith('Failed to load audit logs');
  mockAdminAPI.getAuditLog.mockRejectedValueOnce(new Error('clear')); await act(() => result.current.handleClearAuditFilter());
});

test('empty permission never authorizes step loading', async () => {
  mockUser = { permissions: ['', 'surveys.view'] }; mockLocation = { search: '?survey=survey' };
  const { result } = renderHook(() => useAdminDashboardController());
  await waitFor(() => expect(result.current.loading).toBe(false));
  await waitFor(() => expect(result.current.activeSurveyId).toBe('survey'));
  act(() => result.current.setActiveSurveyId('other'));
  await new Promise(resolve => setTimeout(resolve, 0));
  expect(mockAdminAPI.getSteps).not.toHaveBeenCalled();
});

test('controller supports absent user and empty/fallback response payloads', async () => {
  mockUser = null; mockLocation = { search: '' };
  mockAdminAPI.getCmsContent.mockImplementation(() => Promise.resolve({ data: {} }));
  const { result } = renderHook(() => useAdminDashboardController());
  await waitFor(() => expect(result.current.loading).toBe(false)); expect(result.current.can('x')).toBe(false); expect(result.current.analyticsSteps).toEqual([]); expect(result.current.surveys).toEqual([]); expect(result.current.cmsPartners).toEqual({}); expect(result.current.cmsPartnersTrans).toEqual({}); expect(result.current.cmsLandingPages).toEqual({ pages: [] }); expect(result.current.cmsLandingPagesTrans).toEqual({});
});

test.each([
  ['default', [{ id: 'default', is_default: true }, { id: 'second' }], 'default'],
  ['first', [{ id: 'first' }, { id: 'second' }], 'first'],
  ['empty', [], ''],
])('controller selects %s survey fallback', async (_name, surveys, expected) => {
  mockUser = { permissions: ['surveys.view'] }; mockLocation = { search: '?survey=missing' }; mockAdminAPI.getSurveys.mockResolvedValue({ data: surveys });
  const { result } = renderHook(() => useAdminDashboardController()); await waitFor(() => expect(result.current.loading).toBe(false)); expect(result.current.activeSurveyId).toBe(expected);
});

test('controller moves pagination to the deep-linked step page', async () => {
  const steps = Array.from({ length: 15 }, (_, i) => ({ id: `s${i + 1}`, order: i + 1 })); mockAdminAPI.getSteps.mockResolvedValue({ data: steps }); mockLocation = { search: '?survey=survey&tab=steps&step=15' };
  const { result } = renderHook(() => useAdminDashboardController()); await waitFor(() => expect(result.current.steps).toHaveLength(15)); await waitFor(() => expect(result.current.stepsPagination.page).toBe(2));
});

test('controller scrolls to a deep-linked step while all rows are visible', async () => {
  const { result } = renderHook(() => useAdminDashboardController());
  await waitFor(() => expect(result.current.steps).toEqual([{ id: 's2', order: 2 }]));
  act(() => result.current.stepsPagination.setPageSize('all'));
  await waitFor(() => expect(result.current.stepsPagination.isAll).toBe(true));
  expect(document.querySelector).toHaveBeenCalledWith('[data-testid="step-row-order-2"]');
});

test('controller uses every recoverable API fallback', async () => {
  mockAdminAPI.getSurveys.mockRejectedValueOnce(new Error('surveys')); mockSettingsAPI.getAdmin.mockRejectedValueOnce(new Error('settings')); mockAdminAPI.listStepTemplates.mockRejectedValueOnce(new Error('templates')); mockAdminAPI.getPermissionGroups.mockRejectedValueOnce(new Error('groups')); mockAdminAPI.getPermissionCatalog.mockRejectedValueOnce(new Error('catalog')); mockAdminAPI.getBilling.mockRejectedValueOnce(new Error('billing'));
  const { result } = renderHook(() => useAdminDashboardController()); await waitFor(() => expect(result.current.loading).toBe(false)); expect(result.current.surveys).toEqual([]); expect(result.current.siteSettings).toEqual(expect.objectContaining({ site_title: '', primary_color: '' }));
});

test('controller ignores stale successful and failed load requests', async () => {
  const { result } = renderHook(() => useAdminDashboardController()); await waitFor(() => expect(result.current.loading).toBe(false));
  let resolveOld; const old = new Promise(resolve => { resolveOld = resolve; }); mockAdminAPI.getUsers.mockImplementationOnce(() => old).mockResolvedValueOnce({ data: [{ id: 'new' }] });
  let first, second; act(() => { first = result.current.loadData(); second = result.current.loadData(); }); await act(() => second); await act(async () => { resolveOld({ data: [{ id: 'old' }] }); await first; }); expect(result.current.users).toEqual([{ id: 'new' }]);
  require('sonner').toast.error.mockClear(); let rejectOld; const failed = new Promise((_resolve, reject) => { rejectOld = reject; }); mockAdminAPI.getUsers.mockImplementationOnce(() => failed).mockResolvedValueOnce({ data: [{ id: 'latest' }] });
  let staleFailure, latest; act(() => { staleFailure = result.current.loadData(); latest = result.current.loadData(); }); await act(() => latest); await act(async () => { rejectOld(new Error('old failure')); await staleFailure; }); expect(result.current.users).toEqual([{ id: 'latest' }]); expect(require('sonner').toast.error).not.toHaveBeenCalledWith('Failed to load data');
});

test('controller ignores a stale top-level failure without finishing the current request', async () => {
  const { result } = renderHook(() => useAdminDashboardController()); await waitFor(() => expect(result.current.loading).toBe(false));
  let rejectOld;
  mockAdminAPI.getCmsContent
    .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOld = reject; }))
    .mockImplementation(section => Promise.resolve({ data: { content: { section }, translations: {} } }));
  let stale; let current;
  act(() => { stale = result.current.loadData(); current = result.current.loadData(); });
  await act(() => current);
  require('sonner').toast.error.mockClear();
  await act(async () => { rejectOld(new Error('stale top-level failure')); await stale; });
  expect(require('sonner').toast.error).not.toHaveBeenCalledWith('Failed to load data');
  expect(result.current.loading).toBe(false);
});

test('controller ignores stale step responses after the active survey changes', async () => {
  const { result } = renderHook(() => useAdminDashboardController());
  await waitFor(() => expect(result.current.loading).toBe(false));

  let resolveOld;
  mockAdminAPI.getSteps
    .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce({ data: [{ id: 'fresh', order: 1 }] });
  act(() => result.current.setActiveSurveyId('old-survey'));
  await waitFor(() => expect(mockAdminAPI.getSteps).toHaveBeenCalledWith('old-survey'));
  act(() => result.current.setActiveSurveyId('new-survey'));
  await waitFor(() => expect(result.current.steps).toEqual([{ id: 'fresh', order: 1 }]));
  await act(async () => resolveOld({ data: [{ id: 'stale', order: 1 }] }));
  expect(result.current.steps).toEqual([{ id: 'fresh', order: 1 }]);

  let rejectOld;
  mockAdminAPI.getSteps
    .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOld = reject; }))
    .mockResolvedValueOnce({ data: [{ id: 'latest', order: 1 }] });
  act(() => result.current.setActiveSurveyId('failing-survey'));
  await waitFor(() => expect(mockAdminAPI.getSteps).toHaveBeenCalledWith('failing-survey'));
  act(() => result.current.setActiveSurveyId('latest-survey'));
  await waitFor(() => expect(result.current.steps).toEqual([{ id: 'latest', order: 1 }]));
  await act(async () => rejectOld(new Error('stale failure')));
  expect(result.current.steps).toEqual([{ id: 'latest', order: 1 }]);
});

test('controller normalizes missing optional response collections', async () => {
  mockAdminAPI.getSurveys.mockResolvedValue({ data: undefined }); mockAdminAPI.getAuditLog.mockResolvedValue({ data: {} }); mockAdminAPI.listStepTemplates.mockResolvedValue({ data: undefined }); mockAdminAPI.getPermissionGroups.mockResolvedValue({ data: undefined }); mockAdminAPI.getPermissionCatalog.mockResolvedValue({ data: undefined }); mockAdminAPI.getBilling.mockResolvedValue({ data: undefined }); mockSettingsAPI.getAdmin.mockResolvedValue({ data: null });
  const { result } = renderHook(() => useAdminDashboardController()); await waitFor(() => expect(result.current.loading).toBe(false)); expect(result.current.auditLogs).toEqual([]); expect(result.current.auditActionTypes).toEqual([]); expect(result.current.stepTemplates).toEqual([]); expect(result.current.permissionGroups).toEqual([]); expect(result.current.permissionCatalog).toEqual({ categories: [], all_permissions: [] }); expect(result.current.adminBilling).toEqual({ partners: [], totals: {} }); expect(result.current.siteSettings).toEqual(expect.objectContaining({ site_title: '', primary_color: '' }));
  mockAdminAPI.getPermissionGroups.mockResolvedValueOnce({ data: undefined }); mockAdminAPI.getPermissionCatalog.mockResolvedValueOnce({ data: undefined }); await act(() => result.current.loadPermissionData());
  mockAdminAPI.getAuditLog.mockResolvedValueOnce({ data: {} }); await act(() => result.current.handleAuditFilter()); mockAdminAPI.getAuditLog.mockResolvedValueOnce({ data: {} }); await act(() => result.current.handleClearAuditFilter());
  mockAdminAPI.getSteps.mockResolvedValueOnce({ data: undefined }); act(() => result.current.setActiveSurveyId('empty-steps')); await waitFor(() => expect(mockAdminAPI.getSteps).toHaveBeenCalledWith('empty-steps'));
});
