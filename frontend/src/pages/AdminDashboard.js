import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { adminAPI, formatApiError, filesAPI, settingsAPI } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { 
    SignOut, Users, ListChecks, Buildings, Plus, Pencil, Trash, 
    Eye, X, ChartBar, Notebook, MagnifyingGlass, Link as LinkIcon,
    LinkBreak, UserPlus, ArrowRight, Check, DownloadSimple, ClockCounterClockwise,
    ArrowUp, ArrowDown, UserCircle, Image as ImageIcon, GearSix, UserSwitch,
    Envelope, BellRinging
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Checkbox } from '../components/ui/checkbox';
import { useLanguage } from '../contexts/LanguageContext';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { Logo } from '../components/Logo';
import StepsFlowBuilder from '../components/StepsFlowBuilder';
import EmailTemplateEditor from '../components/admin/EmailTemplateEditor';
import EventManagement from '../components/admin/EventManagement';
import { SearchableMultiSelect, SearchableSelect } from '../components/admin/EntityPickers';
import SurveyFormBuilder, { CONTENT_FIELD_TYPES } from '../components/admin/SurveyFormBuilder';
import PermissionGroupsManager from '../components/admin/PermissionGroupsManager';
import { PaginationControls, usePagination } from '../components/PaginationControls';
import { HelpLabel, HelpTooltip } from '../components/ui/help-tooltip';

