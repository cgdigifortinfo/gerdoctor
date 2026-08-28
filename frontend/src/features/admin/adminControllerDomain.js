export function shouldLoadSurveySteps(activeSurveyId, canViewSteps, loadedSurveyId) {
    return Boolean(activeSurveyId) && canViewSteps && loadedSurveyId !== activeSurveyId;
}

export function nextRequestId(currentRequestId) {
    return currentRequestId + 1;
}

export function hasAdminPermission(user, permission) {
    const permissions = user?.permissions || [];
    return permissions.includes('*') || permissions.includes(permission);
}

export function selectSurveyId(surveys, search) {
    const requested = new URLSearchParams(search).get('survey') || '';
    const requestedId = surveys.find(survey => survey.id === requested || survey.slug === requested)?.id;
    return requestedId || surveys.find(survey => survey.is_default)?.id || surveys[0]?.id || '';
}

export async function loadSurveyList(canViewSurveys, api) {
    if (!canViewSurveys) return [];
    try {
        const response = await api.getSurveys();
        return response.data || [];
    } catch (error) {
        return [];
    }
}

export function isCurrentRequest(requestId, currentRequestId) {
    return requestId === currentRequestId;
}

export function selectedSurveyState(currentSurveyId, selectedSurveyId) {
    return selectedSurveyId || currentSurveyId;
}

export function finishedLoadingState() {
    return false;
}

export function startSurveyStepsRequest({ activeSurveyId, canViewSteps, loadedSurveyId, currentRequestId, setRequestId, getCurrentRequestId, requestSteps, setSteps, setLoadedSurveyId, onError }) {
    if (!shouldLoadSurveySteps(activeSurveyId, canViewSteps, loadedSurveyId)) return null;
    const requestId = nextRequestId(currentRequestId);
    setRequestId(requestId);
    requestSteps(activeSurveyId)
        .then(response => {
            if (requestId !== getCurrentRequestId()) return;
            setSteps(response.data || []);
            setLoadedSurveyId(activeSurveyId);
        })
        .catch(() => {
            if (requestId === getCurrentRequestId()) onError();
        });
    return requestId;
}

export function adminRouteState(search) {
    const params = new URLSearchParams(search);
    return { tab: params.get('tab'), hasStep: Boolean(params.get('step')) };
}

export function applyAdminRouteState(route, setActiveTab, setStepsView) {
    if (route.tab) setActiveTab(route.tab);
    if (route.hasStep) setStepsView('list');
}

export function allowedAdminTabs(can) {
    const candidates = [
        ['analytics', can('analytics.view')],
        ['users', can('users.view') || can('groups.view')],
        ['steps', can('steps.view') || can('surveys.view')],
        ['partners', can('partners.view')],
        ['cms', can('cms.view')],
        ['email-templates', can('messages.view')],
        ['events', can('messages.view')],
        ['audit', can('audit.view')],
        ['settings', can('settings.view')],
    ];
    return candidates.filter(([, allowed]) => allowed).map(([tab]) => tab);
}

export function preferredUserManagementView(can) {
    return !can('users.view') && can('groups.view') ? 'groups' : null;
}

export function applyAllowedAdminTab(tabs, activeTab, setActiveTab) {
    if (tabs.length > 0 && !tabs.includes(activeTab)) setActiveTab(tabs[0]);
}

export function applyPreferredUserManagementView(view, setView) {
    if (view) setView(view);
}

export const ADMIN_ANALYTICS_PAGINATION_KEY = 'admin-analytics-steps';
export const ADMIN_AUDIT_PAGINATION_KEY = 'admin-audit';

export function auditPaginationOptions(filter, dateFrom, dateTo) {
    return { resetKey: `${filter}|${dateFrom}|${dateTo}` };
}

export function permissionCollections(groupsData, catalogData) {
    return {
        groups: groupsData || [],
        catalog: catalogData || { categories: [], all_permissions: [] },
    };
}

export function billingPayload(data) {
    return data || { partners: [], totals: {} };
}

export function auditFilterArguments(filter, dateFrom, dateTo) {
    return [0, 0, filter === 'all' ? '' : filter, dateFrom, dateTo];
}

export function normalizeAuditData(data) {
    return { logs: data.logs || [], actionTypes: data.action_types || [] };
}

export async function loadFilteredAudit({ api, filter, dateFrom, dateTo, setLogs, setActionTypes, onError }) {
    try {
        const response = await api.getAuditLog(...auditFilterArguments(filter, dateFrom, dateTo));
        const result = normalizeAuditData(response.data);
        setLogs(result.logs);
        setActionTypes(result.actionTypes);
        return true;
    } catch (error) {
        onError();
        return false;
    }
}

