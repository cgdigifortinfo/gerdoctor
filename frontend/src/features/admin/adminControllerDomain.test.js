import { ADMIN_ANALYTICS_PAGINATION_KEY, ADMIN_AUDIT_PAGINATION_KEY, DEFAULT_SITE_SETTINGS, adminLoadRequests, adminRouteState, allowedAdminTabs, applyAdminRouteState, applyAllowedAdminTab, applyPreferredUserManagementView, applyStepDeepLinkCommand, auditFilterArguments, auditPaginationOptions, billingPayload, buildAdminControllerResult, clearAuditFilters, finishedLoadingState, hasAdminPermission, isCurrentRequest, loadFilteredAudit, loadSurveyList, nextRequestId, normalizeAdminLoadPayload, normalizeAuditData, permissionCollections, preferredUserManagementView, selectedSurveyState, selectSurveyId, shouldLoadSurveySteps, startSurveyStepsRequest, stepDeepLinkCommand } from './adminControllerDomain';

test('survey request orchestration accepts only new authorized survey loads', () => {
  expect(shouldLoadSurveySteps('survey', true, '')).toBe(true);
  expect(shouldLoadSurveySteps('', true, '')).toBe(false);
  expect(shouldLoadSurveySteps('survey', false, '')).toBe(false);
  expect(shouldLoadSurveySteps('survey', true, 'survey')).toBe(false);
  expect(nextRequestId(0)).toBe(1);
  expect(nextRequestId(7)).toBe(8);
  expect(selectedSurveyState('current', 'selected')).toBe('selected');
  expect(selectedSurveyState('current', 'current')).toBe('current');
  expect(selectedSurveyState('current', '')).toBe('current');
  expect(selectedSurveyState('', '')).toBe('');
  expect(finishedLoadingState()).toBe(false);
});

test('permissions, survey selection and request currency have explicit outcomes', () => {
  expect(hasAdminPermission(null, 'users.view')).toBe(false);
  expect(hasAdminPermission({}, 'users.view')).toBe(false);
  expect(hasAdminPermission({}, 'Stryker was here')).toBe(false);
  expect(hasAdminPermission({ permissions: ['*'] }, 'users.view')).toBe(true);
  expect(hasAdminPermission({ permissions: ['users.view'] }, 'users.view')).toBe(true);
  expect(hasAdminPermission({ permissions: ['other'] }, 'users.view')).toBe(false);
  const surveys = [{ id: 'first', slug: 'one' }, { id: 'default', slug: 'main', is_default: true }, { id: 'slug-target', slug: 'special' }];
  expect(selectSurveyId(surveys, '?survey=first')).toBe('first');
  expect(selectSurveyId(surveys, '?survey=main')).toBe('default');
  expect(selectSurveyId(surveys, '?survey=special')).toBe('slug-target');
  expect(selectSurveyId(surveys, '?survey=missing')).toBe('default');
  expect(selectSurveyId([{ id: 'Stryker was here!' }, { id: 'default', is_default: true }], '')).toBe('default');
  expect(selectSurveyId([{ id: 'first' }], '')).toBe('first');
  expect(selectSurveyId([], '')).toBe('');
  expect(isCurrentRequest(2, 2)).toBe(true);
  expect(isCurrentRequest(2, 3)).toBe(false);
});

test('survey loading handles authorization, missing data and failures', async () => {
  const api = { getSurveys: jest.fn().mockResolvedValue({ data: [{ id: 'survey' }] }) };
  await expect(loadSurveyList(true, api)).resolves.toEqual([{ id: 'survey' }]);
  api.getSurveys.mockResolvedValueOnce({}); await expect(loadSurveyList(true, api)).resolves.toEqual([]);
  api.getSurveys.mockRejectedValueOnce(new Error('failed')); await expect(loadSurveyList(true, api)).resolves.toEqual([]);
  api.getSurveys.mockClear(); await expect(loadSurveyList(false, api)).resolves.toEqual([]); expect(api.getSurveys).not.toHaveBeenCalled();
});