export default function AdminDashboard() {
    const { user, logout, impersonate } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const location = useLocation();
    const loadDataRequestRef = useRef(0);
    const stepsRequestRef = useRef(0);
    const loadedStepsSurveyRef = useRef('');
    const [activeTab, setActiveTab] = useState('analytics');
    const can = useCallback((permission) => !!user && (user.permissions?.includes('*') || user.permissions?.includes(permission)), [user]);

    const handleImpersonate = async (userId) => {
        try {
            const res = await adminAPI.impersonateUser(userId);
            const { access_token, user: targetUser } = res.data;
            await impersonate(access_token, targetUser);
            // Navigate based on target role
            if (targetUser.role === 'partner') navigate('/partner-dashboard');
            else navigate('/dashboard');
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };
    const [users, setUsers] = useState([]);
    const [steps, setSteps] = useState([]);
    const [surveys, setSurveys] = useState([]);
    const [activeSurveyId, setActiveSurveyId] = useState('');
    const [partners, setPartners] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [auditLogs, setAuditLogs] = useState([]);
    const [auditActionTypes, setAuditActionTypes] = useState([]);
    const [auditFilter, setAuditFilter] = useState('');
    const [auditDateFrom, setAuditDateFrom] = useState('');
    const [auditDateTo, setAuditDateTo] = useState('');
    const [adminBilling, setAdminBilling] = useState({ partners: [], totals: {} });
    const [stripeAudit, setStripeAudit] = useState(null);
    const [stripeAuditLoading, setStripeAuditLoading] = useState(false);
    const [loading, setLoading] = useState(true);

    // User management state
    const [selectedUser, setSelectedUser] = useState(null);
    const [showUserDialog, setShowUserDialog] = useState(false);
    const [userSearch, setUserSearch] = useState('');
    const [userRoleFilter, setUserRoleFilter] = useState('all');
    const [showCreateUserDialog, setShowCreateUserDialog] = useState(false);
    const [userManagementView, setUserManagementView] = useState('users');
    const [permissionGroups, setPermissionGroups] = useState([]);
    const [permissionCatalog, setPermissionCatalog] = useState({ categories: [], all_permissions: [] });
    const [userPermissionDraft, setUserPermissionDraft] = useState({ group_ids: [], allow: [], deny: [] });
    const [savingUserPermissions, setSavingUserPermissions] = useState(false);

    // Step management state
    const [editingStep, setEditingStep] = useState(null);
    const [showStepDialog, setShowStepDialog] = useState(false);
    const [stepTemplates, setStepTemplates] = useState([]);
    const [showTemplatesPanel, setShowTemplatesPanel] = useState(false);
    const [stepsView, setStepsView] = useState('flow'); // 'flow' | 'dependency' | 'list'

    // Partner management state
    const [editingPartner, setEditingPartner] = useState(null);
    const [showPartnerDialog, setShowPartnerDialog] = useState(false);
    const [showLinkDialog, setShowLinkDialog] = useState(null);
    const [partnerView, setPartnerView] = useState('active');

    // Confirm dialog state
    const [confirmDialog, setConfirmDialog] = useState(null);

    // CMS state
    const [cmsHome, setCmsHome] = useState({});
    const [cmsAbout, setCmsAbout] = useState({});
    const [cmsPartners, setCmsPartners] = useState({});
    const [cmsLandingPages, setCmsLandingPages] = useState({ pages: [] });
    const [cmsHomeTrans, setCmsHomeTrans] = useState({});
    const [cmsAboutTrans, setCmsAboutTrans] = useState({});
    const [cmsPartnersTrans, setCmsPartnersTrans] = useState({});
    const [cmsLandingPagesTrans, setCmsLandingPagesTrans] = useState({});
    const [cmsLang, setCmsLang] = useState('de');
    const [cmsSaving, setCmsSaving] = useState(false);

    // Bulk selection state
    const [selectedUserIds, setSelectedUserIds] = useState([]);
    const [bulkRole, setBulkRole] = useState('user');

    // Settings state
    const [siteSettings, setSiteSettings] = useState({
        site_title: '', logo_text: '', logo_bold_part: '', logo_light_part: '',
        contact_email: '', footer_text: '', primary_color: '', meta_description: ''
    });
    const [settingsSaving, setSettingsSaving] = useState(false);

    const loadData = useCallback(async () => {
        const requestId = loadDataRequestRef.current + 1;
        loadDataRequestRef.current = requestId;
        try {
            const surveysRes = can('surveys.view') ? await adminAPI.getSurveys().catch(() => ({ data: [] })) : { data: [] };
            const surveyList = surveysRes.data || [];
            const params = new URLSearchParams(location.search);
            const requestedSurvey = params.get('survey') || '';
            const requestedSurveyId = surveyList.find(s => s.id === requestedSurvey || s.slug === requestedSurvey)?.id || '';
            const selectedSurveyId = requestedSurveyId || surveyList.find(s => s.is_default)?.id || surveyList[0]?.id || '';
            const [usersRes, stepsRes, partnersRes, analyticsRes, homeRes, aboutRes, partnersContentRes, landingPagesRes, auditRes, settingsRes, templatesRes, groupsRes, permissionCatalogRes, billingRes] = await Promise.all([
                can('users.view') ? adminAPI.getUsers() : Promise.resolve({ data: [] }),
                can('steps.view') ? adminAPI.getSteps(selectedSurveyId) : Promise.resolve({ data: [] }),
                can('partners.view') ? adminAPI.getPartners() : Promise.resolve({ data: [] }),
                can('analytics.view') ? adminAPI.getAnalytics() : Promise.resolve({ data: null }),
                adminAPI.getCmsContent('home'),
                adminAPI.getCmsContent('about'),
                adminAPI.getCmsContent('partners'),
                adminAPI.getCmsContent('landing_pages'),
                can('audit.view') ? adminAPI.getAuditLog(0) : Promise.resolve({ data: { logs: [], action_types: [] } }),
                can('settings.view') ? settingsAPI.getAdmin().catch(() => ({ data: {} })) : Promise.resolve({ data: {} }),
                can('steps.view') ? adminAPI.listStepTemplates().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
                can('groups.view') ? adminAPI.getPermissionGroups().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
                can('groups.view') ? adminAPI.getPermissionCatalog().catch(() => ({ data: { categories: [], all_permissions: [] } })) : Promise.resolve({ data: { categories: [], all_permissions: [] } }),
                can('settings.view') ? adminAPI.getBilling().catch(() => ({ data: { partners: [], totals: {} } })) : Promise.resolve({ data: { partners: [], totals: {} } }),
            ]);
            if (requestId !== loadDataRequestRef.current) return;
            setSurveys(surveyList);
            if (selectedSurveyId) {
                setActiveSurveyId(current => current === selectedSurveyId ? current : selectedSurveyId);
            }
            setUsers(usersRes.data);
            setSteps(stepsRes.data);
            loadedStepsSurveyRef.current = selectedSurveyId;
            setPartners(partnersRes.data);
            setAnalytics(analyticsRes.data);
            setCmsHome(homeRes.data.content || {});
            setCmsHomeTrans(homeRes.data.translations || {});
            setCmsAbout(aboutRes.data.content || {});
            setCmsAboutTrans(aboutRes.data.translations || {});
            setCmsPartners(partnersContentRes.data.content || {});
            setCmsPartnersTrans(partnersContentRes.data.translations || {});
            setCmsLandingPages(landingPagesRes.data.content || { pages: [] });
            setCmsLandingPagesTrans(landingPagesRes.data.translations || {});
            setAuditLogs(auditRes.data.logs || []);
            setAuditActionTypes(auditRes.data.action_types || []);
            if (settingsRes.data) setSiteSettings(settingsRes.data);
            setStepTemplates(templatesRes.data || []);
            setPermissionGroups(groupsRes.data || []);
            setPermissionCatalog(permissionCatalogRes.data || { categories: [], all_permissions: [] });
            setAdminBilling(billingRes.data || { partners: [], totals: {} });
        } catch (error) {
            if (requestId !== loadDataRequestRef.current) return;
            toast.error('Failed to load data');
        } finally {
            if (requestId === loadDataRequestRef.current) setLoading(false);
        }
    }, [location.search, can]);

    const loadPermissionData = useCallback(async () => {
        const [groupsRes, catalogRes] = await Promise.all([
            adminAPI.getPermissionGroups(),
            adminAPI.getPermissionCatalog(),
        ]);
        setPermissionGroups(groupsRes.data || []);
        setPermissionCatalog(catalogRes.data || { categories: [], all_permissions: [] });
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        if (!activeSurveyId || !can('steps.view')) return;
        if (loadedStepsSurveyRef.current === activeSurveyId) return;
        const requestId = stepsRequestRef.current + 1;
        stepsRequestRef.current = requestId;
        adminAPI.getSteps(activeSurveyId)
            .then((res) => {
                if (requestId === stepsRequestRef.current) {
                    setSteps(res.data || []);
                    loadedStepsSurveyRef.current = activeSurveyId;
                }
            })
            .catch(() => {
                if (requestId === stepsRequestRef.current) {
                    toast.error('Failed to load steps');
                }
            });
    }, [activeSurveyId, can]);

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const tab = params.get('tab');
        if (tab) setActiveTab(tab);
        if (params.get('step')) setStepsView('list');
    }, [location.search]);

    useEffect(() => {
        const allowedTabs = [
            ['analytics', 'analytics.view'],
            ['users', can('users.view') || can('groups.view')],
            ['steps', can('steps.view') || can('surveys.view')],
            ['partners', 'partners.view'],
            ['cms', 'cms.view'],
            ['email-templates', 'messages.view'],
            ['events', 'messages.view'],
            ['audit', 'audit.view'],
            ['settings', 'settings.view'],
        ].filter(([, permission]) => typeof permission === 'boolean' ? permission : can(permission)).map(([tab]) => tab);
        if (allowedTabs.length && !allowedTabs.includes(activeTab)) setActiveTab(allowedTabs[0]);
    }, [activeTab, can]);

    useEffect(() => {
        if (!can('users.view') && can('groups.view')) setUserManagementView('groups');
    }, [can]);

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    // Filtered users
    const filteredUsers = useMemo(() => {
        return users.filter(u => {
            const matchesSearch = !userSearch || 
                u.name.toLowerCase().includes(userSearch.toLowerCase()) ||
                u.email.toLowerCase().includes(userSearch.toLowerCase());
            const matchesRole = userRoleFilter === 'all' || u.role === userRoleFilter;
            return matchesSearch && matchesRole;
        });
    }, [users, userSearch, userRoleFilter]);
    const permissionOptions = useMemo(() => (permissionCatalog.categories || []).flatMap((category) => (
        category.permissions.map((permission) => ({
            value: permission.key,
            label: permission.label,
            description: category.category,
            keywords: `${permission.key} ${permission.description}`,
        }))
    )), [permissionCatalog]);
    const selectedUserGroupOptions = useMemo(() => permissionGroups
        .filter((group) => !selectedUser || group.role === selectedUser.role)
        .map((group) => ({
            value: group.id,
            label: group.name,
            description: `${group.member_count} Mitglieder · ${group.permissions?.includes('*') ? 'Alle Rechte' : `${group.permissions?.length || 0} Rechte`}`,
            keywords: `${group.role} ${group.description || ''}`,
        })), [permissionGroups, selectedUser]);

    const sortedSteps = useMemo(
        () => [...steps].sort((a, b) => a.order - b.order),
        [steps],
    );
    const analyticsSteps = useMemo(
        () => analytics?.step_analytics || [],
        [analytics],
    );
    const usersPagination = usePagination(filteredUsers, 'admin-users', {
        resetKey: `${userSearch}|${userRoleFilter}`,
    });
    const analyticsPagination = usePagination(analyticsSteps, 'admin-analytics-steps');
    const templatesPagination = usePagination(stepTemplates, 'admin-step-templates');
    const stepsPagination = usePagination(sortedSteps, 'admin-steps', {
        resetKey: activeSurveyId,
    });
    const {
        isAll: showAllSteps,
        pageSize: stepsPageSize,
        page: stepsPage,
        setPage: setStepsPage,
    } = stepsPagination;
    const visiblePartners = useMemo(() => partners.filter(p => partnerView === 'pending' ? p.registration_status === 'pending' : p.registration_status !== 'pending'), [partners, partnerView]);
    const partnersPagination = usePagination(visiblePartners, `admin-partners-${partnerView}`);
    const auditPagination = usePagination(auditLogs, 'admin-audit', {
        resetKey: `${auditFilter}|${auditDateFrom}|${auditDateTo}`,
    });

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const stepOrder = params.get('step');
        if (!stepOrder || activeTab !== 'steps' || stepsView !== 'list' || sortedSteps.length === 0) return;

        const targetIndex = sortedSteps.findIndex(step => String(step.order) === String(stepOrder));
        if (targetIndex < 0) return;
        if (!showAllSteps) {
            const targetPage = Math.floor(targetIndex / Number(stepsPageSize)) + 1;
            if (stepsPage !== targetPage) {
                setStepsPage(targetPage);
                return;
            }
        }
        window.requestAnimationFrame(() => {
            document.querySelector(`[data-testid="step-row-order-${stepOrder}"]`)?.scrollIntoView({ block: 'start' });
        });
    }, [location.search, activeTab, stepsView, sortedSteps, showAllSteps, stepsPageSize, stepsPage, setStepsPage]);

    // User handlers
    const handleViewUser = async (userId) => {
        try {
            const response = await adminAPI.getUser(userId);
            setSelectedUser(response.data);
            setUserPermissionDraft({
                group_ids: response.data.group_ids || [],
                allow: response.data.permission_overrides?.allow || [],
                deny: response.data.permission_overrides?.deny || [],
            });
            setShowUserDialog(true);
        } catch (error) {
            toast.error('Failed to load user details');
        }
    };

    const handleSaveUserPermissions = async () => {
        if (!selectedUser) return;
        setSavingUserPermissions(true);
        try {
            const response = await adminAPI.updateUserPermissions(selectedUser.id, userPermissionDraft);
            toast.success('Benutzerrechte aktualisiert');
            setSelectedUser((current) => ({
                ...current,
                group_ids: response.data.group_ids,
                permission_overrides: response.data.permission_overrides,
                effective_permissions: response.data.effective_permissions,
            }));
            await Promise.all([loadPermissionData(), loadData()]);
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSavingUserPermissions(false); }
    };

    const handleUpdateUserRole = async (userId, role) => {
        try {
            await adminAPI.updateUserRole(userId, role);
            toast.success('User role updated');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleUpdateUserProgress = async (userId, stepId, newStatus) => {
        try {
            await adminAPI.updateUserProgress(userId, stepId, newStatus, {});
            toast.success('Progress updated');
            const response = await adminAPI.getUser(userId);
            setSelectedUser(response.data);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    // Step handlers
    const handleSaveStep = async (stepData) => {
        try {
            const payload = { ...stepData, survey_id: stepData.survey_id || activeSurveyId };
            if (editingStep?.id) {
                await adminAPI.updateStep(editingStep.id, payload);
                setSteps((current) => current.map((item) => item.id === editingStep.id ? { ...item, ...payload } : item));
                toast.success('Step updated');
            } else {
                await adminAPI.createStep(payload);
                toast.success('Step created');
            }
            setShowStepDialog(false);
            setEditingStep(null);
            await loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleCreateSurvey = async () => {
        const name = window.prompt('Name des neuen Surveys:', 'FSP Pflege');
        if (!name || !name.trim()) return;
        const slug = window.prompt('URL-Slug, z.B. pflege:', name.toLowerCase().replace(/\s+/g, '-'));
        if (!slug || !slug.trim()) return;
        try {
            await adminAPI.createSurvey({
                name: name.trim(),
                slug: slug.trim(),
                description: '',
                audience: '',
                is_active: true,
                is_default: false,
            });
            toast.success('Survey angelegt');
            setActiveSurveyId('');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleSurveyChange = (surveyId) => {
        setEditingStep(null);
        setShowTemplatesPanel(false);
        setStepsView('list');
        setSteps([]);
        setActiveSurveyId(surveyId);
        const selectedSurvey = surveys.find(s => s.id === surveyId);
        const surveyParam = selectedSurvey?.slug || surveyId;
        navigate(`/admin?tab=steps&survey=${encodeURIComponent(surveyParam)}&step=1`, { replace: true });
    };

    const handleDeleteStep = async (stepId) => {
        setConfirmDialog({
            message: 'Sind Sie sicher, dass Sie diesen Schritt loeschen moechten? Alle Fortschrittsdaten der Nutzer fuer diesen Schritt werden ebenfalls entfernt.',
            onConfirm: async () => {
                try {
                    await adminAPI.deleteStep(stepId);
                    toast.success('Step deleted');
                    loadData();
                } catch (error) {
                    toast.error(formatApiError(error));
                }
                setConfirmDialog(null);
            }
        });
    };

    const handleMoveStep = async (stepId, direction) => {
        const sorted = [...steps].sort((a, b) => a.order - b.order);
        const idx = sorted.findIndex(s => s.id === stepId);
        if (direction === 'up' && idx <= 0) return;
        if (direction === 'down' && idx >= sorted.length - 1) return;
        
        const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
        const newOrder = sorted.map(s => s.id);
        [newOrder[idx], newOrder[swapIdx]] = [newOrder[swapIdx], newOrder[idx]];
        
        try {
            await adminAPI.reorderSteps(newOrder, activeSurveyId);
            toast.success('Steps reordered');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    // Step template handlers
    const handleSaveStepAsTemplate = async (step) => {
        const name = window.prompt(`Template-Name für "${step.title}":`, step.title);
        if (!name || !name.trim()) return;
        try {
            await adminAPI.saveStepAsTemplate(step.id, name.trim(), step.description || '');
            toast.success('Als Template gespeichert');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleApplyTemplate = async (template) => {
        const maxOrder = steps.length ? Math.max(...steps.map(s => s.order)) : 0;
        const input = window.prompt(
            `An welcher Position soll "${template.name}" eingefügt werden? (1-${maxOrder + 1})`,
            String(maxOrder + 1)
        );
        if (!input) return;
        const order = parseInt(input, 10);
        if (!Number.isFinite(order) || order < 1) { toast.error('Ungültige Position'); return; }
        try {
            await adminAPI.applyStepTemplate(template.id, order, activeSurveyId);
            toast.success(`Template "${template.name}" eingefügt`);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleDeleteTemplate = (template) => {
        setConfirmDialog({
            message: `Template "${template.name}" dauerhaft löschen?`,
            onConfirm: async () => {
                try {
                    await adminAPI.deleteStepTemplate(template.id);
                    toast.success('Template gelöscht');
                    loadData();
                } catch (error) {
                    toast.error(formatApiError(error));
                }
                setConfirmDialog(null);
            }
        });
    };

    // Partner handlers
    const handleSavePartner = async (partnerData) => {
        try {
            if (editingPartner?.id) {
                await adminAPI.updatePartner(editingPartner.id, partnerData);
                toast.success('Partner updated');
            } else {
                await adminAPI.createPartner(partnerData);
                toast.success('Partner created');
            }
            setShowPartnerDialog(false);
            setEditingPartner(null);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleDeletePartner = async (partnerId) => {
        setConfirmDialog({
            message: 'Sind Sie sicher, dass Sie diesen Partner loeschen moechten? Alle Verknuepfungen und Submissions werden ebenfalls entfernt.',
            onConfirm: async () => {
                try {
                    await adminAPI.deletePartner(partnerId);
                    toast.success('Partner deleted');
                    loadData();
                } catch (error) {
                    toast.error(formatApiError(error));
                }
                setConfirmDialog(null);
            }
        });
    };

    const handleLinkUser = async (partnerId, userId) => {
        try {
            await adminAPI.linkPartnerUser(partnerId, userId);
            toast.success('User linked to partner');
            setShowLinkDialog(null);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleUnlinkUser = async (partnerId) => {
        try {
            await adminAPI.unlinkPartnerUser(partnerId);
            toast.success('User unlinked from partner');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    // CMS handlers
    const handleSaveCms = async (section, content, trans) => {
        setCmsSaving(true);
        try {
            await adminAPI.updateCmsContent(section, content, trans);
            toast.success(`${section} content updated`);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        } finally {
            setCmsSaving(false);
        }
    };

    // Audit log filter
    const handleAuditFilter = async () => {
        try {
            const actionVal = auditFilter === 'all' ? '' : auditFilter;
            const res = await adminAPI.getAuditLog(0, 0, actionVal, auditDateFrom, auditDateTo);
            setAuditLogs(res.data.logs || []);
            setAuditActionTypes(res.data.action_types || []);
        } catch (error) {
            toast.error('Failed to load audit logs');
        }
    };

    const handleClearAuditFilter = async () => {
        setAuditFilter('');
        setAuditDateFrom('');
        setAuditDateTo('');
        try {
            const res = await adminAPI.getAuditLog(0, 0);
            setAuditLogs(res.data.logs || []);
        } catch {}
    };

    // Bulk user actions
    const toggleUserSelection = (userId) => {
        setSelectedUserIds(prev => 
            prev.includes(userId) ? prev.filter(id => id !== userId) : [...prev, userId]
        );
    };

    const toggleSelectAll = () => {
        if (selectedUserIds.length === filteredUsers.length) {
            setSelectedUserIds([]);
        } else {
            setSelectedUserIds(filteredUsers.map(u => u.id));
        }
    };

    const handleBulkRoleUpdate = async () => {
        if (selectedUserIds.length === 0) { toast.error('No users selected'); return; }
        try {
            await adminAPI.bulkUpdateRole(selectedUserIds, bulkRole);
            toast.success(`${selectedUserIds.length} users updated to ${bulkRole}`);
            setSelectedUserIds([]);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    // CSV Export
    const handleExportCsv = async () => {
        try {
            const response = await adminAPI.exportUsersCsv();
            const blob = new Blob([response.data], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'users_export.csv';
            a.click();
            window.URL.revokeObjectURL(url);
            toast.success('CSV exported');
        } catch (error) {
            toast.error('Failed to export CSV');
        }
    };

    // Settings save
    const handleSaveSettings = async () => {
        setSettingsSaving(true);
        try {
            await settingsAPI.update(siteSettings);
            toast.success('Settings saved');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        } finally {
            setSettingsSaving(false);
        }
    };

    const auditStripeConnections = async () => {
        setStripeAuditLoading(true);
        try { const response = await adminAPI.auditStripeConnections(); setStripeAudit(response.data); }
        catch (error) { toast.error(formatApiError(error)); }
        finally { setStripeAuditLoading(false); }
    };

    const repairStripeConnection = async (partnerId) => {
        try { await adminAPI.repairStripeConnection(partnerId); toast.success('Stripe-Verbindung repariert'); await auditStripeConnections(); loadData(); }
        catch (error) { toast.error(formatApiError(error)); }
    };

    const repairAllStripeConnections = async () => {
        if (!window.confirm('Alle eindeutig reparierbaren Stripe-Verbindungen jetzt korrigieren?')) return;
        setStripeAuditLoading(true);
        try { const response = await adminAPI.repairAllStripeConnections(); toast.success(`${response.data.repaired} Stripe-Verbindungen repariert, ${response.data.skipped} übersprungen`); await auditStripeConnections(); loadData(); }
        catch (error) { toast.error(formatApiError(error)); setStripeAuditLoading(false); }
    };

    // Create user
    const handleCreateUser = async (userData) => {
        try {
            await adminAPI.createUser(userData);
            toast.success('User erstellt');
            setShowCreateUserDialog(false);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    if (loading) {
        return (
            <div className="app-view admin-view min-h-screen bg-background flex items-center justify-center">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        );
    }

    return (
        <div className="app-view admin-view min-h-screen bg-background">
            {/* Header */}
            <header className="app-topbar sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <Logo />
                            <span className="text-xs font-bold tracking-wider uppercase text-[var(--brand-primary)] px-2 py-1 bg-[var(--brand-soft)] rounded">
                                Admin
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <ThemeLangToggle />
                            <span className="text-sm text-muted-foreground hidden sm:block">{user?.name}</span>
                            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground" data-testid="admin-logout-btn">
                                <SignOut size={20} />
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            <div className="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="main-navigation mb-6 bg-card border border-border flex-wrap h-auto gap-1 p-1">
                        {can('analytics.view') && <TabsTrigger value="analytics" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white">
                            <ChartBar size={18} className="mr-2" />
                            {t('admin_dashboard')}
                        </TabsTrigger>}
                        {(can('users.view') || can('groups.view')) && <TabsTrigger value="users" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white" data-testid="admin-users-tab">
                            <Users size={18} className="mr-2" />
                            {t('admin_users')}
                        </TabsTrigger>}
                        {(can('steps.view') || can('surveys.view')) && <TabsTrigger value="steps" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white" data-testid="admin-steps-tab">
                            <ListChecks size={18} className="mr-2" />
                            {t('admin_steps')}
                        </TabsTrigger>}
                        {can('partners.view') && <TabsTrigger value="partners" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white" data-testid="admin-partners-tab">
                            <Buildings size={18} className="mr-2" />
                            {t('admin_partners')} {partners.some(p => p.registration_status === 'pending') && <span className="ml-2 rounded-full bg-amber-500 text-white text-[10px] px-1.5">{partners.filter(p => p.registration_status === 'pending').length}</span>}
                        </TabsTrigger>}
                        {can('cms.view') && <TabsTrigger value="cms" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white">
                            <Notebook size={18} className="mr-2" />
                            {t('admin_cms')}
                        </TabsTrigger>}
                        {can('messages.view') && <TabsTrigger value="email-templates" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white" data-testid="admin-email-templates-tab">
                            <Envelope size={18} className="mr-2" />
                            Nachrichten
                        </TabsTrigger>}
                        {can('messages.view') && <TabsTrigger value="events" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white" data-testid="admin-events-tab">
                            <BellRinging size={18} className="mr-2" />
                            Events
                        </TabsTrigger>}
                        {can('audit.view') && <TabsTrigger value="audit" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white" data-testid="admin-audit-tab">
                            <ClockCounterClockwise size={18} className="mr-2" />
                            {t('admin_audit')}
                        </TabsTrigger>}
                        {can('settings.view') && <TabsTrigger value="settings" className="data-[state=active]:bg-[var(--brand-primary)] data-[state=active]:text-white" data-testid="admin-settings-tab">
                            <GearSix size={18} className="mr-2" />
                            {t('admin_settings')}
                        </TabsTrigger>}
                    </TabsList>

                    {/* ============ ANALYTICS TAB ============ */}
                    <TabsContent value="analytics">
                        {analytics && (
                            <div className="space-y-6">
                                {/* Stats Grid */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <StatCard label="Total Users" value={analytics.total_users} />
                                    <StatCard label="Active Partners" value={analytics.total_partners} />
                                    <StatCard label="Submissions" value={analytics.total_submissions} />
                                    <StatCard label="New (7 days)" value={analytics.recent_registrations} />
                                </div>

                                {/* Role Distribution */}
                                <div className="bg-card border border-border rounded-sm p-6">
                                    <h3 className="text-lg font-semibold text-foreground mb-4">User Distribution</h3>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="text-center p-4 bg-background rounded-sm">
                                            <p className="text-2xl font-black text-foreground">{analytics.total_users}</p>
                                            <p className="text-sm text-muted-foreground">Regular Users</p>
                                        </div>
                                        <div className="text-center p-4 bg-background rounded-sm">
                                            <p className="text-2xl font-black text-foreground">{analytics.partner_count}</p>
                                            <p className="text-sm text-muted-foreground">Partner Users</p>
                                        </div>
                                        <div className="text-center p-4 bg-background rounded-sm">
                                            <p className="text-2xl font-black text-foreground">{analytics.admin_count}</p>
                                            <p className="text-sm text-muted-foreground">Admins</p>
                                        </div>
                                    </div>
                                </div>

                                {/* Step Completion Rates */}
                                <div className="bg-card border border-border rounded-sm p-6">
                                    <h3 className="text-lg font-semibold text-foreground mb-4">Step Completion Rates</h3>
                                    <div className="space-y-4">
                                        {analyticsPagination.paginatedItems.map((step) => (
                                            <div key={step.step_id} className="space-y-2">
                                                <div className="flex justify-between items-center">
                                                    <div className="flex items-center gap-2">
                                                        <span className="w-6 h-6 rounded-full bg-[var(--brand-primary)] text-white flex items-center justify-center text-xs font-bold">
                                                            {step.order}
                                                        </span>
                                                        <span className="font-medium text-sm text-foreground">{step.title}</span>
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                                        <span>{step.completed}/{step.total} completed</span>
                                                        <span className="font-bold text-[var(--brand-primary)]">{step.completion_rate}%</span>
                                                    </div>
                                                </div>
                                                <Progress value={step.completion_rate} className="h-2" />
                                            </div>
                                        ))}
                                    </div>
                                    <PaginationControls pagination={analyticsPagination} id="admin-analytics-steps" className="-mx-6 -mb-6 mt-6" />
                                </div>
                            </div>
                        )}
                    </TabsContent>

                    {/* ============ USERS TAB ============ */}
                    <TabsContent value="users">
                        <div className="mb-4 flex gap-2 rounded-lg border border-border bg-card p-1.5" data-testid="user-management-sections">
                            {can('users.view') && <Button type="button" variant={userManagementView === 'users' ? 'default' : 'ghost'} onClick={() => setUserManagementView('users')} data-testid="show-user-list">Benutzer</Button>}
                            {can('groups.view') && <Button type="button" variant={userManagementView === 'groups' ? 'default' : 'ghost'} onClick={() => setUserManagementView('groups')} data-testid="show-permission-groups">Nutzergruppen & Rechte</Button>}
                        </div>
                        {userManagementView === 'groups' && can('groups.view') && <PermissionGroupsManager groups={permissionGroups} catalog={permissionCatalog} onRefresh={loadPermissionData} canCreate={can('groups.create')} canUpdate={can('groups.update')} canDelete={can('groups.delete')} />}
                        <div className={`bg-card border border-border rounded-sm ${userManagementView === 'groups' || !can('users.view') ? 'hidden' : ''}`}>
                            <div className="p-4 border-b border-border">
                                <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center">
                                    <h2 className="text-lg font-semibold text-foreground">User Management</h2>
                                    <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                                        <div className="relative flex-1 sm:w-64">
                                            <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                            <Input
                                                placeholder="Search by name or email..."
                                                value={userSearch}
                                                onChange={(e) => setUserSearch(e.target.value)}
                                                className="pl-9 border-border rounded-sm"
                                                data-testid="user-search-input"
                                            />
                                        </div>
                                        <Select value={userRoleFilter} onValueChange={setUserRoleFilter}>
                                            <SelectTrigger className="w-full sm:w-36 border-border" data-testid="user-role-filter">
                                                <SelectValue placeholder="All Roles" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="all">All Roles</SelectItem>
                                                <SelectItem value="user">User</SelectItem>
                                                <SelectItem value="admin">Admin</SelectItem>
                                                <SelectItem value="partner">Partner</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        {can('users.export') && <Button variant="outline" onClick={handleExportCsv} className="border-border text-muted-foreground" data-testid="export-csv-btn">
                                            <DownloadSimple size={16} className="mr-1" /> Export CSV
                                        </Button>}
                                        {can('users.create') && <Button onClick={() => setShowCreateUserDialog(true)} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="create-user-btn">
                                            <UserPlus size={16} className="mr-1" /> {t('admin_create_user')}
                                        </Button>}
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground mt-2">{filteredUsers.length} of {users.length} users</p>
                            </div>

                            {/* Bulk Actions Bar */}
                            {can('users.update') && selectedUserIds.length > 0 && (
                                <div className="p-3 bg-[var(--brand-primary)]/5 border-b border-border flex flex-wrap items-center gap-3">
                                    <span className="text-sm font-medium text-[var(--brand-primary)]">{selectedUserIds.length} selected</span>
                                    <Select value={bulkRole} onValueChange={setBulkRole}>
                                        <SelectTrigger className="w-32 h-8 text-xs border-border" data-testid="bulk-role-select">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="user">User</SelectItem>
                                            <SelectItem value="admin">Admin</SelectItem>
                                            <SelectItem value="partner">Partner</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <Button size="sm" onClick={handleBulkRoleUpdate} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="bulk-apply-btn">
                                        Apply Role
                                    </Button>
                                    <Button variant="ghost" size="sm" onClick={() => setSelectedUserIds([])} className="text-muted-foreground">
                                        Clear
                                    </Button>
                                </div>
                            )}

                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-background">
                                        <tr>
                                            <th className="px-4 py-3 w-10">
                                                <Checkbox
                                                    checked={selectedUserIds.length === filteredUsers.length && filteredUsers.length > 0}
                                                    onCheckedChange={toggleSelectAll}
                                                    disabled={!can('users.update')}
                                                    data-testid="select-all-users"
                                                />
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Name</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Anmeldungen</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Email</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Role</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Partner</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Progress</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">{t('admin_forecast')}</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Joined</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {usersPagination.paginatedItems.map((u) => (
                                            <tr key={u.id} className={`border-t border-border table-row-hover ${selectedUserIds.includes(u.id) ? 'bg-[var(--brand-primary)]/5' : ''}`}>
                                                <td className="px-4 py-3">
                                                    <Checkbox
                                                        checked={selectedUserIds.includes(u.id)}
                                                        onCheckedChange={() => toggleUserSelection(u.id)}
                                                        disabled={!can('users.update')}
                                                        data-testid={`select-user-${u.id}`}
                                                    />
                                                </td>
                                                <td className="px-4 py-3 text-sm text-foreground font-medium">{u.name}{u.partner_registration_status === 'pending' && <span className="ml-2 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px]">NEUER PARTNER</span>}</td>
                                                <td className="px-4 py-3" data-testid={`user-pending-registrations-${u.id}`}>
                                                    {u.role === 'admin' ? (
                                                        <span className="text-xs text-muted-foreground">-</span>
                                                    ) : (u.pending_registrations || 0) > 0 ? (
                                                        <span
                                                            className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 rounded-full"
                                                            title={u.role === 'partner'
                                                                ? `${u.pending_registrations} offene Anmeldung${u.pending_registrations === 1 ? '' : 'en'} im Partner-Dashboard`
                                                                : `Gesamtzahl offener Anmeldungen bei allen gewählten Partnern: ${u.pending_registrations}`}
                                                        >
                                                            {u.pending_registrations}
                                                        </span>
                                                    ) : (
                                                        <span className="text-xs text-muted-foreground">0</span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-muted-foreground">{u.email}</td>
                                                <td className="px-4 py-3">
                                                    <Select value={u.role} onValueChange={(val) => handleUpdateUserRole(u.id, val)} disabled={!can('users.update')}>
                                                        <SelectTrigger className="w-32 h-8 text-xs border-border">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="user">User</SelectItem>
                                                            <SelectItem value="admin">Admin</SelectItem>
                                                            <SelectItem value="partner">Partner</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                    <div className="mt-1 flex max-w-40 flex-wrap gap-1" data-testid={`user-groups-${u.id}`}>
                                                        {(u.permission_groups || []).map((group) => <span key={group.id} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{group.name}</span>)}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3" data-testid={`user-partners-${u.id}`}>
                                                    {(u.partner_names && u.partner_names.length > 0) ? (
                                                        <div className="flex flex-wrap gap-1 max-w-[200px]">
                                                            {u.partner_names.map((pn, idx) => (
                                                                <span
                                                                    key={`${pn}-${idx}`}
                                                                    title={pn}
                                                                    className="px-1.5 py-0.5 text-[11px] font-medium bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] rounded-sm truncate max-w-[120px]"
                                                                >
                                                                    {pn}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <span className="text-xs text-muted-foreground">-</span>
                                                    )}
                                                    {(u.orphaned_partner_references || []).length > 0 && (
                                                        <div
                                                            className="mt-1 text-[10px] font-medium text-amber-700 dark:text-amber-300"
                                                            title={u.orphaned_partner_references.map(ref => ref.value).join(', ')}
                                                            data-testid={`user-orphaned-partners-${u.id}`}
                                                        >
                                                            Verwaiste Partnerreferenz
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                                                            <div className="h-full bg-[var(--brand-primary)] rounded-full transition-all" style={{ width: `${u.completion_pct || 0}%` }} />
                                                        </div>
                                                        <span className="text-xs text-muted-foreground font-medium">{u.completion_pct || 0}%</span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-muted-foreground">
                                                    {u.estimated_completion ? new Date(u.estimated_completion).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '-'}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-muted-foreground">
                                                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex gap-1">
                                                        <Button variant="outline" size="sm" onClick={() => handleViewUser(u.id)} className="border-border" data-testid={`view-user-${u.id}`}>
                                                            <Eye size={16} className="mr-1" /> View
                                                        </Button>
                                                        {can('users.impersonate') && u.role !== 'admin' && (
                                                            <Button variant="outline" size="sm" onClick={() => handleImpersonate(u.id)} className="border-border text-muted-foreground hover:text-[var(--brand-primary)] hover:border-[var(--brand-primary)]" data-testid={`impersonate-user-${u.id}`} title="Als User einloggen">
                                                                <UserSwitch size={16} />
                                                            </Button>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                        {filteredUsers.length === 0 && (
                                            <tr>
                                                <td colSpan={10} className="px-4 py-8 text-center text-muted-foreground">No users found</td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                            <PaginationControls pagination={usersPagination} id="admin-users" />
                        </div>
                    </TabsContent>

                    {/* ============ STEPS TAB ============ */}
                    <TabsContent value="steps">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border flex flex-wrap justify-between items-center gap-2">
                                <div>
                                    <h2 className="text-lg font-semibold text-foreground">Survey & Step Management</h2>
                                    <p className="text-xs text-muted-foreground">Verwalte unterschiedliche Survey-URLs und die dazugehörigen Step-Ketten.</p>
                                </div>
                                <div className="flex flex-wrap gap-2 items-center">
                                    <Select value={activeSurveyId} onValueChange={handleSurveyChange}>
                                        <SelectTrigger className="w-56 h-9" data-testid="admin-survey-select">
                                            <SelectValue placeholder="Survey wählen" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {surveys.map(s => (
                                                <SelectItem key={s.id} value={s.id}>
                                                    {s.name} /s/{s.slug}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {surveys.find(s => s.id === activeSurveyId)?.slug && (
                                        <Link
                                            to={`/s/${encodeURIComponent(surveys.find(s => s.id === activeSurveyId)?.slug)}?preview=1`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            <Button variant="outline" className="h-9 border-border" data-testid="open-survey-url-btn">
                                                URL öffnen
                                            </Button>
                                        </Link>
                                    )}
                                    <Button variant="outline" onClick={handleCreateSurvey} className="h-9 border-border" data-testid="create-survey-btn">
                                        Survey anlegen
                                    </Button>
                                    <div className="inline-flex rounded-sm border border-border overflow-hidden" data-testid="steps-view-toggle">
                                        <button
                                            onClick={() => setStepsView('flow')}
                                            className={`px-3 py-1.5 text-xs font-medium transition-colors ${stepsView === 'flow' ? 'bg-[var(--brand-primary)] text-white' : 'bg-card text-muted-foreground hover:text-foreground'}`}
                                            data-testid="steps-view-flow"
                                        >
                                            Flow-Ansicht
                                        </button>
                                        <button
                                            onClick={() => setStepsView('dependency')}
                                            className={`px-3 py-1.5 text-xs font-medium transition-colors border-l border-border ${stepsView === 'dependency' ? 'bg-[var(--brand-primary)] text-white' : 'bg-card text-muted-foreground hover:text-foreground'}`}
                                            data-testid="steps-view-dependency"
                                        >
                                            Abhängigkeiten
                                        </button>
                                        <button
                                            onClick={() => setStepsView('list')}
                                            className={`px-3 py-1.5 text-xs font-medium transition-colors border-l border-border ${stepsView === 'list' ? 'bg-[var(--brand-primary)] text-white' : 'bg-card text-muted-foreground hover:text-foreground'}`}
                                            data-testid="steps-view-list"
                                        >
                                            Listen-Ansicht
                                        </button>
                                    </div>
                                    <Button
                                        variant="outline"
                                        onClick={() => setShowTemplatesPanel(v => !v)}
                                        className="border-border"
                                        data-testid="toggle-templates-panel-btn"
                                    >
                                        Templates ({stepTemplates.length})
                                    </Button>
                                    <Button onClick={() => { setEditingStep(null); setShowStepDialog(true); }} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="add-step-btn">
                                        <Plus size={18} className="mr-2" /> Add Step
                                    </Button>
                                </div>
                            </div>

                            {showTemplatesPanel && (
                                <div className="p-4 border-b border-border bg-muted/30" data-testid="step-templates-panel">
                                    <h3 className="text-sm font-semibold text-foreground mb-3">Step-Templates</h3>
                                    {stepTemplates.length === 0 ? (
                                        <p className="text-sm text-muted-foreground">
                                            Noch keine Templates gespeichert. Klicke bei einem Schritt auf „Als Template speichern".
                                        </p>
                                    ) : (
                                        <>
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                            {templatesPagination.paginatedItems.map(tpl => (
                                                <div key={tpl.id} className="border border-border rounded-sm p-3 bg-card" data-testid={`template-card-${tpl.id}`}>
                                                    <div className="flex items-start justify-between gap-2">
                                                        <div className="min-w-0">
                                                            <p className="text-sm font-semibold text-foreground truncate">{tpl.name}</p>
                                                            <p className="text-xs text-muted-foreground truncate">{tpl.description || tpl.config?.step_type || ''}</p>
                                                        </div>
                                                        <span className="text-[10px] px-1.5 py-0.5 bg-muted text-muted-foreground rounded-sm flex-shrink-0">
                                                            {tpl.config?.step_type || 'form'}
                                                        </span>
                                                    </div>
                                                    <div className="flex gap-2 mt-3">
                                                        <Button size="sm" onClick={() => handleApplyTemplate(tpl)} className="h-7 px-2 text-xs bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid={`apply-template-${tpl.id}`}>
                                                            Einfügen
                                                        </Button>
                                                        <Button size="sm" variant="outline" onClick={() => handleDeleteTemplate(tpl)} className="h-7 px-2 text-xs border-red-200 text-red-500" data-testid={`delete-template-${tpl.id}`}>
                                                            <Trash size={12} />
                                                        </Button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <PaginationControls pagination={templatesPagination} id="admin-step-templates" className="-mx-4 -mb-4 mt-4" />
                                        </>
                                    )}
                                </div>
                            )}
                            {stepsView !== 'list' ? (
                                <div className="p-4">
                                    <StepsFlowBuilder
                                        key={activeSurveyId}
                                        layoutMode={stepsView === 'dependency' ? 'dependency' : 'editor'}
                                        steps={steps}
                                        onEdit={(s) => { setEditingStep(s); setShowStepDialog(true); }}
                                        onDelete={(s) => handleDeleteStep(s.id)}
                                        onAddStep={() => { setEditingStep(null); setShowStepDialog(true); }}
                                        onAddStepWithType={(stepType) => {
                                            const maxOrder = steps.length ? Math.max(...steps.map(s => s.order)) : 0;
                                            setEditingStep({
                                                title: '', description: '', step_type: stepType, order: maxOrder + 1,
                                                survey_id: activeSurveyId,
                                                fields: [], required_fields: [], required_uploads: [],
                                                conditions: [], field_mappings: [], duration_value: 0, duration_unit: 'days',
                                                is_active: true,
                                            });
                                            setShowStepDialog(true);
                                        }}
                                        onConditionAdd={async (source, target, form) => {
                                            try {
                                                const newCondition = {
                                                    source_step_order: source.order,
                                                    action: form.action,
                                                    field: form.field || '',
                                                    operator: form.operator,
                                                    value: form.value ?? '',
                                                    target_step_order: form.action === 'redirect' ? target.order : null,
                                                    message: form.message || '',
                                                };
                                                const updatedConditions = [...(target.conditions || []), newCondition];
                                                await adminAPI.updateStep(target.id, { ...target, survey_id: target.survey_id || activeSurveyId, conditions: updatedConditions });
                                                toast.success(`Condition erstellt: ${form.action}`);
                                                loadData();
                                            } catch (error) { toast.error(formatApiError(error)); }
                                        }}
                                        onConditionUpdate={async (stepId, condIndex, updatedCond) => {
                                            try {
                                                const step = steps.find(s => s.id === stepId);
                                                if (!step) return;
                                                const conds = [...(step.conditions || [])];
                                                conds[condIndex] = {
                                                    source_step_order: updatedCond.source_step_order ?? conds[condIndex].source_step_order,
                                                    action: updatedCond.action,
                                                    field: updatedCond.field || '',
                                                    operator: updatedCond.operator,
                                                    value: updatedCond.value ?? '',
                                                    target_step_order: updatedCond.action === 'redirect'
                                                        ? (updatedCond.target_step_order ?? conds[condIndex].target_step_order ?? null)
                                                        : null,
                                                    message: updatedCond.message || '',
                                                };
                                                await adminAPI.updateStep(stepId, { ...step, survey_id: step.survey_id || activeSurveyId, conditions: conds });
                                                toast.success('Condition aktualisiert');
                                                loadData();
                                            } catch (error) { toast.error(formatApiError(error)); }
                                        }}
                                        onConditionDelete={async (stepId, condIndex) => {
                                            try {
                                                const step = steps.find(s => s.id === stepId);
                                                if (!step) return;
                                                const conds = (step.conditions || []).filter((_, i) => i !== condIndex);
                                                await adminAPI.updateStep(stepId, { ...step, survey_id: step.survey_id || activeSurveyId, conditions: conds });
                                                toast.success('Condition gelöscht');
                                                loadData();
                                            } catch (error) { toast.error(formatApiError(error)); }
                                        }}
                                        onSaveLayout={async (positions) => {
                                            try {
                                                await adminAPI.saveStepLayout(positions);
                                            } catch (error) { /* silent – non-blocking */ }
                                        }}
                                    />
                                </div>
                            ) : (
                            <div className="p-4 space-y-4">
                                {steps.length === 0 && (
                                    <div className="border border-dashed border-border rounded-sm p-8 text-center" data-testid="steps-list-empty-state">
                                        <p className="text-sm font-semibold text-foreground">Keine Steps in diesem Survey</p>
                                        <p className="text-xs text-muted-foreground mt-1">Erstelle den ersten Step oder wähle ein Template aus.</p>
                                        <Button
                                            onClick={() => { setEditingStep(null); setShowStepDialog(true); }}
                                            className="mt-4 bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white"
                                            data-testid="steps-list-empty-add-step-btn"
                                        >
                                            <Plus size={16} className="mr-2" /> Step erstellen
                                        </Button>
                                    </div>
                                )}
                                {stepsPagination.paginatedItems.map((step) => (
                                    <div key={step.id} className="border border-border rounded-sm p-4" data-testid={`step-row-order-${step.order}`}>
                                        <div className="flex justify-between items-start">
                                            {/* Reorder arrows */}
                                            <div className="flex flex-col gap-1 mr-3 flex-shrink-0">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleMoveStep(step.id, 'up')}
                                                    disabled={sortedSteps[0]?.id === step.id}
                                                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground disabled:opacity-20"
                                                    data-testid={`step-move-up-${step.id}`}
                                                >
                                                    <ArrowUp size={14} />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleMoveStep(step.id, 'down')}
                                                    disabled={sortedSteps[sortedSteps.length - 1]?.id === step.id}
                                                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground disabled:opacity-20"
                                                    data-testid={`step-move-down-${step.id}`}
                                                >
                                                    <ArrowDown size={14} />
                                                </Button>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="w-8 h-8 rounded-full bg-[var(--brand-primary)] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                                                        {step.order}
                                                    </span>
                                                    <h3 className="font-semibold text-foreground">{step.title}</h3>
                                                    <span className={`px-2 py-0.5 text-xs rounded-sm ${step.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                                                        {step.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-muted-foreground mt-1 ml-10">{step.description}</p>
                                                <div className="flex gap-4 mt-2 ml-10 text-xs text-muted-foreground flex-wrap">
                                                    <span>Type: <strong>{step.step_type}</strong></span>
                                                    <span>Fields: <strong>{step.fields?.length || 0}</strong></span>
                                                    <span>Dauer: <strong>{step.duration_value === 0 ? t('step_instant') : `${step.duration_value} ${t('step_' + step.duration_unit)}`}</strong></span>
                                                    {step.email_on_enter && <span className="text-[var(--brand-primary)]">Email on enter</span>}
                                                    {step.email_on_edit && <span className="text-[var(--brand-primary)]">Email on edit</span>}
                                                    {step.email_on_leave && <span className="text-[var(--brand-primary)]">Email on leave</span>}
                                                </div>
                                            </div>
                                            <div className="flex gap-2 flex-shrink-0 ml-4">
                                                <Button variant="outline" size="sm" onClick={() => { setEditingStep(step); setShowStepDialog(true); }} className="border-border text-[var(--brand-primary)] hover:bg-[var(--brand-soft)]" data-testid={`edit-step-${step.id}`}>
                                                    <Pencil size={16} className="mr-1" /> Edit
                                                </Button>
                                                <Button variant="outline" size="sm" onClick={() => handleSaveStepAsTemplate(step)} className="border-border text-muted-foreground hover:text-[var(--brand-primary)]" data-testid={`save-template-${step.id}`} title="Als Template speichern">
                                                    Template
                                                </Button>
                                                <Button variant="outline" size="sm" onClick={() => handleDeleteStep(step.id)} className="border-red-200 text-red-500 hover:bg-red-50" data-testid={`delete-step-${step.id}`}>
                                                    <Trash size={16} className="mr-1" /> Delete
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {steps.length > 0 && (
                                    <PaginationControls pagination={stepsPagination} id="admin-steps" className="-mx-4 -mb-4" />
                                )}
                            </div>
                            )}
                        </div>
                    </TabsContent>

                    {/* ============ PARTNERS TAB ============ */}
                    <TabsContent value="partners">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border flex flex-wrap gap-3 justify-between items-center">
                                <div><h2 className="text-lg font-semibold text-foreground">Partner Management</h2><div className="flex gap-2 mt-2"><Button size="sm" variant={partnerView === 'active' ? 'default' : 'outline'} onClick={() => setPartnerView('active')}>Aktive Partner</Button><Button size="sm" variant={partnerView === 'pending' ? 'default' : 'outline'} onClick={() => setPartnerView('pending')} data-testid="pending-partners-view">Neue Partner ({partners.filter(p => p.registration_status === 'pending').length})</Button></div></div>
                                <Button onClick={() => { setEditingPartner(null); setShowPartnerDialog(true); }} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="add-partner-btn">
                                    <Plus size={18} className="mr-2" /> Add Partner
                                </Button>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-background">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Partner</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Anmeldungen</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Category</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Tags</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Linked User</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Status</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {partnersPagination.paginatedItems.map((partner) => {
                                            const linkedUser = users.find(u => u.id === partner.user_id);
                                            return (
                                                <tr key={partner.id} className="border-t border-border table-row-hover">
                                                    <td className="px-4 py-3">
                                                        <div className="flex items-center gap-3">
                                                            {partner.logo_url && <img src={partner.logo_url || '/assets/partner-placeholder.svg'} alt="" className="w-10 h-10 rounded-sm object-cover" />}
                                                            <div>
                                                                <p className="font-medium text-foreground">{partner.name}</p>
                                                                <p className="text-xs text-muted-foreground">{partner.contact_email}</p>
                                                                <p className="mt-1 text-xs text-muted-foreground">Leistungen: {(partner.service_steps || []).map(step => `Step ${step.order} ${step.title}`).join(', ') || 'keine Step-Zuordnung'}</p>
                                                                {partner.registration_source === 'self_service' && <span className="inline-flex mt-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">NEU REGISTRIERT</span>}
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3" data-testid={`partner-pending-registrations-${partner.id}`}>
                                                        {(partner.pending_registrations || 0) > 0 ? (
                                                            <span
                                                                className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 rounded-full"
                                                                title={`${partner.pending_registrations} offene Anmeldung${partner.pending_registrations === 1 ? '' : 'en'} im Partner-Dashboard`}
                                                            >
                                                                {partner.pending_registrations}
                                                            </span>
                                                        ) : (
                                                            <span className="text-xs text-muted-foreground">0</span>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-muted-foreground">{partner.category || '-'}</td>
                                                    <td className="px-4 py-3">
                                                        <div className="flex flex-wrap gap-1">
                                                            {(partner.tags || []).map(tag => (
                                                                <span key={tag} className="px-2 py-0.5 text-xs bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] rounded-sm">{tag}</span>
                                                            ))}
                                                            {(!partner.tags || partner.tags.length === 0) && <span className="text-xs text-muted-foreground">-</span>}
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        {linkedUser ? (
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-sm text-foreground">{linkedUser.name}</span>
                                                                <Button variant="ghost" size="sm" onClick={() => handleUnlinkUser(partner.id)} className="text-red-500 hover:text-red-700 h-6 px-1" title="Unlink user" data-testid={`unlink-partner-${partner.id}`}>
                                                                    <LinkBreak size={14} />
                                                                </Button>
                                                            </div>
                                                        ) : (
                                                            <Button variant="ghost" size="sm" onClick={() => setShowLinkDialog(partner)} className="text-[var(--brand-primary)] h-7 text-xs" data-testid={`link-partner-${partner.id}`}>
                                                                <UserPlus size={14} className="mr-1" /> Link User
                                                            </Button>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={`px-2 py-1 text-xs rounded-sm ${partner.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                                                            {partner.registration_status === 'pending' ? 'Wartet auf Survey' : 'Aktiv'}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <div className="flex gap-2">
                                                            <Button variant="ghost" size="sm" onClick={() => { setEditingPartner(partner); setShowPartnerDialog(true); }} data-testid={`edit-partner-${partner.id}`}>
                                                                <Pencil size={16} />
                                                            </Button>
                                                            <Button variant="ghost" size="sm" onClick={() => handleDeletePartner(partner.id)} className="text-red-500 hover:text-red-700" data-testid={`delete-partner-${partner.id}`}>
                                                                <Trash size={16} />
                                                            </Button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                            <PaginationControls pagination={partnersPagination} id="admin-partners" />
                        </div>
                    </TabsContent>

                    {/* ============ CMS TAB ============ */}
                    <TabsContent value="cms">
                        <div className="space-y-6">
                            <LandingPagesSection
                                content={cmsLandingPages}
                                onChange={setCmsLandingPages}
                                translations={cmsLandingPagesTrans}
                                onTransChange={setCmsLandingPagesTrans}
                                surveys={surveys}
                                onSave={() => handleSaveCms('landing_pages', cmsLandingPages, cmsLandingPagesTrans)}
                                saving={cmsSaving}
                            />

                            {/* Home Section */}
                            <CmsSection
                                title="Home / Hero Section"
                                fields={[
                                    { key: 'hero_title', label: 'Hero Title', type: 'text', placeholder: 'Transform Your Business Journey' },
                                    { key: 'hero_subtitle', label: 'Hero Subtitle', type: 'textarea', placeholder: 'A guided experience to connect you with the right partners' },
                                    { key: 'hero_cta', label: 'CTA Button Text', type: 'text', placeholder: 'Get Started' },
                                    { key: 'box1_title', label: 'Feature-Box 1 · Titel', type: 'text', placeholder: 'Guided Onboarding' },
                                    { key: 'box1_description', label: 'Feature-Box 1 · Beschreibung', type: 'textarea', placeholder: 'Step-by-step process to complete your profile…' },
                                    { key: 'box2_title', label: 'Feature-Box 2 · Titel', type: 'text', placeholder: 'Partner Network' },
                                    { key: 'box2_description', label: 'Feature-Box 2 · Beschreibung', type: 'textarea', placeholder: 'Access our curated network…' },
                                    { key: 'box3_title', label: 'Feature-Box 3 · Titel', type: 'text', placeholder: 'Progress Tracking' },
                                    { key: 'box3_description', label: 'Feature-Box 3 · Beschreibung', type: 'textarea', placeholder: 'Monitor your journey…' },
                                ]}
                                content={cmsHome}
                                onChange={setCmsHome}
                                translations={cmsHomeTrans}
                                onTransChange={setCmsHomeTrans}
                                onSave={() => handleSaveCms('home', cmsHome, cmsHomeTrans)}
                                saving={cmsSaving}
                            />

                            {/* About Section */}
                            <CmsSection
                                title="About Us Section"
                                fields={[
                                    { key: 'title', label: 'Section Title', type: 'text', placeholder: 'About Us' },
                                    { key: 'description', label: 'Description', type: 'textarea', placeholder: 'We help businesses connect...' },
                                    { key: 'mission', label: 'Mission Statement', type: 'textarea', placeholder: 'Our mission is to...' }
                                ]}
                                content={cmsAbout}
                                onChange={setCmsAbout}
                                translations={cmsAboutTrans}
                                onTransChange={setCmsAboutTrans}
                                onSave={() => handleSaveCms('about', cmsAbout, cmsAboutTrans)}
                                saving={cmsSaving}
                            />

                            {/* Partners Section */}
                            <CmsSection
                                title="Partners Section"
                                fields={[
                                    { key: 'title', label: 'Section Title', type: 'text', placeholder: 'Our Partners' },
                                    { key: 'description', label: 'Description', type: 'textarea', placeholder: 'Work with industry-leading partners...' }
                                ]}
                                content={cmsPartners}
                                onChange={setCmsPartners}
                                translations={cmsPartnersTrans}
                                onTransChange={setCmsPartnersTrans}
                                onSave={() => handleSaveCms('partners', cmsPartners, cmsPartnersTrans)}
                                saving={cmsSaving}
                            />
                        </div>
                    </TabsContent>

                    {/* ============ MESSAGE TEMPLATES TAB ============ */}
                    <TabsContent value="email-templates">
                        <EmailTemplateEditor />
                    </TabsContent>

                    {/* ============ DOMAIN EVENTS TAB ============ */}
                    <TabsContent value="events">
                        <EventManagement />
                    </TabsContent>

                    {/* ============ AUDIT LOG TAB ============ */}
                    <TabsContent value="audit">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border">
                                <h2 className="text-lg font-semibold mb-3">{t('admin_audit')}</h2>
                                <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-end">
                                    <div>
                                        <Label className="text-xs text-muted-foreground">Action Type</Label>
                                        <Select value={auditFilter} onValueChange={setAuditFilter}>
                                            <SelectTrigger className="w-44 h-9 text-sm border-border" data-testid="audit-action-filter">
                                                <SelectValue placeholder="All actions" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="all">All actions</SelectItem>
                                                {auditActionTypes.map(a => (
                                                    <SelectItem key={a} value={a}>{a.replace(/_/g, ' ')}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <Label className="text-xs text-muted-foreground">From</Label>
                                        <Input type="date" value={auditDateFrom} onChange={e => setAuditDateFrom(e.target.value)} className="h-9 text-sm border-border w-40" data-testid="audit-date-from" />
                                    </div>
                                    <div>
                                        <Label className="text-xs text-muted-foreground">To</Label>
                                        <Input type="date" value={auditDateTo} onChange={e => setAuditDateTo(e.target.value)} className="h-9 text-sm border-border w-40" data-testid="audit-date-to" />
                                    </div>
                                    <Button size="sm" onClick={handleAuditFilter} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white h-9" data-testid="audit-apply-filter">
                                        Filter
                                    </Button>
                                    <Button variant="ghost" size="sm" onClick={handleClearAuditFilter} className="text-muted-foreground h-9" data-testid="audit-clear-filter">
                                        {t('admin_clear')}
                                    </Button>
                                </div>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-muted">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Time</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Actor</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Action</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Target</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Details</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {auditPagination.paginatedItems.map((log, idx) => (
                                            <tr key={`${log.timestamp || 'log'}-${auditPagination.startIndex + idx}`} className="border-t border-border">
                                                <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                                                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                                                </td>
                                                <td className="px-4 py-3 text-sm font-medium">{log.actor_email}</td>
                                                <td className="px-4 py-3">
                                                    <AuditActionBadge action={log.action} />
                                                </td>
                                                <td className="px-4 py-3 text-sm text-muted-foreground">
                                                    <span className="capitalize">{log.target_type}</span>
                                                    {log.target_id && <span className="text-xs ml-1 opacity-60">#{log.target_id.slice(-6)}</span>}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-muted-foreground max-w-[200px] truncate">
                                                    {log.details ? Object.entries(log.details).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(', ') : '-'}
                                                </td>
                                            </tr>
                                        ))}
                                        {auditLogs.length === 0 && (
                                            <tr>
                                                <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                                                    No audit logs yet. Actions will appear here as admins make changes.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                            <PaginationControls pagination={auditPagination} id="admin-audit" />
                        </div>
                    </TabsContent>

                    {/* ============ SETTINGS TAB ============ */}
                    <TabsContent value="settings">
                        <div className="space-y-6">
                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-6">{t('admin_site_settings')}</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Site Title</Label>
                                        <Input value={siteSettings.site_title || ''} onChange={e => setSiteSettings(s => ({ ...s, site_title: e.target.value }))} placeholder="IHCA" data-testid="settings-site-title" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Meta Description</Label>
                                        <Input value={siteSettings.meta_description || ''} onChange={e => setSiteSettings(s => ({ ...s, meta_description: e.target.value }))} placeholder="Praktizieren in Deutschland" data-testid="settings-meta-desc" />
                                    </div>
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-2">{t('admin_logo_config')}</h2>
                                <p className="text-sm text-muted-foreground mb-6">The logo is displayed as a wordmark: the bold part followed by the light part.</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Bold Part (e.g. "GER")</Label>
                                        <Input value={siteSettings.logo_bold_part || ''} onChange={e => setSiteSettings(s => ({ ...s, logo_bold_part: e.target.value }))} placeholder="GER" data-testid="settings-logo-bold" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Light Part (e.g. "doctor")</Label>
                                        <Input value={siteSettings.logo_light_part || ''} onChange={e => setSiteSettings(s => ({ ...s, logo_light_part: e.target.value }))} placeholder="doctor" data-testid="settings-logo-light" />
                                    </div>
                                </div>
                                <div className="mt-4 p-4 bg-muted rounded-sm">
                                    <Label className="text-xs text-muted-foreground mb-2 block">Preview</Label>
                                    <div className="flex items-baseline">
                                        <span className="font-black text-2xl text-foreground" style={{ fontFamily: "'Varela Round', sans-serif", letterSpacing: 0 }}>{siteSettings.logo_bold_part || 'GER'}</span>
                                        <span className="font-light text-2xl text-foreground" style={{ fontFamily: "'Varela Round', sans-serif", letterSpacing: 0 }}>{siteSettings.logo_light_part || 'doctor'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-6">{t('admin_general')}</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Contact Email</Label>
                                        <Input value={siteSettings.contact_email || ''} onChange={e => setSiteSettings(s => ({ ...s, contact_email: e.target.value }))} placeholder="info@chrizz1001.de" data-testid="settings-contact-email" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Primary Color</Label>
                                        <div className="flex items-center gap-3">
                                            <input type="color" value={siteSettings.primary_color || 'var(--brand-primary)'} onChange={e => setSiteSettings(s => ({ ...s, primary_color: e.target.value }))} className="w-10 h-10 rounded cursor-pointer border border-border" data-testid="settings-primary-color" />
                                            <Input value={siteSettings.primary_color || ''} onChange={e => setSiteSettings(s => ({ ...s, primary_color: e.target.value }))} placeholder="var(--brand-primary)" className="flex-1" />
                                        </div>
                                    </div>
                                    <div className="space-y-2 md:col-span-2">
                                        <Label>Footer Text</Label>
                                        <Input value={siteSettings.footer_text || ''} onChange={e => setSiteSettings(s => ({ ...s, footer_text: e.target.value }))} placeholder="Optional footer text" data-testid="settings-footer-text" />
                                    </div>
                                </div>
                            </div>

                            {/* ============ UI-ELEMENTE (Feature Toggles) ============ */}
                            <div className="bg-card border border-border rounded-lg p-6" data-testid="settings-elements-section">
                                <h3 className="text-lg font-semibold text-foreground mb-1">UI-Elemente</h3>
                                <p className="text-sm text-muted-foreground mb-4">
                                    Ein-/Ausschalten globaler UI-Komponenten im User-Dashboard. Spätere
                                    Version: Diese Toggles werden Teil eines umfassenden Rechtesystems
                                    (Benutzergruppen + individuelle Rechte).
                                </p>
                                <div className="space-y-3">
                                    <ElementToggle
                                        id="ui_show_journey_indicator"
                                        label="Journey-Progress-Indikator"
                                        description={'Zeigt den Banner „Schritt X von Y" mit Pfad-Vorschau (Decision) bzw. nächsten Schritten über dem aktiven Step-Card.'}
                                        checked={siteSettings.ui_show_journey_indicator !== false}
                                        onChange={(val) => setSiteSettings(s => ({ ...s, ui_show_journey_indicator: val }))}
                                    />
                                    <ElementToggle
                                        id="ui_show_eta_header"
                                        label="Voraussichtliches Abschluss-Datum"
                                        description="Zeigt das errechnete ETA-Datum in der Kopfzeile neben dem Logo."
                                        checked={siteSettings.ui_show_eta_header !== false}
                                        onChange={(val) => setSiteSettings(s => ({ ...s, ui_show_eta_header: val }))}
                                    />
                                    <ElementToggle
                                        id="ui_show_progress_percentage"
                                        label="Fortschritts-Prozent-Badge"
                                        description={'Zeigt den Prozent-Badge (z.B. „17 %") in der Kopfzeile.'}
                                        checked={siteSettings.ui_show_progress_percentage !== false}
                                        onChange={(val) => setSiteSettings(s => ({ ...s, ui_show_progress_percentage: val }))}
                                    />
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-lg p-6" data-testid="settings-stripe-section">
                                <h3 className="text-lg font-semibold">Stripe Checkout & Billing</h3>
                                <p className="text-sm text-muted-foreground mt-1 mb-5">Partner bezahlen Ihren Business-Account als Stripe-Kunden. Sandbox nutzt ausschließlich Testschlüssel; Secrets werden nie öffentlich ausgeliefert.</p>
                                <div className="flex items-center justify-between border border-border rounded-md p-4 mb-5"><div><Label>Sandbox-Modus</Label><p className="text-xs text-muted-foreground">Testzahlungen ohne echten Geldfluss</p></div><Switch checked={siteSettings.stripe_sandbox_mode !== false} onCheckedChange={v => setSiteSettings(s => ({...s, stripe_sandbox_mode:v}))}/></div>
                                <div className="grid md:grid-cols-2 gap-4">
                                    {[
                                        ['stripe_test_publishable_key','Test Publishable Key','text'], ['stripe_test_secret_key','Test Secret Key','password'],
                                        ['stripe_test_webhook_secret','Test Webhook Secret','password'], ['stripe_live_publishable_key','Live Publishable Key','text'],
                                        ['stripe_live_secret_key','Live Secret Key','password'], ['stripe_live_webhook_secret','Live Webhook Secret','password']
                                    ].map(([key,label,type]) => <div key={key}><Label>{label}</Label><Input type={type} value={siteSettings[key] || ''} onChange={e => setSiteSettings(s => ({...s,[key]:e.target.value}))} autoComplete="off"/></div>)}
                                </div>
                                <div className="grid md:grid-cols-2 gap-4 mt-5 pt-5 border-t border-border">
                                    <div><Label>Partner Price ID</Label><Input placeholder="price_…" value={siteSettings.stripe_partner_price_id || ''} onChange={e => setSiteSettings(s => ({...s,stripe_partner_price_id:e.target.value}))}/><p className="text-xs text-muted-foreground mt-1">Preis im Stripe-Produktkatalog; für Abos muss er wiederkehrend sein.</p></div>
                                    <div><Label>Zahlungsmodell</Label><Input value="Monatliches Abonnement" disabled/><p className="text-xs text-muted-foreground mt-1">Die Grundgebühr wird ausschließlich als wiederkehrendes Stripe-Abonnement angelegt.</p></div>
                                    <div><Label>Globaler Standardpreis je Nutzer in Cent</Label><Input type="number" min="0" value={siteSettings.stripe_partner_user_fee_cents ?? 0} onChange={e => setSiteSettings(s => ({...s,stripe_partner_user_fee_cents:Number(e.target.value)||0}))}/><p className="text-xs text-muted-foreground mt-1">Default beim ersten Partner-Dokument je Nutzer und Leistungs-Step. Step- und Partnerpreise können ihn überschreiben.</p></div>
                                    <div><Label>Währung der Nutzergebühr</Label><Input maxLength={3} value={siteSettings.stripe_partner_user_fee_currency || 'eur'} onChange={e => setSiteSettings(s => ({...s,stripe_partner_user_fee_currency:e.target.value.toLowerCase()}))}/></div>
                                    <label className="flex items-center gap-3"><Switch checked={siteSettings.stripe_automatic_tax === true} onCheckedChange={v=>setSiteSettings(s=>({...s,stripe_automatic_tax:v}))}/><span><span className="block text-sm font-medium">Stripe Tax automatisch</span><span className="block text-xs text-muted-foreground">Erfordert aktiviertes Stripe Tax.</span></span></label>
                                    <label className="flex items-center gap-3"><Switch checked={siteSettings.stripe_allow_promotion_codes === true} onCheckedChange={v=>setSiteSettings(s=>({...s,stripe_allow_promotion_codes:v}))}/><span className="text-sm font-medium">Aktionscodes erlauben</span></label>
                                </div>
                                <div className="mt-6 border-t border-border pt-5" data-testid="stripe-connection-audit">
                                    <div className="flex flex-wrap items-center justify-between gap-3"><div><h4 className="font-semibold">Stripe-Verbindungen prüfen</h4><p className="text-sm text-muted-foreground">Findet fehlende oder widersprüchliche Customer-, Subscription- und Status-Verknüpfungen.</p></div><div className="flex gap-2"><Button type="button" variant="outline" onClick={auditStripeConnections} disabled={stripeAuditLoading}>{stripeAuditLoading ? 'Prüft…' : 'Verbindungen prüfen'}</Button>{stripeAudit?.repairable > 0 && <Button type="button" onClick={repairAllStripeConnections} disabled={stripeAuditLoading}>Alle reparierbaren Einträge reparieren</Button>}</div></div>
                                    {stripeAudit && <div className="mt-4"><p className="text-sm mb-3">{stripeAudit.defective} auffällig · {stripeAudit.repairable} automatisch reparierbar</p><div className="space-y-3">{(stripeAudit.entries || []).map(entry => <div key={entry.partner_id} className="rounded border border-border p-4" data-testid={`stripe-audit-${entry.partner_id}`}><div className="flex flex-wrap justify-between gap-3"><div><p className="font-medium">{entry.partner_name}</p><p className="text-xs text-muted-foreground">{entry.emails.join(', ') || 'keine E-Mail'} · Customer: {entry.current_customer_id || 'fehlt'} · Abo: {entry.current_subscription_id || 'fehlt'}</p><ul className="mt-2 list-disc pl-5 text-sm text-amber-700">{entry.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>{entry.repairable && <p className="mt-2 text-xs text-muted-foreground">Vorschlag: {entry.proposed_customer_id} / {entry.proposed_subscription_id} / {entry.proposed_billing_status}</p>}</div>{entry.repairable ? <Button type="button" size="sm" onClick={() => repairStripeConnection(entry.partner_id)}>Eintrag reparieren</Button> : <span className="h-fit rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">Manuelle Prüfung nötig</span>}</div></div>)}{!stripeAudit.entries?.length && <p className="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-800">Keine fehlerhaften Stripe-Verbindungen gefunden.</p>}</div></div>}
                                </div>
                                <div className="mt-6 border-t border-border pt-5" data-testid="admin-billing-summary">
                                    <h4 className="font-semibold">Abrechnungsübersicht</h4>
                                    <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Offene Nutzer</p><p className="text-xl font-bold">{adminBilling.totals?.pending_users || 0}</p></div>
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Offener Betrag</p><p className="text-xl font-bold">{((adminBilling.totals?.pending_amount || 0)/100).toLocaleString('de-DE',{style:'currency',currency:(siteSettings.stripe_partner_user_fee_currency||'EUR').toUpperCase()})}</p></div>
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Abgerechnete Nutzer</p><p className="text-xl font-bold">{adminBilling.totals?.billed_users || 0}</p></div>
                                        <div className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">Abgerechneter Betrag</p><p className="text-xl font-bold">{((adminBilling.totals?.billed_amount || 0)/100).toLocaleString('de-DE',{style:'currency',currency:(siteSettings.stripe_partner_user_fee_currency||'EUR').toUpperCase()})}</p></div>
                                    </div>
                                    <div className="mt-4 space-y-3">{(adminBilling.partners || []).map(item => <details key={item.partner_id} className="rounded border border-border"><summary className="cursor-pointer p-3 font-medium">{item.partner_name} · {item.usage.pending_users} offen · {item.invoices.length} Rechnungen</summary><div className="border-t border-border p-3 space-y-2">{item.invoices.map(invoice => <div key={invoice.id} className="flex justify-between gap-3 text-sm"><span>{invoice.number || invoice.id} · {invoice.status} · {((invoice.amount_due||0)/100).toLocaleString('de-DE',{style:'currency',currency:(invoice.currency||'eur').toUpperCase()})}</span><span className="flex gap-2">{invoice.hosted_invoice_url && <a className="text-[var(--brand-primary)] underline" href={invoice.hosted_invoice_url} target="_blank" rel="noreferrer">Ansehen</a>}{invoice.invoice_pdf && <a className="text-[var(--brand-primary)] underline" href={invoice.invoice_pdf} target="_blank" rel="noreferrer" download>PDF</a>}</span></div>)}{!item.invoices.length && <p className="text-sm text-muted-foreground">Noch keine Rechnungen.</p>}</div></details>)}</div>
                                </div>
                            </div>

                            <div className="flex justify-end">
                                <Button onClick={handleSaveSettings} disabled={settingsSaving} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="save-settings-btn">
                                    {settingsSaving ? t('admin_saving') : t('admin_save_settings')}
                                </Button>
                            </div>
                        </div>
                    </TabsContent>
                </Tabs>
            </div>

            {/* User Detail Dialog */}
            <Dialog open={showUserDialog} onOpenChange={setShowUserDialog}>
                <DialogContent className="max-w-4xl max-h-[88vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>User Details</DialogTitle>
                    </DialogHeader>
                    {selectedUser && (
                        <div className="space-y-6">
                            {/* Profile Image + Basic Info */}
                            <div className="flex items-start gap-6">
                                {/* Profile Image Preview */}
                                <div className="flex-shrink-0">
                                    {selectedUser.profile?.profile_image ? (
                                        <img
                                            src={filesAPI.getUrl(selectedUser.profile.profile_image)}
                                            alt={selectedUser.name}
                                            className="w-20 h-20 rounded-full object-cover border-2 border-border"
                                            data-testid="user-profile-image"
                                            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                                        />
                                    ) : null}
                                    <div className={`w-20 h-20 rounded-full bg-muted flex items-center justify-center ${selectedUser.profile?.profile_image ? 'hidden' : ''}`}>
                                        <UserCircle size={40} className="text-muted-foreground" />
                                    </div>
                                </div>
                                <div className="flex-1 grid grid-cols-2 gap-4">
                                    <div>
                                        <Label className="text-muted-foreground">Name</Label>
                                        <p className="font-medium">{selectedUser.name}</p>
                                        {selectedUser.partner_registration_status === 'pending' && <span className="inline-flex mt-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-xs font-bold">Neu registrierter Partner · Survey-Zuordnung offen</span>}
                                    </div>
                                    <div>
                                        <Label className="text-muted-foreground">Email</Label>
                                        <p className="font-medium">{selectedUser.email}</p>
                                    </div>
                                    <div>
                                        <Label className="text-muted-foreground">Role</Label>
                                        <p className="font-medium capitalize">{selectedUser.role}</p>
                                    </div>
                                    <div>
                                        <Label className="text-muted-foreground">Created</Label>
                                        <p className="font-medium">{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleDateString() : '-'}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Groups and per-user permission overrides */}
                            <section className="rounded-lg border border-border p-4" data-testid="user-permissions-editor">
                                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                                    <div><h4 className="font-semibold">Nutzergruppen und individuelle Rechte</h4><p className="mt-1 text-xs text-muted-foreground">Gruppenrechte bilden die Basis. „Erlauben“ ergänzt Rechte; „Verweigern“ hat immer Vorrang.</p></div>
                                    <span className="rounded-full bg-[var(--brand-primary)]/10 px-3 py-1 text-xs font-medium text-[var(--brand-primary)]">{selectedUser.effective_permissions?.includes('*') ? 'Vollzugriff' : `${selectedUser.effective_permissions?.length || 0} wirksame Rechte`}</span>
                                </div>
                                {selectedUser.is_primary_admin ? (
                                    <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">Das primäre Administratorkonto behält aus Sicherheitsgründen immer Vollzugriff.</div>
                                ) : can('users.permissions.manage') ? (
                                    <div className="space-y-4">
                                        <div><Label>Nutzergruppen</Label><p className="mb-2 text-xs text-muted-foreground">Mehrere Gruppen derselben Portalrolle können kombiniert werden.</p><SearchableMultiSelect options={selectedUserGroupOptions} values={userPermissionDraft.group_ids} onChange={(group_ids) => setUserPermissionDraft({ ...userPermissionDraft, group_ids })} placeholder="Nutzergruppen auswählen" searchPlaceholder="Nutzergruppe suchen …" testId="user-permission-groups" /></div>
                                        <div className="grid gap-4 md:grid-cols-2">
                                            <div className="rounded-md border border-green-200 p-3 dark:border-green-900"><Label className="text-green-700 dark:text-green-300">Zusätzlich erlauben</Label><p className="mb-2 mt-1 text-xs text-muted-foreground">Diese Rechte gelten unabhängig von den Gruppen.</p><SearchableMultiSelect options={permissionOptions} values={userPermissionDraft.allow} onChange={(allow) => setUserPermissionDraft({ ...userPermissionDraft, allow, deny: userPermissionDraft.deny.filter((key) => !allow.includes(key)) })} placeholder="Rechte erlauben" searchPlaceholder="Berechtigung suchen …" testId="user-permission-allow" /></div>
                                            <div className="rounded-md border border-red-200 p-3 dark:border-red-900"><Label className="text-red-700 dark:text-red-300">Ausdrücklich verweigern</Label><p className="mb-2 mt-1 text-xs text-muted-foreground">Deny überschreibt Gruppenrechte und individuelle Freigaben.</p><SearchableMultiSelect options={permissionOptions} values={userPermissionDraft.deny} onChange={(deny) => setUserPermissionDraft({ ...userPermissionDraft, deny, allow: userPermissionDraft.allow.filter((key) => !deny.includes(key)) })} placeholder="Rechte verweigern" searchPlaceholder="Berechtigung suchen …" testId="user-permission-deny" /></div>
                                        </div>
                                        <div className="flex justify-end"><Button type="button" onClick={handleSaveUserPermissions} disabled={savingUserPermissions} data-testid="save-user-permissions">{savingUserPermissions ? 'Speichert …' : 'Rechte speichern'}</Button></div>
                                    </div>
                                ) : (
                                    <div className="space-y-2 text-sm text-muted-foreground"><p>Du kannst die effektiven Rechte dieses Benutzers ansehen, aber nicht überschreiben.</p><div className="flex flex-wrap gap-1">{(selectedUser.permission_groups || []).map((group) => <span key={group.id} className="rounded bg-muted px-2 py-1 text-xs">{group.name}</span>)}</div></div>
                                )}
                            </section>

                            {/* Completion bar */}
                            <div className="p-4 bg-muted rounded-sm">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium">Fortschritt</span>
                                    <span className="text-sm font-bold text-[var(--brand-primary)]">{selectedUser.completion_pct || 0}%</span>
                                </div>
                                <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                                    <div className="h-full bg-[var(--brand-primary)] rounded-full transition-all" style={{ width: `${selectedUser.completion_pct || 0}%` }} />
                                </div>
                            </div>

                            {/* Profile Data */}
                            {selectedUser.profile && Object.keys(selectedUser.profile).length > 0 && (
                                <div>
                                    <h4 className="font-semibold mb-3">Profile</h4>
                                    <div className="grid grid-cols-2 gap-3">
                                        {Object.entries(selectedUser.profile)
                                            .filter(([key]) => key !== 'profile_image')
                                            .map(([key, value]) => (
                                            <div key={key} className="p-2 bg-background rounded-sm">
                                                <span className="text-xs text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</span>
                                                {typeof value === 'string' && value.length === 36 && value.includes('-') ? (
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <ImageIcon size={14} className="text-muted-foreground" />
                                                        <a href={filesAPI.getUrl(value)} target="_blank" rel="noopener noreferrer" className="text-sm text-[var(--brand-primary)] hover:underline">
                                                            View file
                                                        </a>
                                                    </div>
                                                ) : (
                                                    <p className="text-sm font-medium">{String(value)}</p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Progress with edit ability + step data */}
                            <div>
                                <h4 className="font-semibold mb-3">Progress</h4>
                                <div className="space-y-2">
                                    {selectedUser.progress?.map((p) => {
                                        const step = steps.find(s => s.id === p.step_id);
                                        const stepData = p.data || {};
                                        const hasData = Object.keys(stepData).filter(k => k !== 'skipped').length > 0;
                                        return (
                                            <div key={p.step_id} className="border border-border rounded-sm overflow-hidden">
                                                <div className="flex items-center justify-between p-3 bg-muted/50">
                                                    <div className="flex items-center gap-2">
                                                        <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${p.status === 'completed' ? 'bg-green-500 text-white' : p.status === 'in_progress' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>
                                                            {p.status === 'completed' ? <Check size={10} weight="bold" /> : step?.order || '?'}
                                                        </div>
                                                        <span className="text-sm font-medium">{step?.title || 'Unknown Step'}</span>
                                                    </div>
                                                    <Select value={p.status} onValueChange={(val) => handleUpdateUserProgress(selectedUser.id, p.step_id, val)}>
                                                        <SelectTrigger className={`w-36 h-8 text-xs border-0 ${p.status === 'completed' ? 'bg-green-100 text-green-700' : p.status === 'in_progress' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700'}`} data-testid={`user-progress-${p.step_id}`}>
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="pending">Pending</SelectItem>
                                                            <SelectItem value="in_progress">In Progress</SelectItem>
                                                            <SelectItem value="completed">Completed</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                {hasData && (
                                                    <div className="px-3 py-2 border-t border-border bg-background/50">
                                                        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                                                            {Object.entries(stepData).map(([key, value]) => {
                                                                if (key === 'skipped') return null;
                                                                const fieldDef = step?.fields?.find(f => f.name === key);
                                                                const label = fieldDef?.label || key.replace(/_/g, ' ');
                                                                const fieldType = fieldDef?.field_type;
                                                                if (fieldType === 'multiupload' && Array.isArray(value)) {
                                                                    return (
                                                                        <div key={key} className="col-span-2">
                                                                            <span className="text-xs text-muted-foreground capitalize">{label}</span>
                                                                            <div className="mt-1 space-y-1">
                                                                                {value.map((entry, i) => (
                                                                                    <div key={i} className="flex items-center gap-2 text-sm">
                                                                                        {entry.document_type && <span className="px-1.5 py-0.5 text-[10px] font-medium bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] rounded-sm">{entry.document_type}</span>}
                                                                                        {entry.file_id ? <a href={filesAPI.getUrl(entry.file_id)} target="_blank" rel="noopener noreferrer" className="text-[var(--brand-primary)] hover:underline text-xs">{entry.filename || 'Download'}</a> : <span className="text-muted-foreground text-xs">-</span>}
                                                                                    </div>
                                                                                ))}
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                }
                                                                if (fieldType === 'file' && value) {
                                                                    return (<div key={key}><span className="text-xs text-muted-foreground capitalize">{label}</span><div><a href={filesAPI.getUrl(value)} target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--brand-primary)] hover:underline">Download</a></div></div>);
                                                                }
                                                                const display = Array.isArray(value) ? value.join(', ') : typeof value === 'object' ? JSON.stringify(value) : String(value || '-');
                                                                return (<div key={key}><span className="text-xs text-muted-foreground capitalize">{label}</span><p className="text-sm font-medium">{display}</p></div>);
                                                            })}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                    {(!selectedUser.progress || selectedUser.progress.length === 0) && (
                                        <p className="text-sm text-muted-foreground p-3">No progress data yet</p>
                                    )}
                                </div>
                            </div>

                            {/* Submissions */}
                            {selectedUser.submissions?.length > 0 && (
                                <div>
                                    <h4 className="font-semibold mb-3">Partner Submissions</h4>
                                    <div className="space-y-2">
                                        {selectedUser.submissions.map((sub) => {
                                            const partner = partners.find(p => p.id === sub.partner_id);
                                            return (
                                                <div key={sub.id} className="p-3 bg-background rounded-sm">
                                                    <p className="font-medium">{partner?.name || 'Unknown Partner'}</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        Submitted: {new Date(sub.created_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* History Timeline */}
                            {selectedUser.history?.length > 0 && (
                                <div>
                                    <h4 className="font-semibold mb-3">Verlauf</h4>
                                    <div className="relative max-h-[250px] overflow-y-auto pr-2">
                                        <div className="absolute left-3 top-0 bottom-0 w-px bg-border" />
                                        {selectedUser.history.map((h, idx) => {
                                            const isDone = h.action === 'completed';
                                            const isWip = h.action === 'in_progress';
                                            return (
                                                <div key={idx} className="relative flex items-start gap-3 py-2">
                                                    <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${isDone ? 'bg-green-500 text-white' : isWip ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>
                                                        {isDone ? <Check size={10} /> : <ArrowRight size={10} />}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2 flex-wrap">
                                                            <span className="text-sm font-medium">{h.step_title}</span>
                                                            <span className={`px-1.5 py-0.5 text-[10px] rounded-sm ${isDone ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'}`}>
                                                                {isDone ? 'Abgeschlossen' : isWip ? 'In Bearbeitung' : h.action}
                                                            </span>
                                                        </div>
                                                        <p className="text-[10px] text-muted-foreground">{new Date(h.timestamp).toLocaleString('de-DE')}</p>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* Step Edit Dialog */}
            <StepDialog
                open={showStepDialog}
                onClose={() => { setShowStepDialog(false); setEditingStep(null); }}
                step={editingStep}
                onSave={handleSaveStep}
                existingSteps={steps}
                surveys={surveys}
                partners={partners}
                activeSurveyId={activeSurveyId}
                onSurveyChange={handleSurveyChange}
                t={t}
            />

            {/* Partner Edit Dialog */}
            <PartnerDialog
                open={showPartnerDialog}
                onClose={() => { setShowPartnerDialog(false); setEditingPartner(null); }}
                partner={editingPartner}
                onSave={handleSavePartner}
                allUsers={users}
                allPartners={partners}
                surveys={surveys}
                defaultUserFeeCents={siteSettings.stripe_partner_user_fee_cents || 0}
                t={t}
            />

            {/* Link User to Partner Dialog */}
            <LinkUserDialog
                open={!!showLinkDialog}
                onClose={() => setShowLinkDialog(null)}
                partner={showLinkDialog}
                users={users.filter(u => u.role === 'user')}
                onLink={handleLinkUser}
            />

            {/* Create User Dialog */}
            <CreateUserDialog
                open={showCreateUserDialog}
                onClose={() => setShowCreateUserDialog(false)}
                onSave={handleCreateUser}
                partners={partners}
                surveys={surveys}
                permissionGroups={permissionGroups}
                canManagePermissions={can('users.permissions.manage')}
                defaultSurveyId={activeSurveyId || surveys.find(s => s.is_default)?.id || surveys[0]?.id || ''}
                t={t}
            />
            {/* Confirm Dialog */}
            <Dialog open={!!confirmDialog} onOpenChange={() => setConfirmDialog(null)}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Bestaetigung</DialogTitle>
                    </DialogHeader>
                    <p className="text-sm text-muted-foreground py-4" data-testid="confirm-dialog-message">{confirmDialog?.message}</p>
                    <div className="flex justify-end gap-3">
                        <Button variant="outline" onClick={() => setConfirmDialog(null)} data-testid="confirm-dialog-cancel">Abbrechen</Button>
                        <Button className="bg-red-600 hover:bg-red-700 text-white" onClick={() => confirmDialog?.onConfirm()} data-testid="confirm-dialog-yes">Ja, loeschen</Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}

// ============ SUBCOMPONENTS ============

function StatCard({ label, value }) {
    return (
        <div className="bg-card border border-border rounded-sm p-6">
            <p className="text-sm text-muted-foreground mb-1">{label}</p>
            <p className="text-3xl font-black text-foreground">{value}</p>
        </div>
    );
}

function LandingPagesSection({ content, onChange, translations, onTransChange, surveys, onSave, saving }) {
    const [selectedId, setSelectedId] = useState('');
    const [cmsLang, setCmsLang] = useState('de');
    const pages = useMemo(() => content?.pages || [], [content]);
    const selectedPage = pages.find(p => p.id === selectedId) || pages[0] || null;
    const activeId = selectedPage?.id || '';

    useEffect(() => {
        if (!selectedId && pages[0]?.id) setSelectedId(pages[0].id);
        if (selectedId && pages.length && !pages.some(p => p.id === selectedId)) {
            setSelectedId(pages[0].id);
        }
    }, [pages, selectedId]);

    const fields = [
        { key: 'title', label: 'Interner Name', type: 'text', placeholder: 'FSP Pflege' },
        { key: 'path', label: 'URL-Pfad', type: 'text', placeholder: '/pflege' },
        { key: 'survey_slug', label: 'Survey-Slug', type: 'text', placeholder: 'pflege' },
        { key: 'partner_tags', label: 'Partner-Tags', type: 'text', placeholder: 'Pflege Sprachschulung,Pflege Arbeitgeber' },
        { key: 'eyebrow', label: 'Hero Eyebrow', type: 'text', placeholder: 'Pflege in Deutschland' },
        { key: 'hero_title', label: 'Hero Titel', type: 'text', placeholder: 'Anerkennung als Pflegefachkraft in Deutschland' },
        { key: 'hero_subtitle', label: 'Hero Text', type: 'textarea', placeholder: 'Kurzbeschreibung der Landingpage' },
        { key: 'hero_cta', label: 'CTA Text', type: 'text', placeholder: 'Jetzt registrieren' },
        { key: 'learn_more_label', label: 'Sekundärbutton', type: 'text', placeholder: 'Mehr erfahren' },
        { key: 'hero_image_url', label: 'Hero Bild URL', type: 'text', placeholder: 'https://...' },
        { key: 'stat_value', label: 'Stat Wert', type: 'text', placeholder: '100%' },
        { key: 'stat_label', label: 'Stat Label', type: 'text', placeholder: 'Von der Anerkennung bis zum Pflegejob' },
        { key: 'box1_title', label: 'Feature 1 Titel', type: 'text', placeholder: 'Geführte Anerkennung' },
        { key: 'box1_description', label: 'Feature 1 Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'box2_title', label: 'Feature 2 Titel', type: 'text', placeholder: 'Partner-Netzwerk' },
        { key: 'box2_description', label: 'Feature 2 Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'box3_title', label: 'Feature 3 Titel', type: 'text', placeholder: 'Fortschritt' },
        { key: 'box3_description', label: 'Feature 3 Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'about_eyebrow', label: 'About Eyebrow', type: 'text', placeholder: 'Für internationale Pflegekräfte' },
        { key: 'about_title', label: 'About Titel', type: 'text', placeholder: 'Ihr Weg in Deutschland' },
        { key: 'about_description', label: 'About Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'about_mission', label: 'About Mission', type: 'textarea', placeholder: 'Mission' },
        { key: 'partners_eyebrow', label: 'Partner Eyebrow', type: 'text', placeholder: 'Partner & Vorbereitung' },
        { key: 'partners_title', label: 'Partner Titel', type: 'text', placeholder: 'Unterstützung' },
        { key: 'partners_description', label: 'Partner Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'cta_title', label: 'CTA Titel', type: 'text', placeholder: 'Bereit?' },
        { key: 'cta_description', label: 'CTA Text', type: 'textarea', placeholder: 'Beschreibung' },
        { key: 'footer_logo_url', label: 'Footer Logo URL', type: 'text', placeholder: 'https://...' },
        { key: 'footer_text', label: 'Footer Text', type: 'text', placeholder: '© 2026 ...' },
    ];

    const updatePages = (nextPages) => onChange({ ...(content || {}), pages: nextPages });
    const updatePage = (patch) => {
        if (!selectedPage) return;
        updatePages(pages.map(page => page.id === selectedPage.id ? { ...page, ...patch } : page));
    };
    const updateTrans = (key, value) => {
        if (!activeId) return;
        onTransChange(prev => ({
            ...prev,
            en: {
                ...(prev?.en || {}),
                [activeId]: {
                    ...(prev?.en?.[activeId] || {}),
                    [key]: value,
                },
            },
        }));
    };
    const addPage = () => {
        const id = `landing-${Date.now()}`;
        const next = {
            id,
            title: 'Neue Landingpage',
            path: '/neue-seite',
            survey_slug: surveys[0]?.slug || '',
            partner_tags: '',
            hero_title: 'Neue Landingpage',
            hero_cta: 'Jetzt starten',
        };
        updatePages([...pages, next]);
        setSelectedId(id);
    };
    const removePage = () => {
        if (!selectedPage || selectedPage.path === '/') return;
        const nextPages = pages.filter(page => page.id !== selectedPage.id);
        updatePages(nextPages);
        setSelectedId(nextPages[0]?.id || '');
    };

    return (
        <div className="bg-card border border-border rounded-sm">
            <div className="p-4 border-b border-border flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                <div>
                    <h3 className="font-semibold text-foreground">Landingpages</h3>
                    <p className="text-xs text-muted-foreground mt-1">Pflege hier mehrere öffentliche Seiten mit eigener URL und Survey-Verknüpfung.</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    <Select value={activeId} onValueChange={setSelectedId}>
                        <SelectTrigger className="w-56 border-border rounded-sm">
                            <SelectValue placeholder="Landingpage wählen" />
                        </SelectTrigger>
                        <SelectContent>
                            {pages.map(page => (
                                <SelectItem key={page.id} value={page.id}>{page.title || page.path} {page.path}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <div className="flex border border-border rounded-sm overflow-hidden">
                        <button type="button" onClick={() => setCmsLang('de')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'de' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>DE</button>
                        <button type="button" onClick={() => setCmsLang('en')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'en' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>EN</button>
                    </div>
                    <Button type="button" variant="outline" onClick={addPage} className="border-border rounded-sm">
                        <Plus size={16} className="mr-2" /> Neu
                    </Button>
                    <Button type="button" variant="outline" onClick={removePage} disabled={!selectedPage || selectedPage.path === '/'} className="border-border rounded-sm">
                        <Trash size={16} className="mr-2" /> Entfernen
                    </Button>
                    <Button onClick={onSave} disabled={saving} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="cms-save-landingpages">
                        {saving ? 'Saving...' : 'Save'}
                    </Button>
                </div>
            </div>
            {selectedPage ? (
                <div className="p-4 grid md:grid-cols-2 gap-4">
                    {fields.map((field) => {
                        const value = cmsLang === 'de'
                            ? selectedPage[field.key] || ''
                            : translations?.en?.[activeId]?.[field.key] || '';
                        const onFieldChange = (nextValue) => {
                            if (cmsLang === 'de') updatePage({ [field.key]: nextValue });
                            else updateTrans(field.key, nextValue);
                        };
                        return (
                            <div key={field.key} className={field.type === 'textarea' ? 'md:col-span-2' : ''}>
                                <Label className="text-foreground">{field.label} <span className="text-xs text-muted-foreground">({cmsLang.toUpperCase()})</span></Label>
                                {field.type === 'textarea' ? (
                                    <Textarea value={value} onChange={(e) => onFieldChange(e.target.value)} placeholder={cmsLang === 'en' ? selectedPage[field.key] || field.placeholder : field.placeholder} className="mt-1 border-border rounded-sm min-h-[80px]" />
                                ) : field.key === 'survey_slug' ? (
                                    <Select value={value || '__none'} onValueChange={(next) => onFieldChange(next === '__none' ? '' : next)}>
                                        <SelectTrigger className="mt-1 border-border rounded-sm">
                                            <SelectValue placeholder="Survey wählen" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none">Kein Survey</SelectItem>
                                            {surveys.map(survey => (
                                                <SelectItem key={survey.id} value={survey.slug}>{survey.name} /s/{survey.slug}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                ) : (
                                    <Input value={value} onChange={(e) => onFieldChange(e.target.value)} placeholder={cmsLang === 'en' ? selectedPage[field.key] || field.placeholder : field.placeholder} className="mt-1 border-border rounded-sm" />
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="p-8 text-center text-muted-foreground">
                    Noch keine Landingpages angelegt.
                </div>
            )}
        </div>
    );
}

function CmsSection({ title, fields, content, onChange, translations, onTransChange, onSave, saving }) {
    const [cmsLang, setCmsLang] = useState('de');

    const setTrans = (lang, key, value) => {
        onTransChange(prev => ({ ...prev, [lang]: { ...(prev?.[lang] || {}), [key]: value } }));
    };

    return (
        <div className="bg-card border border-border rounded-sm">
            <div className="p-4 border-b border-border flex justify-between items-center">
                <h3 className="font-semibold text-foreground">{title}</h3>
                <div className="flex items-center gap-2">
                    <div className="flex border border-border rounded-sm overflow-hidden">
                        <button type="button" onClick={() => setCmsLang('de')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'de' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>DE</button>
                        <button type="button" onClick={() => setCmsLang('en')} className={`px-2.5 py-1 text-xs font-bold ${cmsLang === 'en' ? 'bg-[var(--brand-primary)] text-white' : 'bg-muted text-muted-foreground'}`}>EN</button>
                    </div>
                    <Button onClick={onSave} disabled={saving} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid={`cms-save-${title.toLowerCase().replace(/\s+/g, '-')}`}>
                        {saving ? 'Saving...' : 'Save'}
                    </Button>
                </div>
            </div>
            <div className="p-4 space-y-4">
                {cmsLang === 'de' ? (
                    fields.map((field) => (
                        <div key={field.key}>
                            <Label className="text-foreground">{field.label} <span className="text-xs text-muted-foreground">(DE)</span></Label>
                            {field.type === 'textarea' ? (
                                <Textarea value={content[field.key] || ''} onChange={(e) => onChange({ ...content, [field.key]: e.target.value })} placeholder={field.placeholder} className="mt-1 border-border rounded-sm min-h-[80px]" data-testid={`cms-field-${field.key}`} />
                            ) : (
                                <Input value={content[field.key] || ''} onChange={(e) => onChange({ ...content, [field.key]: e.target.value })} placeholder={field.placeholder} className="mt-1 border-border rounded-sm" data-testid={`cms-field-${field.key}`} />
                            )}
                        </div>
                    ))
                ) : (
                    fields.map((field) => (
                        <div key={field.key}>
                            <Label className="text-foreground">{field.label} <span className="text-xs font-bold text-blue-600">EN</span></Label>
                            {field.type === 'textarea' ? (
                                <Textarea value={translations?.en?.[field.key] || ''} onChange={(e) => setTrans('en', field.key, e.target.value)} placeholder={content[field.key] || field.placeholder} className="mt-1 border-border rounded-sm min-h-[80px]" data-testid={`cms-field-en-${field.key}`} />
                            ) : (
                                <Input value={translations?.en?.[field.key] || ''} onChange={(e) => setTrans('en', field.key, e.target.value)} placeholder={content[field.key] || field.placeholder} className="mt-1 border-border rounded-sm" data-testid={`cms-field-en-${field.key}`} />
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

function LinkUserDialog({ open, onClose, partner, users, onLink }) {
    const [search, setSearch] = useState('');
    const filtered = users
        .filter(u =>
            u.name.toLowerCase().includes(search.toLowerCase()) ||
            u.email.toLowerCase().includes(search.toLowerCase())
        )
        .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }) || a.email.localeCompare(b.email));

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Link User to {partner?.name}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <div className="relative">
                        <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Search users..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-9 border-border rounded-sm"
                            data-testid="link-user-search"
                        />
                    </div>
                    <div className="max-h-[300px] overflow-y-auto space-y-2">
                        {filtered.map((u) => (
                            <div key={u.id} className="flex items-center justify-between p-3 bg-background rounded-sm hover:bg-gray-100 transition-colors">
                                <div>
                                    <p className="font-medium text-sm">{u.name}</p>
                                    <p className="text-xs text-muted-foreground">{u.email}</p>
                                </div>
                                <Button
                                    size="sm"
                                    onClick={() => onLink(partner?.id, u.id)}
                                    className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white"
                                    data-testid={`link-select-user-${u.id}`}
                                >
                                    <LinkIcon size={14} className="mr-1" /> Link
                                </Button>
                            </div>
                        ))}
                        {filtered.length === 0 && (
                            <p className="text-sm text-center text-muted-foreground py-4">
                                No available users found
                            </p>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}

const STEP_STATUS_OPTIONS = [
    { value: 'pending', label: 'Ausstehend' },
    { value: 'in_progress', label: 'In Bearbeitung' },
    { value: 'completed', label: 'Abgeschlossen' },
    { value: 'rejected', label: 'Abgelehnt' },
    { value: 'skipped', label: 'Übersprungen' },
];

const CONDITION_OPERATOR_OPTIONS = [
    { value: 'status_is', label: 'Status ist' },
    { value: 'status_not', label: 'Status ist nicht' },
    { value: 'equals', label: 'Ist gleich' },
    { value: 'not_equals', label: 'Ist ungleich' },
    { value: 'one_of', label: 'Ist einer von' },
    { value: 'not_one_of', label: 'Ist keiner von' },
    { value: 'contains', label: 'Enthält Text' },
    { value: 'not_empty', label: 'Ist ausgefüllt' },
    { value: 'empty', label: 'Ist leer' },
    { value: 'has_upload', label: 'Dokument vorhanden' },
    { value: 'missing_upload', label: 'Dokument fehlt' },
];

const CONDITION_ACTION_OPTIONS = [
    { value: 'block', label: 'Schritt blockieren' },
    { value: 'hide', label: 'Schritt ausblenden' },
    { value: 'read_only', label: 'Schritt schreibschützen' },
    { value: 'auto_complete', label: 'Automatisch abschließen' },
    { value: 'allow_next', label: 'Zugriff erlauben' },
    { value: 'redirect', label: 'Zu anderem Schritt weiterleiten' },
];

function optionValue(option) {
    if (typeof option === 'string') return option;
    return option?.value ?? option?.label ?? '';
}

function optionLabel(option) {
    if (typeof option === 'string') return option;
    return option?.label ?? option?.value ?? '';
}

function stepFieldOptions(selectedStep, includeStatus = true) {
    const options = (selectedStep?.fields || []).map((field) => ({
        value: field.name,
        label: field.label || field.name,
        description: `${field.name} · ${field.field_type || 'Feld'}`,
        keywords: `${field.name} ${field.field_type || ''}`,
    }));
    if (includeStatus) {
        options.unshift({
            value: 'status',
            label: 'Schrittstatus',
            description: 'Systemfeld · pending, in_progress, completed …',
            keywords: 'status abgeschlossen ausstehend system',
        });
    }
    if (selectedStep?.step_type === 'milestone' && !options.some((option) => option.value === 'partner_uploads')) {
        options.push({
            value: 'partner_uploads',
            label: 'Partner-Dokumente',
            description: 'Systemfeld · vom Partner hochgeladene Dokumente',
            keywords: 'partner uploads dokumente system',
        });
    }
    return options;
}

function withFallbackOption(options, value, labelPrefix = 'Bestehender Wert') {
    if (value == null || value === '' || options.some((option) => String(option.value) === String(value))) return options;
    return [...options, { value: String(value), label: `${labelPrefix}: ${value}` }];
}

// Step Dialog Component
function StepDialog({ open, onClose, step, onSave, existingSteps, surveys = [], partners = [], activeSurveyId = '', onSurveyChange, t }) {
    const [formData, setFormData] = useState({
        title: '', description: '', order: existingSteps.length + 1,
        survey_id: activeSurveyId,
        step_type: 'form', fields: [], filter_tag: '', partner_user_fee_cents: null, skippable: false, skip_label: '',
        action_label: '', pending_message: '', complete_message: '',
        required_fields: [], required_uploads: [],
        field_mappings: [], conditions: [],
        duration_value: 0, duration_unit: 'days',
        email_on_enter: false, email_on_edit: false, email_on_leave: false, is_active: true
    });
    const [translations, setTranslations] = useState({});
    const [activeSection, setActiveSection] = useState('basic');

    useEffect(() => {
        if (step) {
            setFormData({
                title: step.title || '', description: step.description || '',
                order: step.order || existingSteps.length + 1,
                survey_id: step.survey_id || activeSurveyId,
                step_type: step.step_type || 'form', fields: step.fields || [],
                filter_tag: step.filter_tag || '', partner_user_fee_cents: step.partner_user_fee_cents ?? null, skippable: step.skippable || false,
                skip_label: step.skip_label || '', action_label: step.action_label || '',
                pending_message: step.pending_message || '', complete_message: step.complete_message || '',
                required_fields: step.required_fields || [], required_uploads: step.required_uploads || [],
                field_mappings: step.field_mappings || [], conditions: step.conditions || [],
                duration_value: step.duration_value ?? 0, duration_unit: step.duration_unit || 'days',
                email_on_enter: step.email_on_enter || false, email_on_edit: step.email_on_edit || false,
                email_on_leave: step.email_on_leave || false, is_active: step.is_active !== false
            });
            setTranslations(step.translations || {});
        } else {
            setFormData({
                title: '', description: '', order: existingSteps.length + 1,
                survey_id: activeSurveyId,
                step_type: 'form', fields: [], filter_tag: '', partner_user_fee_cents: null, skippable: false, skip_label: '',
                action_label: '', pending_message: '', complete_message: '',
                required_fields: [], required_uploads: [],
                field_mappings: [], conditions: [],
                duration_value: 0, duration_unit: 'days',
                email_on_enter: false, email_on_edit: false, email_on_leave: false, is_active: true
            });
            setTranslations({});
        }
    }, [step, existingSteps.length, activeSurveyId]);

    const handleSubmit = (e) => { e.preventDefault(); onSave({ ...formData, translations }); };

    const handleStepSurveyChange = (surveyId) => {
        setFormData({ ...formData, survey_id: surveyId });
        if (surveyId !== activeSurveyId) {
            onSurveyChange?.(surveyId);
        }
    };

    const setTrans = (lang, field, value) => {
        setTranslations(prev => ({
            ...prev,
            [lang]: { ...(prev[lang] || {}), [field]: value }
        }));
    };
    const handleFieldsChange = (fields) => {
        const requiredFieldNames = fields
            .filter((field) => field.required && !CONTENT_FIELD_TYPES.has(field.field_type) && field.field_type !== 'multiupload')
            .map((field) => field.name)
            .filter(Boolean);
        setFormData((current) => ({ ...current, fields, required_fields: requiredFieldNames }));
    };

    const sortedReferenceSteps = useMemo(
        () => [...existingSteps].sort((a, b) => a.order - b.order),
        [existingSteps],
    );
    const stepOptions = useMemo(() => sortedReferenceSteps.map((candidate) => ({
        value: String(candidate.order),
        label: `${candidate.order}. ${candidate.title}`,
        description: candidate.step_type === 'form'
            ? `${candidate.fields?.length || 0} Formularfelder`
            : candidate.step_type,
        keywords: `${candidate.id || ''} ${candidate.step_type || ''}`,
        disabled: candidate.id === step?.id,
    })), [sortedReferenceSteps, step?.id]);
    const surveyOptions = useMemo(() => surveys.map((survey) => ({
        value: survey.id,
        label: survey.name,
        description: `/s/${survey.slug}`,
        keywords: survey.slug,
    })), [surveys]);
    const partnerTagOptions = useMemo(() => {
        const counts = new Map();
        partners.forEach((partner) => (partner.tags || []).forEach((tag) => counts.set(tag, (counts.get(tag) || 0) + 1)));
        return [...counts.entries()].sort(([left], [right]) => left.localeCompare(right, 'de')).map(([tag, count]) => ({
            value: tag,
            label: tag,
            description: `${count} passende${count === 1 ? 'r Partner' : ' Partner'}`,
        }));
    }, [partners]);
    const currentFieldOptions = useMemo(
        () => (formData.fields || []).map((field) => ({
            value: field.name,
            label: field.label || field.name,
            description: `${field.name} · ${field.field_type || 'Feld'}`,
        })),
        [formData.fields],
    );
    const documentTypeOptions = useMemo(() => {
        const values = new Set(formData.required_uploads || []);
        [...sortedReferenceSteps, { fields: formData.fields }].forEach((candidate) => {
            (candidate.fields || []).forEach((field) => {
                if (field.field_type === 'multiupload') {
                    (field.options || []).forEach((option) => values.add(String(optionValue(option))));
                }
            });
        });
        return [...values].filter(Boolean).sort((a, b) => a.localeCompare(b, 'de')).map((value) => ({ value, label: value }));
    }, [formData.fields, formData.required_uploads, sortedReferenceSteps]);

    const findStepByOrder = (order) => sortedReferenceSteps.find((candidate) => candidate.order === Number(order));
    const findField = (selectedStep, fieldName) => (selectedStep?.fields || []).find((field) => field.name === fieldName);
    const sourceFieldOptions = (sourceOrder, currentValue) => withFallbackOption(
        stepFieldOptions(findStepByOrder(sourceOrder)),
        currentValue,
        'Nicht gefundenes Feld',
    );
    const conditionValueOptions = (condition) => {
        if (condition.field === 'status' || ['status_is', 'status_not'].includes(condition.operator)) {
            const current = Array.isArray(condition.value) ? condition.value : [condition.value];
            return current.reduce((options, value) => withFallbackOption(options, value), STEP_STATUS_OPTIONS);
        }
        const sourceStep = findStepByOrder(condition.source_step_order);
        const sourceField = findField(sourceStep, condition.field);
        const configured = (sourceField?.options || []).map((option) => ({
            value: String(optionValue(option)),
            label: String(optionLabel(option)),
        }));
        const base = ['has_upload', 'missing_upload'].includes(condition.operator)
            ? [...configured, ...documentTypeOptions.filter((option) => !configured.some((item) => item.value === option.value))]
            : configured;
        const current = Array.isArray(condition.value) ? condition.value : [condition.value];
        return current.reduce((options, value) => withFallbackOption(options, value), base);
    };
    const conditionOperatorOptions = (condition) => {
        const sourceField = findField(findStepByOrder(condition.source_step_order), condition.field);
        let allowed;
        if (condition.field === 'status') {
            allowed = ['status_is', 'status_not'];
        } else if (sourceField?.field_type === 'multiupload') {
            allowed = ['has_upload', 'missing_upload', 'not_empty', 'empty'];
        } else if ((sourceField?.options || []).length > 0 || sourceField?.field_type === 'decision') {
            allowed = ['equals', 'not_equals', 'one_of', 'not_one_of', 'not_empty', 'empty'];
        } else {
            allowed = ['equals', 'not_equals', 'one_of', 'not_one_of', 'contains', 'not_empty', 'empty'];
        }
        if (condition.operator && !allowed.includes(condition.operator)) allowed.push(condition.operator);
        return CONDITION_OPERATOR_OPTIONS.filter((option) => allowed.includes(option.value));
    };

    // Mapping helpers
    const addMapping = () => {
        const source = sortedReferenceSteps.find((candidate) => candidate.id !== step?.id) || sortedReferenceSteps[0];
        const sourceField = source?.fields?.[0]?.name || '';
        setFormData((current) => ({
            ...current,
            field_mappings: [...current.field_mappings, {
                source_step_order: source?.order || null,
                source_field: sourceField,
                target_field: current.fields?.[0]?.name || '',
            }],
        }));
    };
    const removeMapping = (i) => { setFormData((current) => ({ ...current, field_mappings: current.field_mappings.filter((_, idx) => idx !== i) })); };
    const updateMapping = (i, patch) => {
        setFormData((current) => {
            const mappings = [...current.field_mappings];
            mappings[i] = { ...mappings[i], ...patch };
            return { ...current, field_mappings: mappings };
        });
    };
    const changeMappingSource = (i, value) => {
        const source = findStepByOrder(value);
        updateMapping(i, {
            source_step_order: value ? Number(value) : null,
            source_field: source?.fields?.[0]?.name || '',
        });
    };

    // Condition helpers
    const defaultConditionLeaf = () => {
        const source = [...sortedReferenceSteps].reverse().find((candidate) => candidate.order < formData.order)
            || sortedReferenceSteps.find((candidate) => candidate.id !== step?.id)
            || sortedReferenceSteps[0];
        return { source_step_order: source?.order || null, field: 'status', operator: 'status_is', value: 'completed' };
    };
    const addCondition = () => {
        setFormData((current) => ({
            ...current,
            conditions: [...current.conditions, {
                ...defaultConditionLeaf(),
                action: 'block',
                target_step_order: null,
                message: 'Bitte schließen Sie zuerst den ausgewählten Schritt ab.',
            }],
        }));
    };
    const addConditionGroup = (groupKey) => setFormData((current) => ({
        ...current,
        conditions: [...current.conditions, {
            [groupKey]: [defaultConditionLeaf()], action: 'block', target_step_order: null,
            message: 'Die konfigurierte Bedingungsgruppe ist noch nicht erfüllt.',
        }],
    }));
    const removeCondition = (i) => { setFormData((current) => ({ ...current, conditions: current.conditions.filter((_, idx) => idx !== i) })); };
    const updateCondition = (i, patch) => {
        setFormData((current) => {
            const conditions = [...current.conditions];
            conditions[i] = { ...conditions[i], ...patch };
            return { ...current, conditions };
        });
    };
    const changeConditionSource = (i, value) => updateCondition(i, {
        source_step_order: value ? Number(value) : null,
        field: 'status',
        operator: 'status_is',
        value: 'completed',
    });
    const changeConditionField = (i, fieldName) => {
        const condition = formData.conditions[i];
        const selectedField = findField(findStepByOrder(condition.source_step_order), fieldName);
        if (fieldName === 'status') {
            updateCondition(i, { field: fieldName, operator: 'status_is', value: 'completed' });
        } else if (selectedField?.field_type === 'multiupload') {
            updateCondition(i, { field: fieldName, operator: 'has_upload', value: optionValue(selectedField.options?.[0]) || '' });
        } else {
            updateCondition(i, { field: fieldName, operator: 'equals', value: optionValue(selectedField?.options?.[0]) || '' });
        }
    };
    const changeConditionOperator = (i, operator) => {
        const currentValue = formData.conditions[i].value;
        if (['one_of', 'not_one_of'].includes(operator)) {
            updateCondition(i, { operator, value: Array.isArray(currentValue) ? currentValue : (currentValue ? [currentValue] : []) });
        } else if (['empty', 'not_empty'].includes(operator)) {
            updateCondition(i, { operator, value: '' });
        } else {
            updateCondition(i, { operator, value: Array.isArray(currentValue) ? (currentValue[0] || '') : currentValue });
        }
    };
    const updateConditionChild = (conditionIndex, groupKey, childIndex, patch) => {
        setFormData((current) => {
            const conditions = [...current.conditions];
            const children = [...conditions[conditionIndex][groupKey]];
            children[childIndex] = { ...children[childIndex], ...patch };
            conditions[conditionIndex] = { ...conditions[conditionIndex], [groupKey]: children };
            return { ...current, conditions };
        });
    };
    const addConditionChild = (conditionIndex, groupKey) => {
        setFormData((current) => {
            const conditions = [...current.conditions];
            conditions[conditionIndex] = { ...conditions[conditionIndex], [groupKey]: [...conditions[conditionIndex][groupKey], defaultConditionLeaf()] };
            return { ...current, conditions };
        });
    };
    const removeConditionChild = (conditionIndex, groupKey, childIndex) => {
        setFormData((current) => {
            const conditions = [...current.conditions];
            const children = conditions[conditionIndex][groupKey].filter((_, index) => index !== childIndex);
            if (!children.length) return current;
            conditions[conditionIndex] = { ...conditions[conditionIndex], [groupKey]: children };
            return { ...current, conditions };
        });
    };
    const changeConditionGroupType = (conditionIndex, oldKey, newKey) => {
        setFormData((current) => {
            const conditions = [...current.conditions];
            const condition = { ...conditions[conditionIndex], [newKey]: conditions[conditionIndex][oldKey] };
            delete condition[oldKey];
            conditions[conditionIndex] = condition;
            return { ...current, conditions };
        });
    };

    const sectionMeta = [
        { id: 'basic', label: t('step_basic'), description: 'Identität, Typ und Dauer', help: 'Legt Survey, sichtbare Texte, Position und Step-Typ fest. Der Step-Typ bestimmt die grundlegende Darstellung und Verarbeitung.' },
        ...((['partner_selection', 'partner_multiselection', 'milestone', 'display'].includes(formData.step_type))
            ? [{ id: 'type', label: t('step_type_settings'), description: 'Verhalten dieses Schritttyps', help: 'Enthält nur Einstellungen des aktuell gewählten Step-Typs, etwa Partnerfilter oder Statusmeldungen eines Meilensteins.' }]
            : []),
        ...(['form', 'decision'].includes(formData.step_type) ? [{ id: 'fields', label: t('step_fields'), description: 'Formular visuell aufbauen', count: formData.fields.length, help: 'Fügt Eingaben, Auswahlen, Uploads und Inhaltselemente hinzu. Reihenfolge und Breite bestimmen die spätere Nutzeransicht.' }] : []),
        { id: 'requirements', label: t('step_requirements'), description: 'Pflichtangaben und Dokumente', count: formData.required_fields.length + formData.required_uploads.length, help: 'Definiert serverseitig geprüfte Voraussetzungen für den Abschluss: ausgefüllte Felder und vorhandene Dokumenttypen.' },
        { id: 'mappings', label: t('step_mappings'), description: 'Daten automatisch übernehmen', count: formData.field_mappings.length, help: 'Kopiert einen Wert aus einem früheren Step in ein Feld dieses Steps und vermeidet dadurch Doppeleingaben.' },
        { id: 'conditions', label: t('step_conditions'), description: 'Sichtbarkeit und Zugriff steuern', count: formData.conditions.length, help: 'Wertet Status oder Feldwerte anderer Steps aus. Treffer können den Step verbergen, blockieren, automatisch abschließen oder umleiten.' },
        { id: 'notifications', label: t('step_notifications'), description: 'E-Mail-Auslöser und Inhalte', help: 'Versendet E-Mails beim Eintritt, bei Bearbeitung oder Abschluss. Ohne individuellen Text greift die globale Standardvorlage.' },
        { id: 'translations', label: 'Englisch', description: 'Übersetzte Texte pflegen', help: 'Hinterlegt englische Varianten sichtbarer Texte. Leere Werte fallen auf den deutschen Originaltext zurück.' },
    ];
    const currentSection = sectionMeta.find((section) => section.id === activeSection) || sectionMeta[0];
    const previousStep = [...sortedReferenceSteps].reverse().find((candidate) => candidate.order < formData.order);
    const uploadPresetStep = sortedReferenceSteps.find((candidate) => (candidate.fields || []).some((field) => field.field_type === 'multiupload'));
    const uploadPresetField = (uploadPresetStep?.fields || []).find((field) => field.field_type === 'multiupload');
    const choicePresetStep = sortedReferenceSteps.find((candidate) => (candidate.fields || []).some((field) => (field.options || []).length > 0 && field.field_type !== 'multiupload'));
    const choicePresetField = (choicePresetStep?.fields || []).find((field) => (field.options || []).length > 0 && field.field_type !== 'multiupload');

    const addConditionPreset = (preset) => {
        setFormData((current) => ({
            ...current,
            conditions: [...current.conditions, { target_step_order: null, message: '', ...preset }],
        }));
    };

    useEffect(() => {
        if (activeSection === 'fields' && !['form', 'decision'].includes(formData.step_type)) setActiveSection('basic');
        if (activeSection === 'type' && !['partner_selection', 'partner_multiselection', 'milestone', 'display'].includes(formData.step_type)) setActiveSection('basic');
    }, [activeSection, formData.step_type]);

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent
                className="flex h-[94vh] max-h-[980px] max-w-[96vw] flex-col gap-0 overflow-hidden p-0 xl:max-w-[1500px]"
                data-testid="step-editor-dialog"
                onEscapeKeyDown={(event) => {
                    if (document.querySelector('[data-entity-picker-open="true"], [role="tooltip"]')) event.preventDefault();
                }}
            >
                <DialogHeader className="border-b border-border px-6 py-5 pr-16">
                    <DialogTitle className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                        <span>{step ? t('step_edit') : t('step_create')}</span>
                        <span className="text-[var(--brand-primary)]" data-testid="step-editor-title">
                            {formData.title || (step ? `Step #${formData.order || '–'}` : 'Neuer Schritt')}
                        </span>
                    </DialogTitle>
                    <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
                        <span>Position {formData.order || '–'}</span>
                        <span aria-hidden="true">·</span>
                        <span>{formData.step_type}</span>
                    </div>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
                    <div className="grid min-h-0 flex-1 md:grid-cols-[240px_minmax(0,1fr)]">
                        <aside className="border-b border-border bg-muted/35 p-3 md:border-b-0 md:border-r" aria-label="Editor-Bereiche">
                            <nav className="grid grid-cols-2 gap-1 md:grid-cols-1">
                                {sectionMeta.map((section) => (
                                    <button
                                        key={section.id}
                                        type="button"
                                        onClick={() => setActiveSection(section.id)}
                                        className={`rounded-lg border px-3 py-2.5 text-left transition-colors ${activeSection === section.id ? 'border-[var(--brand-primary)] bg-card text-foreground shadow-sm' : 'border-transparent text-muted-foreground hover:bg-card hover:text-foreground'}`}
                                        data-testid={`step-section-${section.id}`}
                                    >
                                        <span className="flex items-center justify-between gap-2 text-sm font-semibold">
                                            <span className="inline-flex items-center gap-1.5">{section.label}<HelpTooltip content={section.help} side="right" testId={`step-section-help-${section.id}`} /></span>
                                            {section.count > 0 && <span className="rounded-full bg-[var(--brand-primary)]/10 px-2 py-0.5 text-[11px] text-[var(--brand-primary)]">{section.count}</span>}
                                        </span>
                                        <span className="mt-0.5 hidden text-[11px] leading-4 text-muted-foreground md:block">{section.description}</span>
                                    </button>
                                ))}
                            </nav>
                        </aside>
                        <section className="min-h-0 overflow-y-auto px-5 py-5 md:px-7" data-testid={`step-section-panel-${activeSection}`}>
                            <div className="mb-5">
                                <h3 className="inline-flex items-center gap-2 text-lg font-semibold text-foreground">{currentSection.label}<HelpTooltip content={currentSection.help} testId={`step-panel-help-${currentSection.id}`} /></h3>
                                <p className="mt-1 text-sm text-muted-foreground">{currentSection.description}</p>
                            </div>
                    {/* BASIC */}
                    {activeSection === 'basic' && (
                        <div className="space-y-4">
                            <div>
                                <Label><HelpLabel help="Ordnet den Step einem Survey zu. Reihenfolge, Progress und Conditions gelten nur innerhalb dieses Surveys.">Survey</HelpLabel></Label>
                                <div className="mt-1">
                                    <SearchableSelect
                                        options={surveyOptions}
                                        value={formData.survey_id || activeSurveyId}
                                        onChange={handleStepSurveyChange}
                                        placeholder="Survey wählen"
                                        searchPlaceholder="Survey nach Name oder URL suchen …"
                                        testId="step-survey-select"
                                    />
                                </div>
                            </div>
                            <div><Label><HelpLabel help="Sichtbarer Name in Journey, Navigation, Adminansicht und E-Mails.">{t('step_title')}</HelpLabel></Label><Input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} className="mt-1" required data-testid="step-title-input" /></div>
                            <div><Label><HelpLabel help="Erklärt Nutzern Ziel und Inhalt des Steps. Die Beschreibung kann auch in Benachrichtigungen verwendet werden.">{t('step_description')}</HelpLabel></Label><Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="mt-1" required data-testid="step-description-input" /></div>
                            <div className="grid grid-cols-2 gap-4">
                                <div><Label><HelpLabel help="Position innerhalb des aktiven Surveys. Conditions referenzieren Steps über diese Nummer.">{t('step_order')}</HelpLabel></Label><Input type="number" min="1" value={formData.order} onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })} className="mt-1" required /></div>
                                <div><Label><HelpLabel help="Formular sammelt Daten; Entscheidung zeigt Auswahlkarten; Partner-Typen vermitteln Partner; Meilenstein bildet Status ab; Anzeige zeigt Information.">{t('step_type')}</HelpLabel></Label><Select value={formData.step_type} onValueChange={(val) => setFormData({ ...formData, step_type: val })}><SelectTrigger className="mt-1" data-testid="step-type-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="form">{t('step_type_form')}</SelectItem><SelectItem value="decision">Entscheidung (2 Buttons)</SelectItem><SelectItem value="partner_selection">{t('step_type_partner')}</SelectItem><SelectItem value="partner_multiselection">{t('step_type_partner_multi')}</SelectItem><SelectItem value="milestone">{t('step_type_milestone')}</SelectItem><SelectItem value="display">{t('step_type_display')}</SelectItem></SelectContent></Select></div>
                            </div>
                            <div className="flex items-center justify-between"><Label><HelpLabel help="Inaktive Steps werden nicht ausgeliefert und zählen nicht zum Fortschritt.">{t('step_active')}</HelpLabel></Label><Switch checked={formData.is_active} onCheckedChange={(val) => setFormData({ ...formData, is_active: val })} /></div>
                            <div className="flex items-center justify-between"><Label><HelpLabel help="Erlaubt Nutzern, den Step ohne reguläre Eingaben als übersprungen abzuschließen.">{t('step_skippable')}</HelpLabel></Label><Switch checked={formData.skippable} onCheckedChange={(val) => setFormData({ ...formData, skippable: val })} /></div>
                            {formData.skippable && <div><Label>{t('step_skip_label')}</Label><Input value={formData.skip_label} onChange={(e) => setFormData({ ...formData, skip_label: e.target.value })} className="mt-1" placeholder="Vorerst überspringen" /></div>}
                            <div className="border-t border-border pt-4 mt-2">
                                <Label className="text-sm font-semibold"><HelpLabel help="Schätzwert für die ETA-Berechnung. Freischaltungen werden ausschließlich über Conditions gesteuert.">{t('step_duration')}</HelpLabel></Label>
                                <p className="text-xs text-muted-foreground mb-2">{t('step_duration_desc')}</p>
                                <div className="grid grid-cols-2 gap-4">
                                    <div><Label>{t('step_duration_value')}</Label><Input type="number" min="0" value={formData.duration_value} onChange={(e) => setFormData({ ...formData, duration_value: parseInt(e.target.value) || 0 })} className="mt-1" data-testid="step-duration-value" /></div>
                                    <div><Label>{t('step_duration_unit')}</Label><Select value={formData.duration_unit} onValueChange={(val) => setFormData({ ...formData, duration_unit: val })}><SelectTrigger className="mt-1" data-testid="step-duration-unit"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="days">{t('step_days')}</SelectItem><SelectItem value="weeks">{t('step_weeks')}</SelectItem><SelectItem value="months">{t('step_months')}</SelectItem><SelectItem value="years">{t('step_years')}</SelectItem></SelectContent></Select></div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TYPE SETTINGS */}
                    {activeSection === 'type' && (
                        <div className="space-y-4">
                            {(formData.step_type === 'partner_selection' || formData.step_type === 'partner_multiselection') && (
                                <div className="space-y-4">
                                  <div>
                                    <Label><HelpLabel help="Zeigt nur aktive Partner mit exakt diesem Tag. Bei Mehrfachauswahl können mehrere passende Partner gewählt werden.">{t('step_filter_tag')}</HelpLabel></Label>
                                    <p className="mb-2 mt-1 text-xs text-muted-foreground">Nur Partner mit diesem Tag werden angeboten. Neue Tags können direkt angelegt werden.</p>
                                    <SearchableSelect
                                        options={withFallbackOption(partnerTagOptions, formData.filter_tag)}
                                        value={formData.filter_tag}
                                        onChange={(value) => setFormData({ ...formData, filter_tag: value })}
                                        placeholder="Partner-Tag auswählen"
                                        searchPlaceholder="Partner-Tags durchsuchen …"
                                        testId="step-filter-tag"
                                        allowCustom
                                    />
                                  </div>
                                  <div>
                                    <Label>Nutzergebühr für diesen Step in Cent</Label>
                                    <Input type="number" min="0" value={formData.partner_user_fee_cents ?? ''} onChange={(event) => setFormData({...formData, partner_user_fee_cents: event.target.value === '' ? null : Number(event.target.value)})} placeholder="Globalen Standard verwenden" data-testid="step-user-fee-cents" />
                                    <p className="mt-1 text-xs text-muted-foreground">Leer übernimmt den globalen Standard. Auch 0 Cent ist eine explizite Überschreibung.</p>
                                  </div>
                                </div>
                            )}
                            {(formData.step_type === 'display' || formData.step_type === 'milestone') && (
                                <>
                                    <div><Label><HelpLabel help="Text, solange der Meilenstein noch offen oder die Anzeige noch nicht erledigt ist.">{t('step_pending_msg')}</HelpLabel></Label><Textarea value={formData.pending_message} onChange={(e) => setFormData({ ...formData, pending_message: e.target.value })} className="mt-1" /></div>
                                    <div><Label><HelpLabel help="Text, nachdem der Meilenstein oder Anzeigeschritt abgeschlossen wurde.">{t('step_complete_msg')}</HelpLabel></Label><Textarea value={formData.complete_message} onChange={(e) => setFormData({ ...formData, complete_message: e.target.value })} className="mt-1" /></div>
                                </>
                            )}
                            {formData.step_type === 'display' && <div><Label>{t('step_action_label')}</Label><Input value={formData.action_label} onChange={(e) => setFormData({ ...formData, action_label: e.target.value })} className="mt-1" /></div>}
                        </div>
                    )}

                    {/* FIELDS */}
                    {activeSection === 'fields' && ['form', 'decision'].includes(formData.step_type) && (
                        <SurveyFormBuilder fields={formData.fields} onChange={handleFieldsChange} />
                    )}

                    {/* REQUIREMENTS */}
                    {activeSection === 'requirements' && (
                        <div className="space-y-4">
                            <div className="rounded-lg border border-border p-4">
                                <Label className="block"><HelpLabel help="Diese internen Feldnamen werden beim Abschluss serverseitig geprüft. Leere Werte verhindern den Abschluss.">Pflichtfelder</HelpLabel></Label>
                                <p className="mb-3 mt-1 text-xs text-muted-foreground">Mehrere Formularfelder durchsuchen und auswählen. Nutzer können den Schritt erst abschließen, wenn alle ausgewählten Felder ausgefüllt sind.</p>
                                <SearchableMultiSelect
                                    options={formData.required_fields.reduce((options, value) => withFallbackOption(options, value), currentFieldOptions)}
                                    values={formData.required_fields}
                                    onChange={(values) => setFormData((current) => ({
                                        ...current,
                                        required_fields: values,
                                        fields: current.fields.map((field) => CONTENT_FIELD_TYPES.has(field.field_type) || field.field_type === 'multiupload'
                                            ? field
                                            : { ...field, required: values.includes(field.name) }),
                                    }))}
                                    placeholder={formData.fields.length > 0 ? 'Pflichtfelder auswählen' : 'Noch keine Formularfelder definiert'}
                                    searchPlaceholder="Formularfelder durchsuchen …"
                                    testId="step-required-fields"
                                />
                            </div>
                            <div className="rounded-lg border border-border p-4">
                                <Label className="block"><HelpLabel help="Prüft Dokumentlisten auf Uploads mit passendem document_type. Alle ausgewählten Typen müssen vorhanden sein.">Erforderliche Dokumenttypen</HelpLabel></Label>
                                <p className="mb-3 mt-1 text-xs text-muted-foreground">Dokumenttypen aus Upload-Feldern auswählen oder einen neuen Namen eingeben. Mehrfachauswahl ist möglich.</p>
                                <SearchableMultiSelect
                                    options={documentTypeOptions}
                                    values={formData.required_uploads}
                                    onChange={(values) => setFormData({ ...formData, required_uploads: values })}
                                    placeholder="Dokumenttypen auswählen"
                                    searchPlaceholder="Dokumenttyp suchen oder neu eingeben …"
                                    testId="step-required-uploads"
                                    allowCustom
                                />
                            </div>
                        </div>
                    )}

                    {/* MAPPINGS */}
                    {activeSection === 'mappings' && (
                        <div className="space-y-4">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <Label><HelpLabel help="Mappings lesen einen gespeicherten Wert aus dem Quell-Step und schreiben ihn als Vorbelegung in das Zielfeld dieses Steps.">Automatische Feldübernahme</HelpLabel></Label>
                                    <p className="mt-1 text-xs text-muted-foreground">Übernimmt einen Wert aus einem anderen Schritt in ein Feld dieses Schritts.</p>
                                </div>
                                <Button type="button" variant="outline" size="sm" onClick={addMapping} data-testid="add-field-mapping"><Plus size={14} className="mr-1" /> Mapping</Button>
                            </div>
                            {formData.field_mappings.map((m, i) => (
                                <div key={i} className="rounded-lg border border-border bg-card p-4" data-testid={`field-mapping-${i}`}>
                                    <div className="mb-3 flex items-center justify-between">
                                        <p className="text-sm font-semibold">Mapping {i + 1}</p>
                                        <Button type="button" variant="ghost" size="sm" onClick={() => removeMapping(i)} className="h-8 text-red-500"><Trash size={14} className="mr-1" /> Entfernen</Button>
                                    </div>
                                    <div className="grid gap-3 lg:grid-cols-3">
                                        <div>
                                            <Label className="text-xs"><HelpLabel help="Step, dessen bereits gespeicherte Nutzerdaten gelesen werden.">Wert aus Schritt</HelpLabel></Label>
                                            <SearchableSelect
                                                options={withFallbackOption(stepOptions, m.source_step_order, 'Nicht gefundener Schritt')}
                                                value={m.source_step_order == null ? '' : String(m.source_step_order)}
                                                onChange={(value) => changeMappingSource(i, value)}
                                                placeholder="Quell-Schritt auswählen"
                                                searchPlaceholder="Schritt suchen …"
                                                testId={`mapping-source-step-${i}`}
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs"><HelpLabel help="Technischer Feldname, aus dem der Wert übernommen wird.">Quellfeld</HelpLabel></Label>
                                            <SearchableSelect
                                                options={sourceFieldOptions(m.source_step_order, m.source_field).filter((option) => option.value !== 'status')}
                                                value={m.source_field || ''}
                                                onChange={(value) => updateMapping(i, { source_field: value })}
                                                placeholder="Quellfeld auswählen"
                                                searchPlaceholder="Feld suchen …"
                                                testId={`mapping-source-field-${i}`}
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-xs"><HelpLabel help="Feld dieses Steps, das mit dem gelesenen Wert vorbelegt wird.">Zielfeld in diesem Schritt</HelpLabel></Label>
                                            <SearchableSelect
                                                options={withFallbackOption(currentFieldOptions, m.target_field, 'Nicht gefundenes Feld')}
                                                value={m.target_field || ''}
                                                onChange={(value) => updateMapping(i, { target_field: value })}
                                                placeholder="Zielfeld auswählen"
                                                searchPlaceholder="Zielfeld suchen …"
                                                testId={`mapping-target-field-${i}`}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {formData.field_mappings.length === 0 && <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">Keine Mappings konfiguriert. Mit „Mapping“ können Daten ohne erneute Eingabe übernommen werden.</p>}
                        </div>
                    )}

                    {/* CONDITIONS */}
                    {activeSection === 'conditions' && (
                        <div className="space-y-4">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <Label><HelpLabel help="Jede Regel liest einen anderen Step. Mehrere Regeln werden unabhängig ausgewertet; jede zutreffende Aktion kann auf diesen Step wirken.">Regeln für diesen Schritt</HelpLabel></Label>
                                    <p className="mt-1 text-xs text-muted-foreground">Eine Regel liest den Status oder ein Feld eines anderen Schritts und führt bei einem Treffer die gewählte Aktion aus.</p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <Button type="button" variant="outline" size="sm" onClick={addCondition} data-testid="add-condition"><Plus size={14} className="mr-1" /> Einzelregel</Button>
                                    <Button type="button" variant="outline" size="sm" onClick={() => addConditionGroup('all_of')} data-testid="add-condition-all"><Plus size={14} className="mr-1" /> UND-Gruppe</Button>
                                    <Button type="button" variant="outline" size="sm" onClick={() => addConditionGroup('any_of')} data-testid="add-condition-any"><Plus size={14} className="mr-1" /> ODER-Gruppe</Button>
                                </div>
                            </div>

                            {/* Presets */}
                            <div className="rounded-lg border border-[var(--brand-primary)]/20 bg-[var(--brand-primary)]/5 p-4">
                                <p className="mb-2 text-xs font-semibold text-[var(--brand-primary)]">Schnellstart mit sinnvoll vorbelegten Regeln</p>
                                <div className="flex flex-wrap gap-2">
                                    {[
                                        previousStep && { label: 'Vorherigen Schritt voraussetzen', preset: { source_step_order: previousStep.order, field: 'status', operator: 'status_not', value: 'completed', action: 'block', message: `Bitte schließen Sie zuerst „${previousStep.title}“ ab.` } },
                                        uploadPresetStep && uploadPresetField && { label: 'Fehlendes Dokument blockiert', preset: { source_step_order: uploadPresetStep.order, field: uploadPresetField.name, operator: 'missing_upload', value: optionValue(uploadPresetField.options?.[0]) || '', action: 'block', message: 'Bitte laden Sie zuerst das erforderliche Dokument hoch.' } },
                                        choicePresetStep && choicePresetField && { label: 'Mehrere Antworten zulassen', preset: { source_step_order: choicePresetStep.order, field: choicePresetField.name, operator: 'one_of', value: (choicePresetField.options || []).slice(0, 2).map(optionValue), action: 'allow_next', message: '' } },
                                        previousStep && { label: 'Nach Abschluss weiterleiten', preset: { source_step_order: previousStep.order, field: 'status', operator: 'status_is', value: 'completed', action: 'redirect', target_step_order: sortedReferenceSteps.find((candidate) => candidate.order > formData.order)?.order || null, message: '' } },
                                    ].filter(Boolean).map((p, i) => (
                                        <button key={p.label} type="button" onClick={() => addConditionPreset(p.preset)}
                                            className="rounded-md border border-border bg-card px-2.5 py-1.5 text-xs transition-colors hover:border-[var(--brand-primary)] hover:bg-muted" data-testid={`condition-preset-${i}`}>
                                            {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {formData.conditions.map((c, i) => {
                                const valueOptions = conditionValueOptions(c);
                                const actionLabel = CONDITION_ACTION_OPTIONS.find((option) => option.value === c.action)?.label || c.action;
                                const compoundKey = Array.isArray(c.all_of) ? 'all_of' : Array.isArray(c.any_of) ? 'any_of' : null;
                                if (compoundKey) {
                                    const children = c[compoundKey];
                                    return (
                                        <div key={i} className="rounded-lg border border-border bg-card p-4 shadow-sm" data-testid={`condition-card-${i}`}>
                                            <div className="mb-4 flex items-start justify-between gap-3">
                                                <div>
                                                    <p className="text-sm font-semibold">Regel {i + 1} · {compoundKey === 'all_of' ? 'UND-Gruppe' : 'ODER-Gruppe'}</p>
                                                    <p className="mt-0.5 text-xs text-muted-foreground">
                                                        {compoundKey === 'all_of' ? 'Alle Teilbedingungen müssen zutreffen.' : 'Mindestens eine Teilbedingung muss zutreffen.'} Bei Treffer: {actionLabel}
                                                    </p>
                                                </div>
                                                <Button type="button" variant="ghost" size="sm" onClick={() => removeCondition(i)} className="h-8 text-red-500"><Trash size={14} className="mr-1" /> Entfernen</Button>
                                            </div>
                                            <div className="mb-4 flex flex-wrap items-end gap-3 rounded-md bg-muted/30 p-3">
                                                <div className="min-w-48">
                                                    <Label className="text-xs">Gruppierung</Label>
                                                    <Select value={compoundKey} onValueChange={(value) => changeConditionGroupType(i, compoundKey, value)}>
                                                        <SelectTrigger data-testid={`condition-group-type-${i}`}><SelectValue /></SelectTrigger>
                                                        <SelectContent><SelectItem value="all_of">UND – alle müssen zutreffen</SelectItem><SelectItem value="any_of">ODER – eine muss zutreffen</SelectItem></SelectContent>
                                                    </Select>
                                                </div>
                                                <Button type="button" variant="outline" size="sm" onClick={() => addConditionChild(i, compoundKey)} data-testid={`condition-add-child-${i}`}><Plus size={14} className="mr-1" /> Teilbedingung</Button>
                                            </div>
                                            <div className="space-y-2" data-testid={`condition-compound-${i}`}>
                                                {children.map((child, childIndex) => {
                                                    const source = findStepByOrder(child.source_step_order);
                                                    const operator = CONDITION_OPERATOR_OPTIONS.find((option) => option.value === child.operator)?.label || child.operator || '–';
                                                    const value = ['has_upload', 'missing_upload'].includes(child.operator) && (child.value == null || child.value === '')
                                                        ? 'beliebiges Dokument'
                                                        : Array.isArray(child.value) ? child.value.join(', ') : String(child.value ?? '–');
                                                    const childValueOptions = conditionValueOptions(child);
                                                    const updateChildSource = (sourceValue) => updateConditionChild(i, compoundKey, childIndex, {
                                                        source_step_order: sourceValue ? Number(sourceValue) : null, field: 'status', operator: 'status_is', value: 'completed',
                                                    });
                                                    const updateChildField = (fieldName) => {
                                                        const selectedField = findField(findStepByOrder(child.source_step_order), fieldName);
                                                        if (fieldName === 'status') updateConditionChild(i, compoundKey, childIndex, { field: fieldName, operator: 'status_is', value: 'completed' });
                                                        else if (selectedField?.field_type === 'multiupload' || fieldName === 'partner_uploads') updateConditionChild(i, compoundKey, childIndex, { field: fieldName, operator: 'has_upload', value: '' });
                                                        else updateConditionChild(i, compoundKey, childIndex, { field: fieldName, operator: 'equals', value: optionValue(selectedField?.options?.[0]) || '' });
                                                    };
                                                    const updateChildOperator = (nextOperator) => {
                                                        let nextValue = child.value;
                                                        if (['one_of', 'not_one_of'].includes(nextOperator)) nextValue = Array.isArray(nextValue) ? nextValue : (nextValue ? [nextValue] : []);
                                                        else if (Array.isArray(nextValue)) nextValue = nextValue[0] || '';
                                                        if (['empty', 'not_empty', 'has_upload', 'missing_upload'].includes(nextOperator)) nextValue = '';
                                                        updateConditionChild(i, compoundKey, childIndex, { operator: nextOperator, value: nextValue });
                                                    };
                                                    return (
                                                        <details key={childIndex} className="group rounded-md border border-border bg-card" data-testid={`condition-compound-${i}-${childIndex}`} open={childIndex === 0}>
                                                            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-3 text-xs hover:bg-muted/40">
                                                                <span><strong>Teilbedingung {childIndex + 1}</strong> · #{child.source_step_order} {source?.title || 'Unbekannt'} · {child.field || 'Status'} · {operator} · {value}</span>
                                                                <span className="text-muted-foreground group-open:rotate-180">⌄</span>
                                                            </summary>
                                                            <div className="grid gap-3 border-t border-border p-3 lg:grid-cols-2">
                                                                <div><Label className="text-xs">1. Quell-Step</Label><SearchableSelect options={withFallbackOption(stepOptions, child.source_step_order, 'Nicht gefundener Schritt')} value={child.source_step_order == null ? '' : String(child.source_step_order)} onChange={updateChildSource} placeholder="Quell-Step auswählen" searchPlaceholder="Step suchen …" testId={`condition-child-source-${i}-${childIndex}`} /></div>
                                                                <div><Label className="text-xs">2. Status oder Feld</Label><SearchableSelect options={sourceFieldOptions(child.source_step_order, child.field)} value={child.field || ''} onChange={updateChildField} placeholder="Feld auswählen" searchPlaceholder="Feld suchen …" testId={`condition-child-field-${i}-${childIndex}`} /></div>
                                                                <div><Label className="text-xs">3. Vergleich</Label><Select value={child.operator} onValueChange={updateChildOperator}><SelectTrigger data-testid={`condition-child-operator-${i}-${childIndex}`}><SelectValue /></SelectTrigger><SelectContent>{conditionOperatorOptions(child).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select></div>
                                                                <div><Label className="text-xs">4. Vergleichswert</Label>{['empty', 'not_empty'].includes(child.operator) ? <div className="flex min-h-10 items-center rounded-md border border-dashed border-border bg-muted/40 px-3 text-sm text-muted-foreground">Kein Wert erforderlich</div> : ['one_of', 'not_one_of'].includes(child.operator) ? <SearchableMultiSelect options={childValueOptions} values={Array.isArray(child.value) ? child.value : (child.value ? [child.value] : [])} onChange={(values) => updateConditionChild(i, compoundKey, childIndex, { value: values })} placeholder="Werte auswählen" searchPlaceholder="Werte suchen …" testId={`condition-child-values-${i}-${childIndex}`} allowCustom /> : childValueOptions.length > 0 ? <SearchableSelect options={childValueOptions} value={Array.isArray(child.value) ? (child.value[0] || '') : (child.value || '')} onChange={(nextValue) => updateConditionChild(i, compoundKey, childIndex, { value: nextValue })} placeholder="Wert auswählen" searchPlaceholder="Wert suchen …" testId={`condition-child-value-${i}-${childIndex}`} allowCustom /> : <Input value={child.value || ''} onChange={(event) => updateConditionChild(i, compoundKey, childIndex, { value: event.target.value })} data-testid={`condition-child-value-input-${i}-${childIndex}`} />}</div>
                                                                <div className="lg:col-span-2 flex justify-end"><Button type="button" variant="ghost" size="sm" disabled={children.length <= 1} onClick={() => removeConditionChild(i, compoundKey, childIndex)} className="text-red-500" data-testid={`condition-remove-child-${i}-${childIndex}`}><Trash size={14} className="mr-1" /> Teilbedingung entfernen</Button></div>
                                                            </div>
                                                        </details>
                                                    );
                                                })}
                                            </div>
                                            <div className="mt-4 grid gap-3 border-t border-border pt-4 lg:grid-cols-2">
                                                <div>
                                                    <Label className="text-xs">Aktion bei Treffer</Label>
                                                    <Select value={c.action} onValueChange={(value) => updateCondition(i, { action: value, target_step_order: value === 'redirect' ? c.target_step_order : null })}>
                                                        <SelectTrigger className="min-h-10" data-testid={`condition-action-${i}`}><SelectValue /></SelectTrigger>
                                                        <SelectContent>{CONDITION_ACTION_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
                                                    </Select>
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Hinweis für Nutzer</Label>
                                                    <Textarea value={c.message || ''} onChange={(event) => updateCondition(i, { message: event.target.value })} className="mt-1 min-h-[68px]" data-testid={`condition-message-${i}`} />
                                                </div>
                                            </div>
                                        </div>
                                    );
                                }
                                return (
                                    <div key={i} className="rounded-lg border border-border bg-card p-4 shadow-sm" data-testid={`condition-card-${i}`}>
                                        <div className="mb-4 flex items-start justify-between gap-3">
                                            <div>
                                                <p className="text-sm font-semibold">Regel {i + 1}</p>
                                                <p className="mt-0.5 text-xs text-muted-foreground">Bei Treffer: {actionLabel}</p>
                                            </div>
                                            <Button type="button" variant="ghost" size="sm" onClick={() => removeCondition(i)} className="h-8 text-red-500"><Trash size={14} className="mr-1" /> Entfernen</Button>
                                        </div>

                                        <div className="grid gap-3 lg:grid-cols-2">
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Quell-Step, dessen Status oder gespeicherte Felddaten ausgewertet werden.">1. Schritt auswählen</HelpLabel></Label>
                                                <SearchableSelect
                                                    options={withFallbackOption(stepOptions, c.source_step_order, 'Nicht gefundener Schritt')}
                                                    value={c.source_step_order == null ? '' : String(c.source_step_order)}
                                                    onChange={(value) => changeConditionSource(i, value)}
                                                    placeholder="Quell-Schritt auswählen"
                                                    searchPlaceholder="Schritt nach Nummer, Titel oder Typ suchen …"
                                                    testId={`condition-source-step-${i}`}
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Status prüft pending, in_progress oder completed. Ein Feld prüft den konkreten gespeicherten Nutzerwert.">2. Status oder Feld auswählen</HelpLabel></Label>
                                                <SearchableSelect
                                                    options={sourceFieldOptions(c.source_step_order, c.field)}
                                                    value={c.field || ''}
                                                    onChange={(value) => changeConditionField(i, value)}
                                                    placeholder="Feld auswählen"
                                                    searchPlaceholder="Feld nach Name oder Typ suchen …"
                                                    testId={`condition-source-field-${i}`}
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Operator für den Vergleich: gleich/ungleich, eine Auswahlmenge, leer/gefüllt oder vorhandener/fehlender Upload.">3. Vergleich</HelpLabel></Label>
                                                <Select value={c.operator} onValueChange={(value) => changeConditionOperator(i, value)}>
                                                    <SelectTrigger className="min-h-10" data-testid={`condition-operator-${i}`}><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        {conditionOperatorOptions(c).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Erwarteter Wert. Bei Status ist dies z. B. completed; bei Auswahlfeldern der technische Optionswert.">4. Vergleichswert</HelpLabel></Label>
                                                {['empty', 'not_empty'].includes(c.operator) ? (
                                                    <div className="flex min-h-10 items-center rounded-md border border-dashed border-border bg-muted/40 px-3 text-sm text-muted-foreground">Kein Wert erforderlich</div>
                                                ) : ['one_of', 'not_one_of'].includes(c.operator) ? (
                                                    <SearchableMultiSelect
                                                        options={valueOptions}
                                                        values={Array.isArray(c.value) ? c.value : (c.value ? [c.value] : [])}
                                                        onChange={(values) => updateCondition(i, { value: values })}
                                                        placeholder="Mehrere Werte auswählen"
                                                        searchPlaceholder="Werte durchsuchen oder eingeben …"
                                                        testId={`condition-values-${i}`}
                                                        allowCustom
                                                    />
                                                ) : valueOptions.length > 0 ? (
                                                    <SearchableSelect
                                                        options={valueOptions}
                                                        value={Array.isArray(c.value) ? (c.value[0] || '') : (c.value || '')}
                                                        onChange={(value) => updateCondition(i, { value })}
                                                        placeholder="Wert auswählen"
                                                        searchPlaceholder="Wert durchsuchen …"
                                                        testId={`condition-value-${i}`}
                                                        allowCustom
                                                    />
                                                ) : (
                                                    <Input value={c.value || ''} onChange={(event) => updateCondition(i, { value: event.target.value })} placeholder="Vergleichswert eingeben" data-testid={`condition-value-input-${i}`} />
                                                )}
                                            </div>
                                        </div>

                                        <div className="mt-4 grid gap-3 border-t border-border pt-4 lg:grid-cols-2">
                                            <div>
                                                <Label className="text-xs"><HelpLabel help="Verbergen entfernt den Step aus Journey und Fortschritt; Blockieren zeigt ihn gesperrt; Auto-Abschluss erledigt ihn; Weiterleitung öffnet das Ziel.">5. Aktion bei Treffer</HelpLabel></Label>
                                                <Select value={c.action} onValueChange={(value) => updateCondition(i, { action: value, target_step_order: value === 'redirect' ? c.target_step_order : null })}>
                                                    <SelectTrigger className="min-h-10" data-testid={`condition-action-${i}`}><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        {CONDITION_ACTION_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            {c.action === 'redirect' && (
                                                <div>
                                                    <Label className="text-xs"><HelpLabel help="Step, zu dem bei einer zutreffenden Redirect-Regel gewechselt wird.">Ziel-Schritt</HelpLabel></Label>
                                                    <SearchableSelect
                                                        options={withFallbackOption(stepOptions, c.target_step_order, 'Nicht gefundener Schritt')}
                                                        value={c.target_step_order == null ? '' : String(c.target_step_order)}
                                                        onChange={(value) => updateCondition(i, { target_step_order: value ? Number(value) : null })}
                                                        placeholder="Ziel-Schritt auswählen"
                                                        searchPlaceholder="Ziel-Schritt suchen …"
                                                        testId={`condition-target-step-${i}`}
                                                    />
                                                </div>
                                            )}
                                            <div className={c.action === 'redirect' ? 'lg:col-span-2' : ''}>
                                                <Label className="text-xs"><HelpLabel help="Erklärt den Grund der Regel in verständlicher Sprache, besonders bei blockierten Steps.">Hinweis für Nutzer (optional)</HelpLabel></Label>
                                                <Textarea value={c.message || ''} onChange={(event) => updateCondition(i, { message: event.target.value })} className="mt-1 min-h-[68px]" placeholder="Erklärt verständlich, warum der Schritt blockiert, verborgen oder weitergeleitet wird." data-testid={`condition-message-${i}`} />
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                            {formData.conditions.length === 0 && <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">Keine Regeln konfiguriert. Dieser Schritt ist ohne zusätzliche Einschränkung erreichbar.</p>}
                        </div>
                    )}

                    {/* NOTIFICATIONS + EMAIL TEMPLATES */}
                    {activeSection === 'notifications' && (
                        <div className="space-y-4">
                            <div className="space-y-3">
                                {[['email_on_enter', 'Bei Schritt-Eintritt'], ['email_on_edit', 'Bei Bearbeitung'], ['email_on_leave', 'Bei Schritt-Abschluss']].map(([key, label]) => (
                                    <div key={key} className="flex items-center justify-between"><HelpLabel className="text-sm" help={{ email_on_enter: 'Sendet beim ersten Öffnen beziehungsweise Starten dieses Steps.', email_on_edit: 'Sendet bei späteren Änderungen gespeicherter Step-Daten, sofern Nutzer dies erlaubt haben.', email_on_leave: 'Sendet unmittelbar beim erfolgreichen Abschluss dieses Steps.' }[key]}>{label}</HelpLabel><Switch checked={formData[key]} onCheckedChange={(val) => setFormData({ ...formData, [key]: val })} /></div>
                                ))}
                            </div>
                            
                            <div className="p-3 bg-muted rounded-sm">
                                <p className="text-xs text-muted-foreground mb-1">Verfügbare Variablen für E-Mail-Vorlagen:</p>
                                <div className="flex flex-wrap gap-1">
                                    {['{{user_name}}', '{{user_email}}', '{{step_title}}', '{{step_order}}', '{{step_description}}'].map(v => (
                                        <code key={v} className="px-1.5 py-0.5 text-[10px] bg-card border border-border rounded">{v}</code>
                                    ))}
                                </div>
                            </div>

                            {formData.email_on_enter && (
                                <div className="p-3 border border-border rounded-sm space-y-2">
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">E-Mail bei Eintritt</p>
                                    <div><Label className="text-xs">Betreff</Label><Input value={formData.email_subject_enter || ''} onChange={(e) => setFormData({ ...formData, email_subject_enter: e.target.value })} className="h-8 text-sm mt-1" placeholder="Schritt gestartet: {{step_title}}" data-testid="email-subject-enter" /></div>
                                    <div><Label className="text-xs">Inhalt (HTML)</Label><Textarea value={formData.email_body_enter || ''} onChange={(e) => setFormData({ ...formData, email_body_enter: e.target.value })} className="text-sm mt-1 min-h-[60px]" placeholder="<p>Hallo {{user_name}}, Sie haben {{step_title}} begonnen.</p>" data-testid="email-body-enter" /></div>
                                </div>
                            )}

                            {formData.email_on_edit && (
                                <div className="p-3 border border-border rounded-sm space-y-2">
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">E-Mail bei Bearbeitung</p>
                                    <div><Label className="text-xs">Betreff</Label><Input value={formData.email_subject_edit || ''} onChange={(e) => setFormData({ ...formData, email_subject_edit: e.target.value })} className="h-8 text-sm mt-1" placeholder="Schritt aktualisiert: {{step_title}}" data-testid="email-subject-edit" /></div>
                                    <div><Label className="text-xs">Inhalt (HTML)</Label><Textarea value={formData.email_body_edit || ''} onChange={(e) => setFormData({ ...formData, email_body_edit: e.target.value })} className="text-sm mt-1 min-h-[60px]" placeholder="<p>Hallo {{user_name}}, {{step_title}} wurde aktualisiert.</p>" data-testid="email-body-edit" /></div>
                                </div>
                            )}

                            {formData.email_on_leave && (
                                <div className="p-3 border border-border rounded-sm space-y-2">
                                    <p className="text-xs font-semibold text-muted-foreground uppercase">E-Mail bei Abschluss</p>
                                    <div><Label className="text-xs">Betreff</Label><Input value={formData.email_subject_leave || ''} onChange={(e) => setFormData({ ...formData, email_subject_leave: e.target.value })} className="h-8 text-sm mt-1" placeholder="Schritt abgeschlossen: {{step_title}}" data-testid="email-subject-leave" /></div>
                                    <div><Label className="text-xs">Inhalt (HTML)</Label><Textarea value={formData.email_body_leave || ''} onChange={(e) => setFormData({ ...formData, email_body_leave: e.target.value })} className="text-sm mt-1 min-h-[60px]" placeholder="<p>Hallo {{user_name}}, herzlichen Glückwunsch! {{step_title}} ist abgeschlossen.</p>" data-testid="email-body-leave" /></div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeSection === 'translations' && (
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-sm border border-blue-200 dark:border-blue-800">
                                <span className="text-xs font-bold text-blue-700 dark:text-blue-300 bg-blue-200 dark:bg-blue-800 px-1.5 py-0.5 rounded">EN</span>
                                <span className="text-sm text-blue-700 dark:text-blue-300">English Translation</span>
                            </div>
                            <div className="space-y-3">
                                <div>
                                    <Label className="text-xs">Title (EN)</Label>
                                    <Input value={translations.en?.title || ''} onChange={(e) => setTrans('en', 'title', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.title} data-testid="trans-en-title" />
                                </div>
                                <div>
                                    <Label className="text-xs">Description (EN)</Label>
                                    <Textarea value={translations.en?.description || ''} onChange={(e) => setTrans('en', 'description', e.target.value)} className="text-sm mt-1 min-h-[60px]" placeholder={formData.description} data-testid="trans-en-description" />
                                </div>
                                {(formData.step_type === 'display' || formData.step_type === 'milestone') && (
                                    <>
                                        <div>
                                            <Label className="text-xs">Pending Message (EN)</Label>
                                            <Input value={translations.en?.pending_message || ''} onChange={(e) => setTrans('en', 'pending_message', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.pending_message} />
                                        </div>
                                        <div>
                                            <Label className="text-xs">Action Label (EN)</Label>
                                            <Input value={translations.en?.action_label || ''} onChange={(e) => setTrans('en', 'action_label', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.action_label} />
                                        </div>
                                    </>
                                )}
                                {formData.skippable && (
                                    <div>
                                        <Label className="text-xs">Skip Label (EN)</Label>
                                        <Input value={translations.en?.skip_label || ''} onChange={(e) => setTrans('en', 'skip_label', e.target.value)} className="h-8 text-sm mt-1" placeholder={formData.skip_label} />
                                    </div>
                                )}
                            </div>
                            <p className="text-xs text-muted-foreground">Deutsche Texte (DE) werden im Tab "Basis" gepflegt. Hier nur die englische Uebersetzung eingeben.</p>
                        </div>
                    )}


                        </section>
                    </div>

                    <div className="flex items-center justify-between gap-3 border-t border-border bg-card px-6 py-4">
                        <p className="hidden text-xs text-muted-foreground sm:block">Änderungen werden erst mit „Speichern“ übernommen.</p>
                        <div className="ml-auto flex gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>{t('cancel')}</Button>
                        <Button type="submit" className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="save-step-btn">{step ? t('save') : t('create_user_submit')}</Button>
                        </div>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

function PartnerDialog({ open, onClose, partner, onSave, allUsers, allPartners, surveys, defaultUserFeeCents = 0, t }) {
    const [formData, setFormData] = useState({
        name: '', description: '', logo_url: '', website: '',
        contact_email: '', category: '', tags: [], is_active: true, linked_user_ids: [], survey_ids: [], step_user_fee_cents: {}, stripe_customer_id: '', stripe_subscription_id: '', billing_status: ''
    });
    const [tagInput, setTagInput] = useState('');
    const [tagSuggestions, setTagSuggestions] = useState([]);
    const [showTagSuggestions, setShowTagSuggestions] = useState(false);
    const [userSearch, setUserSearch] = useState('');

    // Collect all existing tags from all partners for autocomplete
    const allTags = [...new Set((allPartners || []).flatMap(p => p.tags || []))].sort();

    useEffect(() => {
        if (partner) {
            setFormData({
                name: partner.name || '', description: partner.description || '',
                logo_url: partner.logo_url || '', website: partner.website || '',
                contact_email: partner.contact_email || '', category: partner.category || '',
                tags: partner.tags || [], is_active: partner.is_active !== false,
                linked_user_ids: partner.linked_user_ids || [], survey_ids: partner.survey_ids || [], step_user_fee_cents: partner.step_user_fee_cents || {}, stripe_customer_id: partner.stripe_customer_id || '', stripe_subscription_id: partner.stripe_subscription_id || '', billing_status: partner.billing_status || ''
            });
        } else {
            setFormData({ name: '', description: '', logo_url: '', website: '', contact_email: '', category: '', tags: [], is_active: true, linked_user_ids: [], survey_ids: [], step_user_fee_cents: {}, stripe_customer_id: '', stripe_subscription_id: '', billing_status: '' });
        }
        setTagInput('');
        setUserSearch('');
    }, [partner]);

    const handleTagInputChange = (val) => {
        setTagInput(val);
        if (val.trim()) {
            const filtered = allTags.filter(t => t.toLowerCase().includes(val.toLowerCase()) && !formData.tags.includes(t));
            setTagSuggestions(filtered);
            setShowTagSuggestions(true);
        } else {
            setShowTagSuggestions(false);
        }
    };

    const addTag = (tag) => {
        const trimmed = tag.trim();
        if (trimmed && !formData.tags.includes(trimmed)) {
            setFormData(fd => ({ ...fd, tags: [...fd.tags, trimmed] }));
        }
        setTagInput('');
        setShowTagSuggestions(false);
    };

    const removeTag = (tag) => {
        setFormData(fd => ({ ...fd, tags: fd.tags.filter(t => t !== tag) }));
    };

    const handleTagKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (tagInput.trim()) addTag(tagInput);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({ ...formData });
    };

    const toggleUser = (uid) => {
        setFormData(fd => ({
            ...fd,
            linked_user_ids: fd.linked_user_ids.includes(uid)
                ? fd.linked_user_ids.filter(id => id !== uid)
                : [...fd.linked_user_ids, uid]
        }));
    };

    const availableUsers = allUsers.filter(u => u.role !== 'admin');

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{partner ? t('partner_edit') : t('partner_create')}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <Label>Name</Label>
                        <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="mt-1" required data-testid="partner-name-input" />
                    </div>
                    <div>
                        <Label>Beschreibung</Label>
                        <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="mt-1" required data-testid="partner-description-input" />
                    </div>
                    <div>
                        <Label>Logo URL</Label>
                        <Input value={formData.logo_url} onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })} className="mt-1" placeholder="https://..." data-testid="partner-logo-input" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label>Website</Label>
                            <Input value={formData.website} onChange={(e) => setFormData({ ...formData, website: e.target.value })} className="mt-1" placeholder="https://..." data-testid="partner-website-input" />
                        </div>
                        <div>
                            <Label>Kontakt-Email</Label>
                            <Input type="email" value={formData.contact_email} onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })} className="mt-1" data-testid="partner-email-input" />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label>Kategorie</Label>
                            <Input value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} className="mt-1" placeholder="z.B. Antragstellung" data-testid="partner-category-input" />
                        </div>
                    </div>
                    <div>
                        <Label>Tags</Label>
                            <div className="mt-1 flex flex-wrap gap-1.5 p-2 min-h-[38px] border border-border rounded-sm bg-background">
                                {formData.tags.map(tag => (
                                    <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] text-xs rounded-sm" data-testid={`tag-badge-${tag}`}>
                                        {tag}
                                        <button type="button" onClick={() => removeTag(tag)} className="hover:text-red-500 font-bold ml-0.5" data-testid={`remove-tag-${tag}`}>&times;</button>
                                    </span>
                                ))}
                                <div className="relative flex-1 min-w-[120px]">
                                    <input
                                        type="text"
                                        value={tagInput}
                                        onChange={(e) => handleTagInputChange(e.target.value)}
                                        onKeyDown={handleTagKeyDown}
                                        onFocus={() => { if (tagInput.trim()) setShowTagSuggestions(true); }}
                                        onBlur={() => setTimeout(() => setShowTagSuggestions(false), 200)}
                                        placeholder={formData.tags.length === 0 ? "Tag eingeben..." : "+"}
                                        className="w-full bg-transparent border-none outline-none text-sm text-foreground placeholder:text-muted-foreground"
                                        data-testid="partner-tags-input"
                                    />
                                    {showTagSuggestions && tagSuggestions.length > 0 && (
                                        <div className="absolute left-0 top-full mt-1 w-56 bg-card border border-border rounded-sm shadow-lg z-50 max-h-40 overflow-y-auto" data-testid="tag-suggestions">
                                            {tagSuggestions.map(s => (
                                                <button key={s} type="button" onMouseDown={() => addTag(s)} className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-foreground">{s}</button>
                                            ))}
                                        </div>
                                    )}
                                    {showTagSuggestions && tagInput.trim() && !allTags.includes(tagInput.trim()) && !formData.tags.includes(tagInput.trim()) && (
                                        <div className="absolute left-0 top-full mt-1 w-56 bg-card border border-border rounded-sm shadow-lg z-50">
                                            {tagSuggestions.map(s => (
                                                <button key={s} type="button" onMouseDown={() => addTag(s)} className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-foreground">{s}</button>
                                            ))}
                                            <button type="button" onMouseDown={() => addTag(tagInput)} className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-[var(--brand-primary)] font-medium border-t border-border" data-testid="create-new-tag">
                                                + Neuen Tag "{tagInput.trim()}" erstellen
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                    </div>
                    <div>
                        <Label>{t('partner_linked_users')}</Label>
                        <p className="text-xs text-muted-foreground mb-2">{t('partner_linked_users_desc')}</p>
                        <Input placeholder={t('partner_search_users')} value={userSearch} onChange={e => setUserSearch(e.target.value)} className="mb-2 h-8 text-sm" data-testid="partner-user-search" />
                        <div className="max-h-40 overflow-y-auto border border-border rounded-sm">
                            {availableUsers.length === 0 ? (
                                <p className="p-3 text-xs text-muted-foreground">{t('partner_no_users')}</p>
                            ) : (() => {
                                const q = userSearch.toLowerCase();
                                const filtered = availableUsers.filter(u => !q || u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
                                const sorted = [...filtered].sort((a, b) => {
                                    const aChecked = formData.linked_user_ids.includes(a.id) ? 0 : 1;
                                    const bChecked = formData.linked_user_ids.includes(b.id) ? 0 : 1;
                                    return aChecked - bChecked
                                        || a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
                                        || a.email.localeCompare(b.email);
                                });
                                return sorted.length === 0 ? (
                                    <p className="p-3 text-xs text-muted-foreground">{t('partner_no_results')}</p>
                                ) : sorted.map(u => (
                                    <label key={u.id} className="flex items-center gap-2 px-3 py-2 hover:bg-muted cursor-pointer border-b border-border last:border-0" data-testid={`partner-link-user-${u.id}`}>
                                        <input type="checkbox" checked={formData.linked_user_ids.includes(u.id)} onChange={() => toggleUser(u.id)} className="rounded border-border" />
                                        <span className="text-sm font-medium">{u.name}</span>
                                        <span className="text-xs text-muted-foreground">{u.email}</span>
                                    </label>
                                ));
                            })()}
                        </div>
                    </div>
                    <div>
                        <Label>Survey-Zuordnung</Label>
                        <p className="text-xs text-muted-foreground mb-2">Mindestens eine Zuordnung aktiviert den Partner.</p>
                        <div className="border border-border rounded-sm divide-y divide-border">{(surveys || []).map(survey => <label key={survey.id} className="flex items-center gap-2 p-3 cursor-pointer"><Checkbox checked={formData.survey_ids.includes(survey.id)} onCheckedChange={() => setFormData(fd => ({...fd, survey_ids: fd.survey_ids.includes(survey.id) ? fd.survey_ids.filter(id => id !== survey.id) : [...fd.survey_ids, survey.id]}))}/><span>{survey.name}</span></label>)}</div>
                    </div>
                    {partner && <div data-testid="partner-step-prices">
                        <Label>Leistungen und Step-Preise</Label>
                        <p className="text-xs text-muted-foreground mb-2">Ein Partnerpreis überschreibt Step-Preis und globalen Standard. Leer übernimmt den jeweils nächstniedrigeren Wert.</p>
                        <div className="space-y-2">{(partner.service_steps || []).map(serviceStep => {
                            const inherited = serviceStep.step_user_fee_cents ?? defaultUserFeeCents;
                            const ownValue = formData.step_user_fee_cents[serviceStep.id];
                            return <div key={serviceStep.id} className="rounded border border-border p-3"><div className="flex justify-between gap-3"><div><p className="text-sm font-medium">Step {serviceStep.order}: {serviceStep.title}</p><p className="text-xs text-muted-foreground">Tag: {serviceStep.filter_tag || '–'} · geerbt: {(inherited/100).toLocaleString('de-DE',{style:'currency',currency:'EUR'})}</p></div><Input className="w-32" type="number" min="0" value={ownValue ?? ''} placeholder={String(inherited)} onChange={event => setFormData(current => { const prices={...current.step_user_fee_cents}; if(event.target.value==='') delete prices[serviceStep.id]; else prices[serviceStep.id]=Number(event.target.value); return {...current,step_user_fee_cents:prices}; })} data-testid={`partner-step-price-${serviceStep.id}`} /></div></div>;
                        })}{!(partner.service_steps || []).length && <p className="rounded border border-dashed border-border p-3 text-sm text-muted-foreground">Über Tags und Survey-Zuordnung ist diesem Partner noch kein Partner-Step zugeordnet.</p>}</div>
                    </div>}
                    <div className="border-t border-border pt-4" data-testid="partner-stripe-fields"><Label>Stripe-Verknüpfung</Label><p className="mb-3 text-xs text-muted-foreground">Manuelle Pflege für bestehende Stripe-Konten. IDs müssen zum selben Stripe-Kunden gehören.</p><div className="space-y-3"><div><Label>Customer-ID</Label><Input value={formData.stripe_customer_id} onChange={event => setFormData({...formData,stripe_customer_id:event.target.value.trim()})} placeholder="cus_…" /></div><div><Label>Subscription-ID</Label><Input value={formData.stripe_subscription_id} onChange={event => setFormData({...formData,stripe_subscription_id:event.target.value.trim()})} placeholder="sub_…" /></div><div><Label>Abrechnungsstatus</Label><Select value={formData.billing_status || 'pending'} onValueChange={value => setFormData({...formData,billing_status:value})}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="pending">pending</SelectItem><SelectItem value="trialing">trialing</SelectItem><SelectItem value="active">active</SelectItem><SelectItem value="paid">paid</SelectItem><SelectItem value="past_due">past_due</SelectItem><SelectItem value="unpaid">unpaid</SelectItem><SelectItem value="canceled">canceled</SelectItem></SelectContent></Select></div></div></div>
                    <div className="flex justify-end gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>{t('cancel')}</Button>
                        <Button type="submit" className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="save-partner-btn">
                            {partner ? t('save') : t('partner_create')}
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

function CreateUserDialog({ open, onClose, onSave, partners, surveys, permissionGroups = [], canManagePermissions = false, defaultSurveyId, t }) {
    const defaultGroupsForRole = useCallback((role) => permissionGroups.filter((group) => group.role === role && group.is_system).map((group) => group.id), [permissionGroups]);
    const [formData, setFormData] = useState(() => ({ email: '', password: '', name: '', role: 'user', partner_id: 'none', survey_id: defaultSurveyId || '', group_ids: [] }));

    useEffect(() => {
        if (open) setFormData({ email: '', password: '', name: '', role: 'user', partner_id: 'none', survey_id: defaultSurveyId || '', group_ids: defaultGroupsForRole('user') });
    }, [open, defaultSurveyId, defaultGroupsForRole]);

    const handleSubmit = (e) => {
        e.preventDefault();
        const data = { ...formData };
        if (data.partner_id === 'none') delete data.partner_id;
        if (data.role !== 'user') delete data.survey_id;
        if (!canManagePermissions) delete data.group_ids;
        onSave(data);
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{t('create_user_title')}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div><Label>{t('create_user_name')}</Label><Input value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="mt-1" required data-testid="create-user-name" /></div>
                    <div><Label>{t('create_user_email')}</Label><Input type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} className="mt-1" required data-testid="create-user-email" /></div>
                    <div><Label>{t('create_user_password')}</Label><Input type="password" value={formData.password} onChange={e => setFormData({ ...formData, password: e.target.value })} className="mt-1" required minLength={6} data-testid="create-user-password" /></div>
                    <div>
                        <Label>{t('create_user_role')}</Label>
                        <Select value={formData.role} onValueChange={val => setFormData({ ...formData, role: val, partner_id: val !== 'partner' ? 'none' : formData.partner_id, group_ids: defaultGroupsForRole(val) })}>
                            <SelectTrigger className="mt-1" data-testid="create-user-role"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="user">{t('user')}</SelectItem>
                                <SelectItem value="partner">{t('partner')}</SelectItem>
                                {canManagePermissions && <SelectItem value="admin">Admin</SelectItem>}
                            </SelectContent>
                        </Select>
                    </div>
                    {canManagePermissions && <div>
                        <Label>Nutzergruppen</Label>
                        <p className="mb-2 mt-1 text-xs text-muted-foreground">Passende Gruppen für die gewählte Portalrolle zuweisen.</p>
                        <SearchableMultiSelect
                            options={permissionGroups.filter((group) => group.role === formData.role).map((group) => ({ value: group.id, label: group.name, description: `${group.permissions?.includes('*') ? 'Alle' : group.permissions?.length || 0} Rechte` }))}
                            values={formData.group_ids}
                            onChange={(group_ids) => setFormData({ ...formData, group_ids })}
                            placeholder="Nutzergruppen auswählen"
                            searchPlaceholder="Nutzergruppe suchen …"
                            testId="create-user-permission-groups"
                        />
                    </div>}
                    {formData.role === 'user' && (
                        <div>
                            <Label>Survey</Label>
                            <Select value={formData.survey_id} onValueChange={val => setFormData({ ...formData, survey_id: val })} required>
                                <SelectTrigger className="mt-1" data-testid="create-user-survey">
                                    <SelectValue placeholder="Survey auswählen" />
                                </SelectTrigger>
                                <SelectContent>
                                    {surveys.filter(s => s.is_active).map(s => (
                                        <SelectItem key={s.id} value={s.id}>{s.name} /s/{s.slug}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    {formData.role === 'partner' && (
                        <div>
                            <Label>{t('create_user_partner')}</Label>
                            <Select value={formData.partner_id} onValueChange={val => setFormData({ ...formData, partner_id: val })}>
                                <SelectTrigger className="mt-1" data-testid="create-user-partner"><SelectValue placeholder={t('create_user_no_partner')} /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">{t('create_user_no_partner')}</SelectItem>
                                    {[...partners]
                                        .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
                                        .map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    <div className="flex justify-end gap-3 pt-2">
                        <Button type="button" variant="outline" onClick={onClose}>{t('cancel')}</Button>
                        <Button type="submit" disabled={formData.role === 'user' && !formData.survey_id} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="submit-create-user">{t('create_user_submit')}</Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

function AuditActionBadge({ action }) {
    const colors = {
        role_change: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
        step_create: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
        step_update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
        step_delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
        partner_create: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
        partner_update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
        partner_delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
        cms_update: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
        bulk_role_change: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    };
    const label = action?.replace(/_/g, ' ') || 'unknown';
    return (
        <span className={`px-2 py-1 text-xs font-medium rounded-sm capitalize ${colors[action] || 'bg-gray-100 text-gray-700'}`}>
            {label}
        </span>
    );
}

// ---------------------------------------------------------------------------
// ElementToggle — compact row with a name, description and right-side Switch.
// Used in Settings → UI-Elemente. Intentionally styled to fit later into a
// larger "Rechte­system" screen (user-group matrix rows will reuse this).
// ---------------------------------------------------------------------------
function ElementToggle({ id, label, description, checked, onChange }) {
    return (
        <div className="flex items-start justify-between gap-4 border border-border rounded-md p-3 bg-background/50">
            <div className="flex-1 min-w-0">
                <label htmlFor={id} className="font-medium text-foreground cursor-pointer block">
                    {label}
                </label>
                {description && (
                    <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
                )}
            </div>
            <Switch
                id={id}
                checked={checked}
                onCheckedChange={onChange}
                data-testid={`element-toggle-${id}`}
                className="shrink-0"
            />
        </div>
    );
}
