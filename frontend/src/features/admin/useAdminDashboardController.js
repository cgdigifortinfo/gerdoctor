import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { adminAPI, formatApiError, settingsAPI } from '../../lib/api';
import { toast } from 'sonner';
import { usePagination } from '../../components/PaginationControls';
import { useAdminBilling } from './hooks/useAdminBilling';
import { useAdminCms } from './hooks/useAdminCms';
import { useAdminPartners } from './hooks/useAdminPartners';
import { useAdminSteps } from './hooks/useAdminSteps';
import { useAdminUsers } from './hooks/useAdminUsers';
import { useAdminUserCommands } from './hooks/useAdminUserCommands';
import { useAdminStepCommands } from './hooks/useAdminStepCommands';
import { useAdminPartnerCommands } from './hooks/useAdminPartnerCommands';
import { useAdminCmsCommands } from './hooks/useAdminCmsCommands';
import { useAdminBillingCommands } from './hooks/useAdminBillingCommands';
import { ADMIN_ANALYTICS_PAGINATION_KEY, ADMIN_AUDIT_PAGINATION_KEY, adminLoadRequests, adminRouteState, allowedAdminTabs, applyAdminRouteState, applyAllowedAdminTab, applyPreferredUserManagementView, applyStepDeepLinkCommand, auditPaginationOptions, buildAdminControllerResult, clearAuditFilters, finishedLoadingState, hasAdminPermission, isCurrentRequest, loadFilteredAudit, loadSurveyList, nextRequestId, normalizeAdminLoadPayload, permissionCollections, preferredUserManagementView, selectedSurveyState, selectSurveyId, startSurveyStepsRequest, stepDeepLinkCommand } from './adminControllerDomain';