test('audit orchestration normalizes filters, responses, clearing and failures', async () => {
  expect(auditFilterArguments('all', 'from', 'to')).toEqual([0, 0, '', 'from', 'to']);
  expect(auditFilterArguments('login', '', '')).toEqual([0, 0, 'login', '', '']);
  expect(normalizeAuditData({ logs: [1], action_types: ['login'] })).toEqual({ logs: [1], actionTypes: ['login'] });
  expect(normalizeAuditData({})).toEqual({ logs: [], actionTypes: [] });
  const api = { getAuditLog: jest.fn().mockResolvedValue({ data: { logs: [1], action_types: ['login'] } }) };
  const setLogs = jest.fn(); const setActionTypes = jest.fn(); const onError = jest.fn();
  await expect(loadFilteredAudit({ api, filter: 'all', dateFrom: 'from', dateTo: 'to', setLogs, setActionTypes, onError })).resolves.toBe(true);
  expect(api.getAuditLog).toHaveBeenCalledWith(0, 0, '', 'from', 'to'); expect(setLogs).toHaveBeenCalledWith([1]); expect(setActionTypes).toHaveBeenCalledWith(['login']); expect(onError).not.toHaveBeenCalled();
  api.getAuditLog.mockRejectedValueOnce(new Error('failed'));
  await expect(loadFilteredAudit({ api, filter: 'login', dateFrom: '', dateTo: '', setLogs, setActionTypes, onError })).resolves.toBe(false); expect(onError).toHaveBeenCalledTimes(1);
  const setFilter = jest.fn(); const setDateFrom = jest.fn(); const setDateTo = jest.fn(); api.getAuditLog.mockResolvedValueOnce({ data: {} }); setLogs.mockClear();
  await expect(clearAuditFilters({ api, setFilter, setDateFrom, setDateTo, setLogs })).resolves.toBe(true);
  expect(setFilter).toHaveBeenCalledWith(''); expect(setDateFrom).toHaveBeenCalledWith(''); expect(setDateTo).toHaveBeenCalledWith(''); expect(api.getAuditLog).toHaveBeenLastCalledWith(0, 0); expect(setLogs).toHaveBeenCalledWith([]);
  api.getAuditLog.mockRejectedValueOnce(new Error('failed'));
  await expect(clearAuditFilters({ api, setFilter, setDateFrom, setDateTo, setLogs })).resolves.toBe(false);
});

test('survey step requests apply only current responses and current errors', async () => {
  let current = 3; let loaded = ''; const setSteps = jest.fn(); const onError = jest.fn();
  const deps = overrides => ({ activeSurveyId: 'survey', canViewSteps: true, loadedSurveyId: loaded, currentRequestId: current, setRequestId: id => { current = id; }, getCurrentRequestId: () => current, requestSteps: jest.fn().mockResolvedValue({ data: [{ id: 'step' }] }), setSteps, setLoadedSurveyId: id => { loaded = id; }, onError, ...overrides });
  expect(startSurveyStepsRequest(deps({ activeSurveyId: '' }))).toBeNull();
  expect(startSurveyStepsRequest(deps({ canViewSteps: false }))).toBeNull();
  expect(startSurveyStepsRequest(deps({ loadedSurveyId: 'survey' }))).toBeNull();
  expect(startSurveyStepsRequest(deps({}))).toBe(4); await Promise.resolve();
  expect(setSteps).toHaveBeenCalledWith([{ id: 'step' }]); expect(loaded).toBe('survey');
  loaded = ''; setSteps.mockClear();
  let resolveStale; const staleRequest = new Promise(resolve => { resolveStale = resolve; });
  startSurveyStepsRequest(deps({ requestSteps: jest.fn(() => staleRequest) })); current += 1; resolveStale({ data: [{ id: 'stale' }] }); await Promise.resolve(); expect(setSteps).not.toHaveBeenCalled();
  current = 10; startSurveyStepsRequest(deps({ requestSteps: jest.fn().mockResolvedValue({ data: undefined }) })); await Promise.resolve(); expect(setSteps).toHaveBeenCalledWith([]);
  loaded = ''; onError.mockClear(); current = 20; startSurveyStepsRequest(deps({ requestSteps: jest.fn().mockRejectedValue(new Error('current')) })); await Promise.resolve(); await Promise.resolve(); expect(onError).toHaveBeenCalledTimes(1);
  loaded = ''; onError.mockClear(); current = 30; startSurveyStepsRequest(deps({ requestSteps: jest.fn().mockRejectedValue(new Error('stale')), setRequestId: id => { current = id + 1; } })); await Promise.resolve(); await Promise.resolve(); expect(onError).not.toHaveBeenCalled();
});