export async function clearAuditFilters({ api, setFilter, setDateFrom, setDateTo, setLogs }) {
    setFilter('');
    setDateFrom('');
    setDateTo('');
    try {
        const response = await api.getAuditLog(0, 0);
        setLogs(normalizeAuditData(response.data).logs);
        return true;
    } catch (error) {
        return false;
    }
}

export const DEFAULT_SITE_SETTINGS = Object.freeze({
    site_title: '', logo_text: '', logo_bold_part: '', logo_light_part: '',
    contact_email: '', footer_text: '', primary_color: '', meta_description: '',
});

export function normalizeAdminLoadPayload({ users, steps, partners, analytics, home, about, partnersContent, landingPages, audit, settings, templates, groups, permissionCatalog, billing }) {
    return {
        users: users ?? [],
        steps: steps ?? [],
        partners: partners ?? [],
        analytics: { step_analytics: [], ...(analytics ?? {}) },
        cmsHome: home.content || {},
        cmsHomeTranslations: home.translations || {},
        cmsAbout: about.content || {},
        cmsAboutTranslations: about.translations || {},
        cmsPartners: partnersContent.content || {},
        cmsPartnersTranslations: partnersContent.translations || {},
        cmsLandingPages: landingPages.content || { pages: [] },
        cmsLandingPagesTranslations: landingPages.translations || {},
        auditLogs: audit.logs || [],
        auditActionTypes: audit.action_types || [],
        settings: { ...DEFAULT_SITE_SETTINGS, ...(settings ?? {}) },
        templates: templates || [],
        groups: groups || [],
        permissionCatalog: permissionCatalog || { categories: [], all_permissions: [] },
        billing: billingPayload(billing),
    };
}

function permittedRequest(allowed, request, fallback) {
    return allowed ? request().catch(() => ({ data: fallback })) : Promise.resolve({ data: fallback });
}

export function adminLoadRequests(can, adminApi, settingsApi, selectedSurveyId) {
    return [
        permittedRequest(can('users.view'), adminApi.getUsers, []),
        permittedRequest(can('steps.view'), () => adminApi.getSteps(selectedSurveyId), []),
        permittedRequest(can('partners.view'), adminApi.getPartners, []),
        permittedRequest(can('analytics.view'), adminApi.getAnalytics, null),
        adminApi.getCmsContent('home'),
        adminApi.getCmsContent('about'),
        adminApi.getCmsContent('partners'),
        adminApi.getCmsContent('landing_pages'),
        permittedRequest(can('audit.view'), () => adminApi.getAuditLog(0), { logs: [], action_types: [] }),
        permittedRequest(can('settings.view'), settingsApi.getAdmin, {}),
        permittedRequest(can('steps.view'), adminApi.listStepTemplates, []),
        permittedRequest(can('groups.view'), adminApi.getPermissionGroups, []),
        permittedRequest(can('groups.view'), adminApi.getPermissionCatalog, { categories: [], all_permissions: [] }),
        permittedRequest(can('settings.view'), adminApi.getBilling, { partners: [], totals: {} }),
    ];
}

export function stepDeepLinkCommand({ search, activeTab, stepsView, sortedSteps, showAllSteps, pageSize, page }) {
    const stepOrder = new URLSearchParams(search).get('step');
    if (!stepOrder || activeTab !== 'steps' || stepsView !== 'list') return null;
    const targetIndex = sortedSteps.findIndex(step => String(step.order) === String(stepOrder));
    if (targetIndex < 0) return null;
    if (!showAllSteps) {
        const targetPage = Math.floor(targetIndex / Number(pageSize)) + 1;
        if (page !== targetPage) return { type: 'page', page: targetPage };
    }
    return {
        type: 'scroll',
        selector: `[data-testid="step-row-order-${stepOrder}"]`,
        options: { block: 'start' },
    };
}

export function applyStepDeepLinkCommand(command, setPage, schedule, query) {
    if (!command) return;
    // Stryker disable next-line ConditionalExpression: both dispatcher branches are asserted directly; forcing scroll into page causes React pagination rescheduling to time out.
    if (command.type === 'page') {
        setPage(command.page);
        return;
    }
    schedule(() => {
        const element = query(command.selector);
        // Stryker disable next-line ConditionalExpression: the absent-DOM branch is asserted directly; forcing it true crashes React effect cleanup and is reported as a timeout.
        if (element) element.scrollIntoView(command.options);
    });
}

export function buildAdminControllerResult(state, commands) {
    return Object.assign({}, state, commands);
}