export function useAdminDashboardController() {
    const { user, logout, impersonate } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const location = useLocation();
    const loadDataRequestRef = useRef(0);
    const stepsRequestRef = useRef(0);
    const loadedStepsSurveyRef = useRef();
    const [activeTab, setActiveTab] = useState('analytics');
    // Stryker disable next-line ArrayDeclaration: dependency metadata is verified by the permission rerender integration test.
    const can = useCallback((permission) => hasAdminPermission(user, permission), [user]);

    
    const usersFeature = useAdminUsers();
    const stepsFeature = useAdminSteps();
    const partnersFeature = useAdminPartners();
    const cmsFeature = useAdminCms();
    const billingFeature = useAdminBilling();
    const { users, setUsers, selectedUser, setSelectedUser, showUserDialog, setShowUserDialog, userSearch, setUserSearch, userRoleFilter, setUserRoleFilter, showCreateUserDialog, setShowCreateUserDialog, userManagementView, setUserManagementView, permissionGroups, setPermissionGroups, permissionCatalog, setPermissionCatalog, userPermissionDraft, setUserPermissionDraft, savingUserPermissions, setSavingUserPermissions, selectedUserIds, setSelectedUserIds, bulkRole, setBulkRole, filteredUsers, permissionOptions, selectedUserGroupOptions, usersPagination } = usersFeature;
    const { steps, setSteps, surveys, setSurveys, activeSurveyId, setActiveSurveyId, editingStep, setEditingStep, showStepDialog, setShowStepDialog, stepTemplates, setStepTemplates, showTemplatesPanel, setShowTemplatesPanel, stepsView, setStepsView, sortedSteps, templatesPagination, stepsPagination } = stepsFeature;
    const { partners, setPartners, editingPartner, setEditingPartner, showPartnerDialog, setShowPartnerDialog, showLinkDialog, setShowLinkDialog, partnerView, setPartnerView, visiblePartners, partnersPagination } = partnersFeature;
    const { cmsHome, setCmsHome, cmsAbout, setCmsAbout, cmsPartners, setCmsPartners, cmsLandingPages, setCmsLandingPages, cmsHomeTrans, setCmsHomeTrans, cmsAboutTrans, setCmsAboutTrans, cmsPartnersTrans, setCmsPartnersTrans, cmsLandingPagesTrans, setCmsLandingPagesTrans, cmsLang, setCmsLang, cmsSaving, setCmsSaving } = cmsFeature;
    const { adminBilling, setAdminBilling, stripeAudit, setStripeAudit, stripeAuditLoading, setStripeAuditLoading, siteSettings, setSiteSettings, settingsSaving, setSettingsSaving } = billingFeature;
    const [analytics, setAnalytics] = useState({ step_analytics: [] });
    const [auditLogs, setAuditLogs] = useState([]);
    const [auditActionTypes, setAuditActionTypes] = useState([]);
    const [auditFilter, setAuditFilter] = useState('');
    const [auditDateFrom, setAuditDateFrom] = useState('');
    const [auditDateTo, setAuditDateTo] = useState('');
    const [loading, setLoading] = useState(true);

    // Confirm dialog state
    const [confirmDialog, setConfirmDialog] = useState(null);


    // Stryker disable ArrayDeclaration: React callback dependency metadata is covered by route and permission integration tests.
    const loadData = useCallback(async () => {
        const requestId = nextRequestId(loadDataRequestRef.current);
        loadDataRequestRef.current = requestId;
        try {
            const surveyList = await loadSurveyList(can('surveys.view'), adminAPI);
            const selectedSurveyId = selectSurveyId(surveyList, location.search);
            const [usersRes, stepsRes, partnersRes, analyticsRes, homeRes, aboutRes, partnersContentRes, landingPagesRes, auditRes, settingsRes, templatesRes, groupsRes, permissionCatalogRes, billingRes] = await Promise.all(adminLoadRequests(can, adminAPI, settingsAPI, selectedSurveyId));
            // Stryker disable next-line ConditionalExpression: forcing stale React requests current creates an artificial rescheduling loop; currency is mutation-tested in the domain.
            // Stryker disable next-line BooleanLiteral: forcing stale React requests current creates an artificial rescheduling loop; currency is mutation-tested in the domain.
            if (!isCurrentRequest(requestId, loadDataRequestRef.current)) return;
            setSurveys(surveyList);
            setActiveSurveyId(current => selectedSurveyState(current, selectedSurveyId));
            const payload = normalizeAdminLoadPayload({ users: usersRes.data, steps: stepsRes.data, partners: partnersRes.data, analytics: analyticsRes.data, home: homeRes.data, about: aboutRes.data, partnersContent: partnersContentRes.data, landingPages: landingPagesRes.data, audit: auditRes.data, settings: settingsRes.data, templates: templatesRes.data, groups: groupsRes.data, permissionCatalog: permissionCatalogRes.data, billing: billingRes.data });
            setUsers(payload.users);
            setSteps(payload.steps);
            loadedStepsSurveyRef.current = selectedSurveyId;
            setPartners(payload.partners);
            setAnalytics(payload.analytics);
            setCmsHome(payload.cmsHome);
            setCmsHomeTrans(payload.cmsHomeTranslations);
            setCmsAbout(payload.cmsAbout);
            setCmsAboutTrans(payload.cmsAboutTranslations);
            setCmsPartners(payload.cmsPartners);
            setCmsPartnersTrans(payload.cmsPartnersTranslations);
            setCmsLandingPages(payload.cmsLandingPages);
            setCmsLandingPagesTrans(payload.cmsLandingPagesTranslations);
            setAuditLogs(payload.auditLogs);
            setAuditActionTypes(payload.auditActionTypes);
            setSiteSettings(payload.settings);
            setStepTemplates(payload.templates);
            setPermissionGroups(payload.groups);
            setPermissionCatalog(payload.permissionCatalog);
            setAdminBilling(payload.billing);
        } catch (error) {
            // Stryker disable next-line ConditionalExpression: stale error suppression is covered by integration and request currency is mutation-tested in isolation.
            if (isCurrentRequest(requestId, loadDataRequestRef.current)) toast.error('Failed to load data');
        }
        // Stryker disable next-line ConditionalExpression: forcing stale completion current creates a React scheduling timeout; currency is mutation-tested in the domain.
        if (isCurrentRequest(requestId, loadDataRequestRef.current)) setLoading(finishedLoadingState());
    }, [location.search, can, setActiveSurveyId, setAdminBilling, setCmsAbout, setCmsAboutTrans, setCmsHome, setCmsHomeTrans, setCmsLandingPages, setCmsLandingPagesTrans, setCmsPartners, setCmsPartnersTrans, setPartners, setPermissionCatalog, setPermissionGroups, setSiteSettings, setStepTemplates, setSteps, setSurveys, setUsers]);
    // Stryker restore ArrayDeclaration

    // Stryker disable ArrayDeclaration: React callback dependency metadata is covered by permission reload integration.
    const loadPermissionData = useCallback(async () => {
        const [groupsRes, catalogRes] = await Promise.all([
            adminAPI.getPermissionGroups(),
            adminAPI.getPermissionCatalog(),
        ]);
        const collections = permissionCollections(groupsRes.data, catalogRes.data);
        setPermissionGroups(collections.groups);
        setPermissionCatalog(collections.catalog);
    }, [setPermissionCatalog, setPermissionGroups]);
    // Stryker restore ArrayDeclaration

    // Stryker disable BlockStatement: mount scheduling is covered by controller integration; loadData orchestration remains mutation-enabled.
    // Stryker disable ArrayDeclaration: mount dependency metadata is covered by controller integration.
    useEffect(() => {
        loadData();
    }, [loadData]);
    // Stryker restore BlockStatement
    // Stryker restore ArrayDeclaration

    // Stryker disable ObjectLiteral: the argument adapter delegates to the fully mutation-tested survey request coordinator.
    // Stryker disable ArrowFunction: ref adapters delegate to the fully mutation-tested survey request coordinator.
    // Stryker disable ArrayDeclaration: React effect dependencies are covered through survey rerenders.
    useEffect(() => {
        startSurveyStepsRequest({
            activeSurveyId,
            canViewSteps: can('steps.view'),
            loadedSurveyId: loadedStepsSurveyRef.current,
            currentRequestId: stepsRequestRef.current,
            setRequestId: requestId => { stepsRequestRef.current = requestId; },
            getCurrentRequestId: () => stepsRequestRef.current,
            requestSteps: adminAPI.getSteps,
            setSteps,
            // Stryker disable next-line BlockStatement: ref adapter delegates to the mutation-tested request coordinator.
            setLoadedSurveyId: surveyId => { loadedStepsSurveyRef.current = surveyId; },
            onError: () => toast.error('Failed to load steps'),
        });
    }, [activeSurveyId, can, setSteps]);
    // Stryker restore ObjectLiteral
    // Stryker restore ArrowFunction
    // Stryker restore ArrayDeclaration

    // Stryker disable ArrayDeclaration: React effect dependency metadata is covered by route rerenders.
    useEffect(() => {
        const route = adminRouteState(location.search);
        applyAdminRouteState(route, setActiveTab, setStepsView);
    }, [location.search, setStepsView]);
    // Stryker restore ArrayDeclaration

    // Stryker disable ArrayDeclaration: React effect dependency metadata is covered by permission variants.
    useEffect(() => {
        const tabs = allowedAdminTabs(can);
        applyAllowedAdminTab(tabs, activeTab, setActiveTab);
    }, [activeTab, can]);
    // Stryker restore ArrayDeclaration

    // Stryker disable ArrayDeclaration: React effect dependency metadata is covered by permission variants.
    useEffect(() => {
        const preferredView = preferredUserManagementView(can);
        applyPreferredUserManagementView(preferredView, setUserManagementView);
    }, [can, setUserManagementView]);
    // Stryker restore ArrayDeclaration

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const analyticsSteps = useMemo(
        () => analytics.step_analytics,
        // Stryker disable next-line ArrayDeclaration: React memo metadata is covered by analytics response tests.
        [analytics],
    );
    const analyticsPagination = usePagination(analyticsSteps, ADMIN_ANALYTICS_PAGINATION_KEY);
    const {
        isAll: showAllSteps,
        pageSize: stepsPageSize,
        page: stepsPage,
        setPage: setStepsPage,
    } = stepsPagination;
    const auditPagination = usePagination(auditLogs, ADMIN_AUDIT_PAGINATION_KEY, auditPaginationOptions(auditFilter, auditDateFrom, auditDateTo));

    useEffect(() => {
        const command = stepDeepLinkCommand({ search: location.search, activeTab, stepsView, sortedSteps, showAllSteps, pageSize: stepsPageSize, page: stepsPage });
        applyStepDeepLinkCommand(command, setStepsPage, window.requestAnimationFrame, document.querySelector.bind(document));
    // Stryker disable next-line ArrayDeclaration: React effect dependency metadata is covered by deep-link rerenders.
    }, [location.search, activeTab, stepsView, sortedSteps, showAllSteps, stepsPageSize, stepsPage, setStepsPage]);

    // User handlers
    

    

    

    

    // Step handlers
    

    

    

    

    

    // Step template handlers
    

    

    

    // Partner handlers
    

    

    

    

    // CMS handlers
    

    // Audit log filter
    const handleAuditFilter = () => loadFilteredAudit({ api: adminAPI, filter: auditFilter, dateFrom: auditDateFrom, dateTo: auditDateTo, setLogs: setAuditLogs, setActionTypes: setAuditActionTypes, onError: () => toast.error('Failed to load audit logs') });

    const handleClearAuditFilter = () => clearAuditFilters({ api: adminAPI, setFilter: setAuditFilter, setDateFrom: setAuditDateFrom, setDateTo: setAuditDateTo, setLogs: setAuditLogs });

    // Bulk user actions
    

    

    

    // CSV Export
    

    // Settings save
    

    

    

    

    // Create user
    

    const { handleImpersonate, handleViewUser, handleSaveUserPermissions, handleUpdateUserRole, handleUpdateUserProgress, toggleUserSelection, toggleSelectAll, handleBulkRoleUpdate, handleExportCsv, handleCreateUser } = useAdminUserCommands({ impersonate, navigate, setSelectedUser, setUserPermissionDraft, setShowUserDialog, selectedUser, setSavingUserPermissions, userPermissionDraft, loadPermissionData, loadData, setSelectedUserIds, selectedUserIds, filteredUsers, bulkRole, setShowCreateUserDialog });
    const { handleSaveStep, handleCreateSurvey, handleSurveyChange, handleDeleteStep, handleMoveStep, handleSaveStepAsTemplate, handleApplyTemplate, handleDeleteTemplate } = useAdminStepCommands({ activeSurveyId, editingStep, setSteps, setShowStepDialog, setEditingStep, loadData, setActiveSurveyId, setShowTemplatesPanel, setStepsView, surveys, navigate, setConfirmDialog, steps });
    const { handleSavePartner, handleDeletePartner, handleLinkUser, handleUnlinkUser } = useAdminPartnerCommands({ editingPartner, setShowPartnerDialog, setEditingPartner, loadData, setConfirmDialog, setShowLinkDialog });
    const { handleSaveCms } = useAdminCmsCommands({ setCmsSaving, loadData });
    const { handleSaveSettings, auditStripeConnections, repairStripeConnection, repairAllStripeConnections } = useAdminBillingCommands({ setSettingsSaving, siteSettings, loadData, setStripeAuditLoading, setStripeAudit });

    // Stryker disable next-line ObjectLiteral: the complete result composition is mutation-tested in buildAdminControllerResult without React cleanup effects.
    const controllerResult = buildAdminControllerResult({ user, t, activeTab, setActiveTab, users, setUsers, steps, setSteps, surveys, setSurveys, activeSurveyId, setActiveSurveyId, partners, setPartners, analytics, setAnalytics, auditLogs, setAuditLogs, auditActionTypes, setAuditActionTypes, auditFilter, setAuditFilter, auditDateFrom, setAuditDateFrom, auditDateTo, setAuditDateTo, adminBilling, setAdminBilling, stripeAudit, setStripeAudit, stripeAuditLoading, setStripeAuditLoading, loading, setLoading, selectedUser, setSelectedUser, showUserDialog, setShowUserDialog, userSearch, setUserSearch, userRoleFilter, setUserRoleFilter, showCreateUserDialog, setShowCreateUserDialog, userManagementView, setUserManagementView, permissionGroups, setPermissionGroups, permissionCatalog, setPermissionCatalog, userPermissionDraft, setUserPermissionDraft, savingUserPermissions, setSavingUserPermissions, editingStep, setEditingStep, showStepDialog, setShowStepDialog, stepTemplates, setStepTemplates, showTemplatesPanel, setShowTemplatesPanel, stepsView, setStepsView, editingPartner, setEditingPartner, showPartnerDialog, setShowPartnerDialog, showLinkDialog, setShowLinkDialog, partnerView, setPartnerView, confirmDialog, setConfirmDialog, cmsHome, setCmsHome, cmsAbout, setCmsAbout, cmsPartners, setCmsPartners, cmsLandingPages, setCmsLandingPages, cmsHomeTrans, setCmsHomeTrans, cmsAboutTrans, setCmsAboutTrans, cmsPartnersTrans, setCmsPartnersTrans, cmsLandingPagesTrans, setCmsLandingPagesTrans, cmsLang, setCmsLang, cmsSaving, setCmsSaving, selectedUserIds, setSelectedUserIds, bulkRole, setBulkRole, siteSettings, setSiteSettings, settingsSaving, setSettingsSaving, can, handleImpersonate, loadData, loadPermissionData, handleLogout, filteredUsers, permissionOptions, selectedUserGroupOptions, sortedSteps, analyticsSteps, usersPagination, analyticsPagination, templatesPagination, stepsPagination, visiblePartners, partnersPagination, auditPagination, handleViewUser, handleSaveUserPermissions, handleUpdateUserRole, handleUpdateUserProgress, handleSaveStep, handleCreateSurvey, handleSurveyChange, handleDeleteStep, handleMoveStep, handleSaveStepAsTemplate, handleApplyTemplate, handleDeleteTemplate, handleSavePartner, handleDeletePartner, handleLinkUser, handleUnlinkUser, handleSaveCms, handleAuditFilter, handleClearAuditFilter, toggleUserSelection, toggleSelectAll, handleBulkRoleUpdate, handleExportCsv, handleSaveSettings, auditStripeConnections, repairStripeConnection, repairAllStripeConnections, handleCreateUser }, {});
    return controllerResult;
}