test('route and permission orchestration is explicit', () => {
  expect(adminRouteState('?tab=steps&step=2')).toEqual({ tab: 'steps', hasStep: true });
  expect(adminRouteState('?tab=&step=')).toEqual({ tab: '', hasStep: false });
  const permissions = new Set(['groups.view', 'surveys.view', 'partners.view', 'cms.view', 'messages.view', 'audit.view', 'settings.view']);
  expect(allowedAdminTabs(permission => permissions.has(permission))).toEqual(['users', 'steps', 'partners', 'cms', 'email-templates', 'events', 'audit', 'settings']);
  expect(allowedAdminTabs(() => false)).toEqual([]);
  expect(allowedAdminTabs(permission => permission === 'analytics.view')).toEqual(['analytics']);
  expect(allowedAdminTabs(permission => permission === 'users.view')).toEqual(['users']);
  expect(allowedAdminTabs(permission => permission === 'steps.view')).toEqual(['steps']);
  expect(preferredUserManagementView(permission => permission === 'groups.view')).toBe('groups');
  expect(preferredUserManagementView(permission => permission === 'users.view')).toBeNull();
  expect(preferredUserManagementView(permission => ['users.view', 'groups.view'].includes(permission))).toBeNull();
  expect(preferredUserManagementView(() => false)).toBeNull();
  expect(ADMIN_ANALYTICS_PAGINATION_KEY).toBe('admin-analytics-steps');
  expect(ADMIN_AUDIT_PAGINATION_KEY).toBe('admin-audit');
  expect(auditPaginationOptions('role', '2026-01-01', '2026-01-02')).toEqual({ resetKey: 'role|2026-01-01|2026-01-02' });
  expect(auditPaginationOptions('', '', '')).toEqual({ resetKey: '||' });
  expect(permissionCollections([{ id: 'group' }], { all_permissions: ['x'] })).toEqual({ groups: [{ id: 'group' }], catalog: { all_permissions: ['x'] } });
  expect(permissionCollections(undefined, undefined)).toEqual({ groups: [], catalog: { categories: [], all_permissions: [] } });
  expect(billingPayload({ partners: [{ id: 'p' }], totals: { cents: 1 } })).toEqual({ partners: [{ id: 'p' }], totals: { cents: 1 } });
  expect(billingPayload(undefined)).toEqual({ partners: [], totals: {} });
  const setTab = jest.fn(); const setView = jest.fn();
  applyAdminRouteState({ tab: 'steps', hasStep: true }, setTab, setView);
  expect(setTab).toHaveBeenCalledWith('steps'); expect(setView).toHaveBeenCalledWith('list');
  setTab.mockClear(); setView.mockClear(); applyAdminRouteState({ tab: null, hasStep: false }, setTab, setView);
  expect(setTab).not.toHaveBeenCalled(); expect(setView).not.toHaveBeenCalled();
  applyAllowedAdminTab(['users'], 'steps', setTab); expect(setTab).toHaveBeenCalledWith('users');
  setTab.mockClear(); applyAllowedAdminTab([], 'steps', setTab); applyAllowedAdminTab(['steps'], 'steps', setTab); expect(setTab).not.toHaveBeenCalled();
  applyPreferredUserManagementView('groups', setView); expect(setView).toHaveBeenCalledWith('groups');
  setView.mockClear(); applyPreferredUserManagementView(null, setView); expect(setView).not.toHaveBeenCalled();
});

test('deep-link orchestration covers guards, pagination and scrolling', () => {
  const base = { search: '?step=15', activeTab: 'steps', stepsView: 'list', sortedSteps: Array.from({ length: 15 }, (_, index) => ({ order: index + 1 })), showAllSteps: false, pageSize: 10, page: 1 };
  expect(stepDeepLinkCommand(base)).toEqual({ type: 'page', page: 2 });
  expect(stepDeepLinkCommand({ ...base, page: 2 })).toEqual({ type: 'scroll', selector: '[data-testid="step-row-order-15"]', options: { block: 'start' } });
  expect(stepDeepLinkCommand({ ...base, showAllSteps: true })).toEqual({ type: 'scroll', selector: '[data-testid="step-row-order-15"]', options: { block: 'start' } });
  expect(stepDeepLinkCommand({ ...base, search: '' })).toBeNull();
  expect(stepDeepLinkCommand({ ...base, activeTab: 'users' })).toBeNull();
  expect(stepDeepLinkCommand({ ...base, stepsView: 'flow' })).toBeNull();
  expect(stepDeepLinkCommand({ ...base, sortedSteps: [] })).toBeNull();
  expect(stepDeepLinkCommand({ ...base, search: '?step=99' })).toBeNull();
  expect(stepDeepLinkCommand({ ...base, pageSize: '5', page: 1 })).toEqual({ type: 'page', page: 3 });
  expect(stepDeepLinkCommand({ ...base, search: '?step=1' })).toEqual({ type: 'scroll', selector: '[data-testid="step-row-order-1"]', options: { block: 'start' } });
  const setPage = jest.fn(); const schedule = jest.fn(callback => callback()); const element = { scrollIntoView: jest.fn() }; const query = jest.fn(() => element);
  applyStepDeepLinkCommand(null, setPage, schedule, query); expect(setPage).not.toHaveBeenCalled(); expect(schedule).not.toHaveBeenCalled();
  applyStepDeepLinkCommand({ type: 'page', page: 4 }, setPage, schedule, query); expect(setPage).toHaveBeenCalledWith(4); expect(schedule).not.toHaveBeenCalled();
  applyStepDeepLinkCommand({ type: 'scroll', selector: '#step', options: { block: 'start' } }, setPage, schedule, query);
  expect(query).toHaveBeenCalledWith('#step'); expect(element.scrollIntoView).toHaveBeenCalledWith({ block: 'start' });
  query.mockReturnValueOnce(null); applyStepDeepLinkCommand({ type: 'scroll', selector: '#missing', options: {} }, setPage, schedule, query); expect(query).toHaveBeenCalledWith('#missing');
});

test('controller result builder combines state and commands with command precedence', () => {
  const state = { users: [], handleSaveStep: 'stale' };
  const command = jest.fn();
  const result = buildAdminControllerResult(state, { handleSaveStep: command });
  expect(result).toEqual({ users: [], handleSaveStep: command });
  expect(result).not.toBe(state);
});

test('admin load payload normalization preserves data and supplies every fallback', () => {
  const populated = normalizeAdminLoadPayload({ users: [{ id: 'u' }], steps: [1], partners: [{ id: 'p' }], analytics: { total: 1 }, home: { content: { h: 1 }, translations: { en: 1 } }, about: { content: { a: 1 }, translations: { en: 2 } }, partnersContent: { content: { p: 1 }, translations: { en: 3 } }, landingPages: { content: { pages: [1] }, translations: { en: 4 } }, audit: { logs: [1], action_types: ['x'] }, settings: { title: 'x' }, templates: [1], groups: [2], permissionCatalog: { all_permissions: ['x'] }, billing: { partners: [3], totals: { cents: 4 } } });
  expect(populated).toEqual(expect.objectContaining({ users: [{ id: 'u' }], steps: [1], partners: [{ id: 'p' }], analytics: { step_analytics: [], total: 1 }, settings: expect.objectContaining({ title: 'x', site_title: '' }) }));
  expect(normalizeAdminLoadPayload({ home: {}, about: {}, partnersContent: {}, landingPages: {}, audit: {} })).toEqual({ users: [], steps: [], partners: [], analytics: { step_analytics: [] }, cmsHome: {}, cmsHomeTranslations: {}, cmsAbout: {}, cmsAboutTranslations: {}, cmsPartners: {}, cmsPartnersTranslations: {}, cmsLandingPages: { pages: [] }, cmsLandingPagesTranslations: {}, auditLogs: [], auditActionTypes: [], settings: DEFAULT_SITE_SETTINGS, templates: [], groups: [], permissionCatalog: { categories: [], all_permissions: [] }, billing: { partners: [], totals: {} } });
});

test('admin request matrix enforces permissions, arguments and recoverable fallbacks', async () => {
  const call = value => jest.fn().mockResolvedValue({ data: value });
  const adminApi = { getUsers: call('users'), getSteps: call('steps'), getPartners: call('partners'), getAnalytics: call('analytics'), getCmsContent: call('cms'), getAuditLog: call('audit'), listStepTemplates: call('templates'), getPermissionGroups: call('groups'), getPermissionCatalog: call('catalog'), getBilling: call('billing') };
  const settingsApi = { getAdmin: call('settings') };
  const allowed = new Set(['users.view', 'steps.view', 'partners.view', 'analytics.view', 'audit.view', 'settings.view', 'groups.view']);
  const results = await Promise.all(adminLoadRequests(permission => allowed.has(permission), adminApi, settingsApi, 'survey'));
  expect(results.map(result => result.data)).toEqual(['users', 'steps', 'partners', 'analytics', 'cms', 'cms', 'cms', 'cms', 'audit', 'settings', 'templates', 'groups', 'catalog', 'billing']);
  expect(adminApi.getSteps).toHaveBeenCalledWith('survey'); expect(adminApi.getAuditLog).toHaveBeenCalledWith(0); expect(adminApi.getCmsContent.mock.calls.map(callArgs => callArgs[0])).toEqual(['home', 'about', 'partners', 'landing_pages']);
  Object.values(adminApi).forEach(mock => mock.mockClear()); settingsApi.getAdmin.mockClear();
  const denied = await Promise.all(adminLoadRequests(() => false, adminApi, settingsApi, 'denied'));
  expect(denied.map(result => result.data)).toEqual([[], [], [], null, 'cms', 'cms', 'cms', 'cms', { logs: [], action_types: [] }, {}, [], [], { categories: [], all_permissions: [] }, { partners: [], totals: {} }]);
  expect(adminApi.getUsers).not.toHaveBeenCalled(); expect(adminApi.getSteps).not.toHaveBeenCalled(); expect(settingsApi.getAdmin).not.toHaveBeenCalled();
  const failingAdmin = { ...adminApi, getUsers: jest.fn().mockRejectedValue(new Error('x')), getSteps: jest.fn().mockRejectedValue(new Error('x')), getPartners: jest.fn().mockRejectedValue(new Error('x')), getAnalytics: jest.fn().mockRejectedValue(new Error('x')), getAuditLog: jest.fn().mockRejectedValue(new Error('x')), listStepTemplates: jest.fn().mockRejectedValue(new Error('x')), getPermissionGroups: jest.fn().mockRejectedValue(new Error('x')), getPermissionCatalog: jest.fn().mockRejectedValue(new Error('x')), getBilling: jest.fn().mockRejectedValue(new Error('x')) };
  settingsApi.getAdmin.mockRejectedValueOnce(new Error('x'));
  const recovered = await Promise.all(adminLoadRequests(() => true, failingAdmin, settingsApi, 'survey'));
  expect(recovered.map(result => result.data)).toEqual([[], [], [], null, 'cms', 'cms', 'cms', 'cms', { logs: [], action_types: [] }, {}, [], [], { categories: [], all_permissions: [] }, { partners: [], totals: {} }]);
});
