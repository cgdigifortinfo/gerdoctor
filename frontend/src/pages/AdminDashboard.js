import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
    ArrowUp, ArrowDown, UserCircle, Image as ImageIcon, GearSix, UserSwitch
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Checkbox } from '../components/ui/checkbox';
import { useLanguage } from '../contexts/LanguageContext';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { Logo } from '../components/Logo';

export default function AdminDashboard() {
    const { user, logout, impersonate } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('analytics');

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
    const [partners, setPartners] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [auditLogs, setAuditLogs] = useState([]);
    const [auditActionTypes, setAuditActionTypes] = useState([]);
    const [auditFilter, setAuditFilter] = useState('');
    const [auditDateFrom, setAuditDateFrom] = useState('');
    const [auditDateTo, setAuditDateTo] = useState('');
    const [loading, setLoading] = useState(true);

    // User management state
    const [selectedUser, setSelectedUser] = useState(null);
    const [showUserDialog, setShowUserDialog] = useState(false);
    const [userSearch, setUserSearch] = useState('');
    const [userRoleFilter, setUserRoleFilter] = useState('all');

    // Step management state
    const [editingStep, setEditingStep] = useState(null);
    const [showStepDialog, setShowStepDialog] = useState(false);

    // Partner management state
    const [editingPartner, setEditingPartner] = useState(null);
    const [showPartnerDialog, setShowPartnerDialog] = useState(false);
    const [showLinkDialog, setShowLinkDialog] = useState(null);

    // CMS state
    const [cmsHome, setCmsHome] = useState({});
    const [cmsAbout, setCmsAbout] = useState({});
    const [cmsPartners, setCmsPartners] = useState({});
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
        try {
            const [usersRes, stepsRes, partnersRes, analyticsRes, homeRes, aboutRes, partnersContentRes, auditRes, settingsRes] = await Promise.all([
                adminAPI.getUsers(),
                adminAPI.getSteps(),
                adminAPI.getPartners(),
                adminAPI.getAnalytics(),
                adminAPI.getCmsContent('home'),
                adminAPI.getCmsContent('about'),
                adminAPI.getCmsContent('partners'),
                adminAPI.getAuditLog(50),
                settingsAPI.get().catch(() => ({ data: {} }))
            ]);
            setUsers(usersRes.data);
            setSteps(stepsRes.data);
            setPartners(partnersRes.data);
            setAnalytics(analyticsRes.data);
            setCmsHome(homeRes.data.content || {});
            setCmsAbout(aboutRes.data.content || {});
            setCmsPartners(partnersContentRes.data.content || {});
            setAuditLogs(auditRes.data.logs || []);
            setAuditActionTypes(auditRes.data.action_types || []);
            if (settingsRes.data) setSiteSettings(settingsRes.data);
        } catch (error) {
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

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

    // User handlers
    const handleViewUser = async (userId) => {
        try {
            const response = await adminAPI.getUser(userId);
            setSelectedUser(response.data);
            setShowUserDialog(true);
        } catch (error) {
            toast.error('Failed to load user details');
        }
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
            if (editingStep?.id) {
                await adminAPI.updateStep(editingStep.id, stepData);
                toast.success('Step updated');
            } else {
                await adminAPI.createStep(stepData);
                toast.success('Step created');
            }
            setShowStepDialog(false);
            setEditingStep(null);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleDeleteStep = async (stepId) => {
        if (!window.confirm('Are you sure you want to delete this step?')) return;
        try {
            await adminAPI.deleteStep(stepId);
            toast.success('Step deleted');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
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
            await adminAPI.reorderSteps(newOrder);
            toast.success('Steps reordered');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
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
        if (!window.confirm('Are you sure you want to delete this partner?')) return;
        try {
            await adminAPI.deletePartner(partnerId);
            toast.success('Partner deleted');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
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
    const handleSaveCms = async (section, content) => {
        setCmsSaving(true);
        try {
            await adminAPI.updateCmsContent(section, content);
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
            const res = await adminAPI.getAuditLog(100, 0, actionVal, auditDateFrom, auditDateTo);
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
            const res = await adminAPI.getAuditLog(100, 0);
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

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <Logo />
                            <span className="text-xs font-bold tracking-wider uppercase text-[#114f55] px-2 py-1 bg-teal-50 rounded">
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

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="mb-6 bg-card border border-border flex-wrap h-auto gap-1 p-1">
                        <TabsTrigger value="analytics" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                            <ChartBar size={18} className="mr-2" />
                            {t('admin_dashboard')}
                        </TabsTrigger>
                        <TabsTrigger value="users" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                            <Users size={18} className="mr-2" />
                            {t('admin_users')}
                        </TabsTrigger>
                        <TabsTrigger value="steps" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                            <ListChecks size={18} className="mr-2" />
                            {t('admin_steps')}
                        </TabsTrigger>
                        <TabsTrigger value="partners" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                            <Buildings size={18} className="mr-2" />
                            {t('admin_partners')}
                        </TabsTrigger>
                        <TabsTrigger value="cms" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                            <Notebook size={18} className="mr-2" />
                            {t('admin_cms')}
                        </TabsTrigger>
                        <TabsTrigger value="audit" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                            <ClockCounterClockwise size={18} className="mr-2" />
                            {t('admin_audit')}
                        </TabsTrigger>
                        <TabsTrigger value="settings" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white" data-testid="admin-settings-tab">
                            <GearSix size={18} className="mr-2" />
                            Settings
                        </TabsTrigger>
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
                                        {analytics.step_analytics?.map((step) => (
                                            <div key={step.step_id} className="space-y-2">
                                                <div className="flex justify-between items-center">
                                                    <div className="flex items-center gap-2">
                                                        <span className="w-6 h-6 rounded-full bg-[#114f55] text-white flex items-center justify-center text-xs font-bold">
                                                            {step.order}
                                                        </span>
                                                        <span className="font-medium text-sm text-foreground">{step.title}</span>
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                                        <span>{step.completed}/{step.total} completed</span>
                                                        <span className="font-bold text-[#114f55]">{step.completion_rate}%</span>
                                                    </div>
                                                </div>
                                                <Progress value={step.completion_rate} className="h-2" />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </TabsContent>

                    {/* ============ USERS TAB ============ */}
                    <TabsContent value="users">
                        <div className="bg-card border border-border rounded-sm">
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
                                        <Button variant="outline" onClick={handleExportCsv} className="border-border text-muted-foreground" data-testid="export-csv-btn">
                                            <DownloadSimple size={16} className="mr-1" /> Export CSV
                                        </Button>
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground mt-2">{filteredUsers.length} of {users.length} users</p>
                            </div>

                            {/* Bulk Actions Bar */}
                            {selectedUserIds.length > 0 && (
                                <div className="p-3 bg-[#114f55]/5 border-b border-border flex flex-wrap items-center gap-3">
                                    <span className="text-sm font-medium text-[#114f55]">{selectedUserIds.length} selected</span>
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
                                    <Button size="sm" onClick={handleBulkRoleUpdate} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="bulk-apply-btn">
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
                                                    data-testid="select-all-users"
                                                />
                                            </th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Name</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Email</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Role</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Progress</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Forecast</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Joined</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredUsers.map((u) => (
                                            <tr key={u.id} className={`border-t border-border table-row-hover ${selectedUserIds.includes(u.id) ? 'bg-[#114f55]/5' : ''}`}>
                                                <td className="px-4 py-3">
                                                    <Checkbox
                                                        checked={selectedUserIds.includes(u.id)}
                                                        onCheckedChange={() => toggleUserSelection(u.id)}
                                                        data-testid={`select-user-${u.id}`}
                                                    />
                                                </td>
                                                <td className="px-4 py-3 text-sm text-foreground font-medium">{u.name}</td>
                                                <td className="px-4 py-3 text-sm text-muted-foreground">{u.email}</td>
                                                <td className="px-4 py-3">
                                                    <Select value={u.role} onValueChange={(val) => handleUpdateUserRole(u.id, val)}>
                                                        <SelectTrigger className="w-32 h-8 text-xs border-border">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="user">User</SelectItem>
                                                            <SelectItem value="admin">Admin</SelectItem>
                                                            <SelectItem value="partner">Partner</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                                                            <div className="h-full bg-[#114f55] rounded-full transition-all" style={{ width: `${u.completion_pct || 0}%` }} />
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
                                                        {u.role !== 'admin' && (
                                                            <Button variant="outline" size="sm" onClick={() => handleImpersonate(u.id)} className="border-border text-muted-foreground hover:text-[#114f55] hover:border-[#114f55]" data-testid={`impersonate-user-${u.id}`} title="Als User einloggen">
                                                                <UserSwitch size={16} />
                                                            </Button>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                        {filteredUsers.length === 0 && (
                                            <tr>
                                                <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">No users found</td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </TabsContent>

                    {/* ============ STEPS TAB ============ */}
                    <TabsContent value="steps">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border flex justify-between items-center">
                                <h2 className="text-lg font-semibold text-foreground">Step Management</h2>
                                <Button onClick={() => { setEditingStep(null); setShowStepDialog(true); }} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="add-step-btn">
                                    <Plus size={18} className="mr-2" /> Add Step
                                </Button>
                            </div>
                            <div className="p-4 space-y-4">
                                {steps.sort((a, b) => a.order - b.order).map((step, idx) => (
                                    <div key={step.id} className="border border-border rounded-sm p-4">
                                        <div className="flex justify-between items-start">
                                            {/* Reorder arrows */}
                                            <div className="flex flex-col gap-1 mr-3 flex-shrink-0">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleMoveStep(step.id, 'up')}
                                                    disabled={idx === 0}
                                                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground disabled:opacity-20"
                                                    data-testid={`step-move-up-${step.id}`}
                                                >
                                                    <ArrowUp size={14} />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleMoveStep(step.id, 'down')}
                                                    disabled={idx === steps.length - 1}
                                                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground disabled:opacity-20"
                                                    data-testid={`step-move-down-${step.id}`}
                                                >
                                                    <ArrowDown size={14} />
                                                </Button>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="w-8 h-8 rounded-full bg-[#114f55] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
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
                                                    <span>Dauer: <strong>{step.duration_value === 0 ? 'Sofort' : `${step.duration_value} ${({days:'Tage',weeks:'Wochen',months:'Monate',years:'Jahre'})[step.duration_unit] || step.duration_unit}`}</strong></span>
                                                    {step.email_on_enter && <span className="text-[#114f55]">Email on enter</span>}
                                                    {step.email_on_edit && <span className="text-[#114f55]">Email on edit</span>}
                                                    {step.email_on_leave && <span className="text-[#114f55]">Email on leave</span>}
                                                </div>
                                            </div>
                                            <div className="flex gap-2 flex-shrink-0 ml-4">
                                                <Button variant="outline" size="sm" onClick={() => { setEditingStep(step); setShowStepDialog(true); }} className="border-border text-[#114f55] hover:bg-teal-50" data-testid={`edit-step-${step.id}`}>
                                                    <Pencil size={16} className="mr-1" /> Edit
                                                </Button>
                                                <Button variant="outline" size="sm" onClick={() => handleDeleteStep(step.id)} className="border-red-200 text-red-500 hover:bg-red-50" data-testid={`delete-step-${step.id}`}>
                                                    <Trash size={16} className="mr-1" /> Delete
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </TabsContent>

                    {/* ============ PARTNERS TAB ============ */}
                    <TabsContent value="partners">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border flex justify-between items-center">
                                <h2 className="text-lg font-semibold text-foreground">Partner Management</h2>
                                <Button onClick={() => { setEditingPartner(null); setShowPartnerDialog(true); }} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="add-partner-btn">
                                    <Plus size={18} className="mr-2" /> Add Partner
                                </Button>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-background">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Partner</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Category</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Linked User</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Status</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {partners.map((partner) => {
                                            const linkedUser = users.find(u => u.id === partner.user_id);
                                            return (
                                                <tr key={partner.id} className="border-t border-border table-row-hover">
                                                    <td className="px-4 py-3">
                                                        <div className="flex items-center gap-3">
                                                            {partner.logo_url && <img src={partner.logo_url} alt="" className="w-10 h-10 rounded-sm object-cover" />}
                                                            <div>
                                                                <p className="font-medium text-foreground">{partner.name}</p>
                                                                <p className="text-xs text-muted-foreground">{partner.contact_email}</p>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-muted-foreground">{partner.category || '-'}</td>
                                                    <td className="px-4 py-3">
                                                        {linkedUser ? (
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-sm text-foreground">{linkedUser.name}</span>
                                                                <Button variant="ghost" size="sm" onClick={() => handleUnlinkUser(partner.id)} className="text-red-500 hover:text-red-700 h-6 px-1" title="Unlink user" data-testid={`unlink-partner-${partner.id}`}>
                                                                    <LinkBreak size={14} />
                                                                </Button>
                                                            </div>
                                                        ) : (
                                                            <Button variant="ghost" size="sm" onClick={() => setShowLinkDialog(partner)} className="text-[#114f55] h-7 text-xs" data-testid={`link-partner-${partner.id}`}>
                                                                <UserPlus size={14} className="mr-1" /> Link User
                                                            </Button>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={`px-2 py-1 text-xs rounded-sm ${partner.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                                                            {partner.is_active ? 'Active' : 'Inactive'}
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
                        </div>
                    </TabsContent>

                    {/* ============ CMS TAB ============ */}
                    <TabsContent value="cms">
                        <div className="space-y-6">
                            {/* Home Section */}
                            <CmsSection
                                title="Home / Hero Section"
                                fields={[
                                    { key: 'hero_title', label: 'Hero Title', type: 'text', placeholder: 'Transform Your Business Journey' },
                                    { key: 'hero_subtitle', label: 'Hero Subtitle', type: 'textarea', placeholder: 'A guided experience to connect you with the right partners' },
                                    { key: 'hero_cta', label: 'CTA Button Text', type: 'text', placeholder: 'Get Started' }
                                ]}
                                content={cmsHome}
                                onChange={setCmsHome}
                                onSave={() => handleSaveCms('home', cmsHome)}
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
                                onSave={() => handleSaveCms('about', cmsAbout)}
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
                                onSave={() => handleSaveCms('partners', cmsPartners)}
                                saving={cmsSaving}
                            />
                        </div>
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
                                    <Button size="sm" onClick={handleAuditFilter} className="bg-[#114f55] hover:bg-[#0d3d42] text-white h-9" data-testid="audit-apply-filter">
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
                                        {auditLogs.map((log, idx) => (
                                            <tr key={idx} className="border-t border-border">
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
                        </div>
                    </TabsContent>

                    {/* ============ SETTINGS TAB ============ */}
                    <TabsContent value="settings">
                        <div className="space-y-6">
                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-6">Site Settings</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Site Title</Label>
                                        <Input value={siteSettings.site_title || ''} onChange={e => setSiteSettings(s => ({ ...s, site_title: e.target.value }))} placeholder="GERdoctor" data-testid="settings-site-title" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Meta Description</Label>
                                        <Input value={siteSettings.meta_description || ''} onChange={e => setSiteSettings(s => ({ ...s, meta_description: e.target.value }))} placeholder="Praktizieren in Deutschland" data-testid="settings-meta-desc" />
                                    </div>
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-2">Logo Configuration</h2>
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
                                        <span className="font-black text-2xl tracking-tight text-foreground" style={{ fontFamily: "'Cabinet Grotesk', sans-serif", letterSpacing: '-0.02em' }}>{siteSettings.logo_bold_part || 'GER'}</span>
                                        <span className="font-light text-2xl tracking-tight text-foreground" style={{ fontFamily: "'Cabinet Grotesk', sans-serif", letterSpacing: '-0.02em' }}>{siteSettings.logo_light_part || 'doctor'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-card border border-border rounded-sm p-6">
                                <h2 className="text-lg font-semibold text-foreground mb-6">General</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label>Contact Email</Label>
                                        <Input value={siteSettings.contact_email || ''} onChange={e => setSiteSettings(s => ({ ...s, contact_email: e.target.value }))} placeholder="info@gerdoctor.de" data-testid="settings-contact-email" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Primary Color</Label>
                                        <div className="flex items-center gap-3">
                                            <input type="color" value={siteSettings.primary_color || '#114f55'} onChange={e => setSiteSettings(s => ({ ...s, primary_color: e.target.value }))} className="w-10 h-10 rounded cursor-pointer border border-border" data-testid="settings-primary-color" />
                                            <Input value={siteSettings.primary_color || ''} onChange={e => setSiteSettings(s => ({ ...s, primary_color: e.target.value }))} placeholder="#114f55" className="flex-1" />
                                        </div>
                                    </div>
                                    <div className="space-y-2 md:col-span-2">
                                        <Label>Footer Text</Label>
                                        <Input value={siteSettings.footer_text || ''} onChange={e => setSiteSettings(s => ({ ...s, footer_text: e.target.value }))} placeholder="Optional footer text" data-testid="settings-footer-text" />
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-end">
                                <Button onClick={handleSaveSettings} disabled={settingsSaving} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-settings-btn">
                                    {settingsSaving ? 'Saving...' : 'Save Settings'}
                                </Button>
                            </div>
                        </div>
                    </TabsContent>
                </Tabs>
            </div>

            {/* User Detail Dialog */}
            <Dialog open={showUserDialog} onOpenChange={setShowUserDialog}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
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

                            {/* Completion bar */}
                            <div className="p-4 bg-muted rounded-sm">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium">Fortschritt</span>
                                    <span className="text-sm font-bold text-[#114f55]">{selectedUser.completion_pct || 0}%</span>
                                </div>
                                <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                                    <div className="h-full bg-[#114f55] rounded-full transition-all" style={{ width: `${selectedUser.completion_pct || 0}%` }} />
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
                                                        <a href={filesAPI.getUrl(value)} target="_blank" rel="noopener noreferrer" className="text-sm text-[#114f55] hover:underline">
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

                            {/* Progress with edit ability */}
                            <div>
                                <h4 className="font-semibold mb-3">Progress</h4>
                                <div className="space-y-2">
                                    {selectedUser.progress?.map((p) => {
                                        const step = steps.find(s => s.id === p.step_id);
                                        return (
                                            <div key={p.step_id} className="flex items-center justify-between p-3 bg-background rounded-sm">
                                                <span className="text-sm">{step?.title || 'Unknown Step'}</span>
                                                <Select
                                                    value={p.status}
                                                    onValueChange={(val) => handleUpdateUserProgress(selectedUser.id, p.step_id, val)}
                                                >
                                                    <SelectTrigger className={`w-36 h-8 text-xs border-0 ${
                                                        p.status === 'completed' ? 'bg-green-100 text-green-700' :
                                                        p.status === 'in_progress' ? 'bg-yellow-100 text-yellow-700' :
                                                        'bg-gray-100 text-gray-700'
                                                    }`} data-testid={`user-progress-${p.step_id}`}>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="pending">Pending</SelectItem>
                                                        <SelectItem value="in_progress">In Progress</SelectItem>
                                                        <SelectItem value="completed">Completed</SelectItem>
                                                    </SelectContent>
                                                </Select>
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
                                                    <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${isDone ? 'bg-green-500 text-white' : isWip ? 'bg-[#114f55] text-white' : 'bg-muted text-muted-foreground'}`}>
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
            />

            {/* Partner Edit Dialog */}
            <PartnerDialog
                open={showPartnerDialog}
                onClose={() => { setShowPartnerDialog(false); setEditingPartner(null); }}
                partner={editingPartner}
                onSave={handleSavePartner}
            />

            {/* Link User to Partner Dialog */}
            <LinkUserDialog
                open={!!showLinkDialog}
                onClose={() => setShowLinkDialog(null)}
                partner={showLinkDialog}
                users={users.filter(u => u.role === 'user')}
                onLink={handleLinkUser}
            />
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

function CmsSection({ title, fields, content, onChange, onSave, saving }) {
    return (
        <div className="bg-card border border-border rounded-sm">
            <div className="p-4 border-b border-border flex justify-between items-center">
                <h3 className="font-semibold text-foreground">{title}</h3>
                <Button
                    onClick={onSave}
                    disabled={saving}
                    className="bg-[#114f55] hover:bg-[#0d3d42] text-white"
                    data-testid={`cms-save-${title.toLowerCase().replace(/\s+/g, '-')}`}
                >
                    {saving ? 'Saving...' : 'Save Changes'}
                </Button>
            </div>
            <div className="p-4 space-y-4">
                {fields.map((field) => (
                    <div key={field.key}>
                        <Label className="text-foreground">{field.label}</Label>
                        {field.type === 'textarea' ? (
                            <Textarea
                                value={content[field.key] || ''}
                                onChange={(e) => onChange({ ...content, [field.key]: e.target.value })}
                                placeholder={field.placeholder}
                                className="mt-1 border-border rounded-sm min-h-[80px]"
                                data-testid={`cms-field-${field.key}`}
                            />
                        ) : (
                            <Input
                                value={content[field.key] || ''}
                                onChange={(e) => onChange({ ...content, [field.key]: e.target.value })}
                                placeholder={field.placeholder}
                                className="mt-1 border-border rounded-sm"
                                data-testid={`cms-field-${field.key}`}
                            />
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

function LinkUserDialog({ open, onClose, partner, users, onLink }) {
    const [search, setSearch] = useState('');
    const filtered = users.filter(u =>
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md max-h-[70vh]">
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
                                    className="bg-[#114f55] hover:bg-[#0d3d42] text-white"
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

// Step Dialog Component
function StepDialog({ open, onClose, step, onSave, existingSteps }) {
    const [formData, setFormData] = useState({
        title: '', description: '', order: existingSteps.length + 1,
        step_type: 'form', fields: [], filter_tag: '', skippable: false, skip_label: '',
        action_label: '', pending_message: '', complete_message: '',
        required_fields: [], required_uploads: [],
        field_mappings: [], conditions: [],
        duration_value: 0, duration_unit: 'days',
        email_on_enter: false, email_on_edit: false, email_on_leave: false, is_active: true
    });
    const [showFieldForm, setShowFieldForm] = useState(false);
    const [editingField, setEditingField] = useState(null);
    const [activeSection, setActiveSection] = useState('basic');

    useEffect(() => {
        if (step) {
            setFormData({
                title: step.title || '', description: step.description || '',
                order: step.order || existingSteps.length + 1,
                step_type: step.step_type || 'form', fields: step.fields || [],
                filter_tag: step.filter_tag || '', skippable: step.skippable || false,
                skip_label: step.skip_label || '', action_label: step.action_label || '',
                pending_message: step.pending_message || '', complete_message: step.complete_message || '',
                required_fields: step.required_fields || [], required_uploads: step.required_uploads || [],
                field_mappings: step.field_mappings || [], conditions: step.conditions || [],
                duration_value: step.duration_value ?? 0, duration_unit: step.duration_unit || 'days',
                email_on_enter: step.email_on_enter || false, email_on_edit: step.email_on_edit || false,
                email_on_leave: step.email_on_leave || false, is_active: step.is_active !== false
            });
        } else {
            setFormData({
                title: '', description: '', order: existingSteps.length + 1,
                step_type: 'form', fields: [], filter_tag: '', skippable: false, skip_label: '',
                action_label: '', pending_message: '', complete_message: '',
                required_fields: [], required_uploads: [],
                field_mappings: [], conditions: [],
                duration_value: 0, duration_unit: 'days',
                email_on_enter: false, email_on_edit: false, email_on_leave: false, is_active: true
            });
        }
    }, [step, existingSteps.length]);

    const handleSubmit = (e) => { e.preventDefault(); onSave(formData); };
    const handleAddField = (field) => {
        if (editingField !== null) { const nf = [...formData.fields]; nf[editingField] = field; setFormData({ ...formData, fields: nf }); setEditingField(null); }
        else { setFormData({ ...formData, fields: [...formData.fields, field] }); }
        setShowFieldForm(false);
    };
    const handleRemoveField = (index) => { setFormData({ ...formData, fields: formData.fields.filter((_, i) => i !== index) }); };

    // Mapping helpers
    const addMapping = () => { setFormData({ ...formData, field_mappings: [...formData.field_mappings, { source_step_order: 1, source_field: '', target_field: '' }] }); };
    const removeMapping = (i) => { setFormData({ ...formData, field_mappings: formData.field_mappings.filter((_, idx) => idx !== i) }); };
    const updateMapping = (i, key, val) => { const m = [...formData.field_mappings]; m[i] = { ...m[i], [key]: key === 'source_step_order' ? parseInt(val) : val }; setFormData({ ...formData, field_mappings: m }); };

    // Condition helpers
    const addCondition = () => { setFormData({ ...formData, conditions: [...formData.conditions, { source_step_order: 1, field: 'status', operator: 'status_is', value: 'completed', action: 'allow_next', target_step_order: null, message: '' }] }); };
    const removeCondition = (i) => { setFormData({ ...formData, conditions: formData.conditions.filter((_, idx) => idx !== i) }); };
    const updateCondition = (i, key, val) => { const c = [...formData.conditions]; c[i] = { ...c[i], [key]: ['source_step_order', 'target_step_order'].includes(key) ? (val ? parseInt(val) : null) : val }; setFormData({ ...formData, conditions: c }); };

    // Required fields/uploads
    const toggleRequiredField = (name) => {
        const rf = formData.required_fields.includes(name) ? formData.required_fields.filter(f => f !== name) : [...formData.required_fields, name];
        setFormData({ ...formData, required_fields: rf });
    };
    const [newReqUpload, setNewReqUpload] = useState('');
    const addRequiredUpload = () => { if (newReqUpload && !formData.required_uploads.includes(newReqUpload)) { setFormData({ ...formData, required_uploads: [...formData.required_uploads, newReqUpload] }); setNewReqUpload(''); } };
    const removeRequiredUpload = (u) => { setFormData({ ...formData, required_uploads: formData.required_uploads.filter(x => x !== u) }); };

    const sectionBtnClass = (s) => `px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${activeSection === s ? 'bg-[#114f55] text-white' : 'bg-muted text-muted-foreground hover:bg-muted/80'}`;

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
                <DialogHeader><DialogTitle>{step ? 'Schritt bearbeiten' : 'Schritt erstellen'}</DialogTitle></DialogHeader>
                
                {/* Section tabs */}
                <div className="flex flex-wrap gap-2 mb-4">
                    <button type="button" onClick={() => setActiveSection('basic')} className={sectionBtnClass('basic')}>Grunddaten</button>
                    <button type="button" onClick={() => setActiveSection('type')} className={sectionBtnClass('type')}>Typ-Einstellungen</button>
                    {formData.step_type === 'form' && <button type="button" onClick={() => setActiveSection('fields')} className={sectionBtnClass('fields')}>Felder ({formData.fields.length})</button>}
                    <button type="button" onClick={() => setActiveSection('requirements')} className={sectionBtnClass('requirements')}>Anforderungen</button>
                    <button type="button" onClick={() => setActiveSection('mappings')} className={sectionBtnClass('mappings')}>Mappings ({formData.field_mappings.length})</button>
                    <button type="button" onClick={() => setActiveSection('conditions')} className={sectionBtnClass('conditions')}>Bedingungen ({formData.conditions.length})</button>
                    <button type="button" onClick={() => setActiveSection('notifications')} className={sectionBtnClass('notifications')}>Benachrichtigungen</button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* BASIC */}
                    {activeSection === 'basic' && (
                        <div className="space-y-4">
                            <div><Label>Titel</Label><Input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} className="mt-1" required data-testid="step-title-input" /></div>
                            <div><Label>Beschreibung</Label><Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="mt-1" required data-testid="step-description-input" /></div>
                            <div className="grid grid-cols-2 gap-4">
                                <div><Label>Reihenfolge</Label><Input type="number" min="1" value={formData.order} onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })} className="mt-1" required /></div>
                                <div><Label>Typ</Label><Select value={formData.step_type} onValueChange={(val) => setFormData({ ...formData, step_type: val })}><SelectTrigger className="mt-1" data-testid="step-type-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="form">Formular</SelectItem><SelectItem value="partner_selection">Partner-Auswahl</SelectItem><SelectItem value="milestone">Meilenstein</SelectItem><SelectItem value="display">Anzeige</SelectItem><SelectItem value="info">Information</SelectItem></SelectContent></Select></div>
                            </div>
                            <div className="flex items-center justify-between"><Label>Aktiv</Label><Switch checked={formData.is_active} onCheckedChange={(val) => setFormData({ ...formData, is_active: val })} /></div>
                            <div className="flex items-center justify-between"><Label>Überspringbar</Label><Switch checked={formData.skippable} onCheckedChange={(val) => setFormData({ ...formData, skippable: val })} /></div>
                            {formData.skippable && <div><Label>Überspringen-Text</Label><Input value={formData.skip_label} onChange={(e) => setFormData({ ...formData, skip_label: e.target.value })} className="mt-1" placeholder="Vorerst überspringen" /></div>}
                            <div className="border-t border-border pt-4 mt-2">
                                <Label className="text-sm font-semibold">Dauer dieses Schritts</Label>
                                <p className="text-xs text-muted-foreground mb-2">Wie lange dauert dieser Schritt? 0 = sofort abschließbar.</p>
                                <div className="grid grid-cols-2 gap-4">
                                    <div><Label>Wert</Label><Input type="number" min="0" value={formData.duration_value} onChange={(e) => setFormData({ ...formData, duration_value: parseInt(e.target.value) || 0 })} className="mt-1" data-testid="step-duration-value" /></div>
                                    <div><Label>Einheit</Label><Select value={formData.duration_unit} onValueChange={(val) => setFormData({ ...formData, duration_unit: val })}><SelectTrigger className="mt-1" data-testid="step-duration-unit"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="days">Tage</SelectItem><SelectItem value="weeks">Wochen</SelectItem><SelectItem value="months">Monate</SelectItem><SelectItem value="years">Jahre</SelectItem></SelectContent></Select></div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TYPE SETTINGS */}
                    {activeSection === 'type' && (
                        <div className="space-y-4">
                            {(formData.step_type === 'partner_selection') && <div><Label>Filter-Tag</Label><Input value={formData.filter_tag} onChange={(e) => setFormData({ ...formData, filter_tag: e.target.value })} className="mt-1" placeholder="z.B. Antragstellung" /></div>}
                            {(formData.step_type === 'display' || formData.step_type === 'milestone') && (
                                <>
                                    <div><Label>Ausstehend-Nachricht</Label><Textarea value={formData.pending_message} onChange={(e) => setFormData({ ...formData, pending_message: e.target.value })} className="mt-1" placeholder="Warten auf Abschluss..." /></div>
                                    <div><Label>Abgeschlossen-Nachricht</Label><Textarea value={formData.complete_message} onChange={(e) => setFormData({ ...formData, complete_message: e.target.value })} className="mt-1" placeholder="Alles erledigt!" /></div>
                                </>
                            )}
                            {formData.step_type === 'display' && <div><Label>Button-Text</Label><Input value={formData.action_label} onChange={(e) => setFormData({ ...formData, action_label: e.target.value })} className="mt-1" placeholder="z.B. zur FaMed" /></div>}
                        </div>
                    )}

                    {/* FIELDS */}
                    {activeSection === 'fields' && formData.step_type === 'form' && (
                        <div>
                            <div className="flex justify-between items-center mb-3"><Label>Formularfelder</Label><Button type="button" variant="outline" size="sm" onClick={() => { setEditingField(null); setShowFieldForm(true); }} data-testid="add-field-btn"><Plus size={16} className="mr-1" /> Feld hinzufügen</Button></div>
                            <div className="space-y-2">
                                {formData.fields.map((field, index) => (
                                    <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-sm">
                                        <div><span className="font-medium">{field.label}</span><span className="text-xs text-muted-foreground ml-2">({field.field_type})</span>{field.required && <span className="text-red-500 ml-1">*</span>}</div>
                                        <div className="flex gap-2"><Button type="button" variant="ghost" size="sm" onClick={() => { setEditingField(index); setShowFieldForm(true); }}><Pencil size={16} /></Button><Button type="button" variant="ghost" size="sm" onClick={() => handleRemoveField(index)} className="text-red-500"><X size={16} /></Button></div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* REQUIREMENTS */}
                    {activeSection === 'requirements' && (
                        <div className="space-y-4">
                            <div>
                                <Label className="mb-2 block">Pflichtfelder (zum Abschluss des Schritts)</Label>
                                {formData.fields.length > 0 ? (
                                    <div className="space-y-1">{formData.fields.map(f => (
                                        <label key={f.name} className="flex items-center gap-2 p-2 bg-muted rounded-sm cursor-pointer hover:bg-muted/80">
                                            <input type="checkbox" checked={formData.required_fields.includes(f.name)} onChange={() => toggleRequiredField(f.name)} className="rounded" />
                                            <span className="text-sm">{f.label} ({f.name})</span>
                                        </label>
                                    ))}</div>
                                ) : <p className="text-sm text-muted-foreground">Keine Felder definiert</p>}
                            </div>
                            <div>
                                <Label className="mb-2 block">Erforderliche Dokument-Uploads</Label>
                                <div className="space-y-2">
                                    {formData.required_uploads.map(u => (
                                        <div key={u} className="flex items-center justify-between p-2 bg-muted rounded-sm">
                                            <span className="text-sm">{u}</span>
                                            <Button type="button" variant="ghost" size="sm" onClick={() => removeRequiredUpload(u)} className="text-red-500 h-6 w-6 p-0"><X size={14} /></Button>
                                        </div>
                                    ))}
                                    <div className="flex gap-2">
                                        <Input value={newReqUpload} onChange={(e) => setNewReqUpload(e.target.value)} placeholder="z.B. Visum" className="flex-1" />
                                        <Button type="button" variant="outline" size="sm" onClick={addRequiredUpload}><Plus size={14} /></Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* MAPPINGS */}
                    {activeSection === 'mappings' && (
                        <div className="space-y-4">
                            <div className="flex justify-between items-center"><Label>Feld-Mappings (Daten aus anderen Schritten vorausfüllen)</Label><Button type="button" variant="outline" size="sm" onClick={addMapping}><Plus size={14} className="mr-1" /> Mapping</Button></div>
                            {formData.field_mappings.map((m, i) => (
                                <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2 p-3 bg-muted rounded-sm items-end">
                                    <div><Label className="text-xs">Quell-Schritt Nr.</Label><Input type="number" min="1" value={m.source_step_order || ''} onChange={(e) => updateMapping(i, 'source_step_order', e.target.value)} className="h-8 text-sm" /></div>
                                    <div><Label className="text-xs">Quell-Feld</Label><Input value={m.source_field || ''} onChange={(e) => updateMapping(i, 'source_field', e.target.value)} className="h-8 text-sm" placeholder="z.B. name" /></div>
                                    <div><Label className="text-xs">Ziel-Feld</Label><Input value={m.target_field || ''} onChange={(e) => updateMapping(i, 'target_field', e.target.value)} className="h-8 text-sm" placeholder="z.B. applicant_name" /></div>
                                    <Button type="button" variant="ghost" size="sm" onClick={() => removeMapping(i)} className="text-red-500 h-8 w-8 p-0"><Trash size={14} /></Button>
                                </div>
                            ))}
                            {formData.field_mappings.length === 0 && <p className="text-sm text-muted-foreground p-4 bg-muted rounded-sm text-center">Keine Mappings konfiguriert</p>}
                        </div>
                    )}

                    {/* CONDITIONS */}
                    {activeSection === 'conditions' && (
                        <div className="space-y-4">
                            <div className="flex justify-between items-center"><Label>Bedingungen (Zugangssteuerung basierend auf vorherigen Schritten)</Label><Button type="button" variant="outline" size="sm" onClick={addCondition}><Plus size={14} className="mr-1" /> Bedingung</Button></div>
                            
                            {/* Presets */}
                            <div className="p-3 bg-[#114f55]/5 border border-[#114f55]/20 rounded-sm">
                                <p className="text-xs font-semibold text-[#114f55] mb-2">Vorlagen (klicken zum Hinzufügen)</p>
                                <div className="flex flex-wrap gap-2">
                                    {[
                                        { label: 'Vorheriger Schritt abgeschlossen', preset: { source_step_order: Math.max(1, formData.order - 1), field: 'status', operator: 'status_not', value: 'completed', action: 'block', message: 'Bitte schließen Sie zuerst den vorherigen Schritt ab.' } },
                                        { label: 'Dokument vorhanden', preset: { source_step_order: 1, field: 'documents', operator: 'has_upload', value: 'Visum', action: 'allow_next', message: 'Visum liegt vor.' } },
                                        { label: 'Dokument fehlt → blockieren', preset: { source_step_order: 1, field: 'documents', operator: 'missing_upload', value: 'Visum', action: 'block', message: 'Bitte laden Sie zuerst Ihr Visum hoch.' } },
                                        { label: 'Feld ausgefüllt', preset: { source_step_order: 1, field: 'field_of_study', operator: 'not_empty', value: '', action: 'allow_next', message: '' } },
                                        { label: 'Bestimmtes Fachgebiet', preset: { source_step_order: 1, field: 'field_of_study', operator: 'equals', value: 'Allgemeinmedizin', action: 'allow_next', message: 'Nur für Allgemeinmedizin.' } },
                                        { label: 'Weiterleitung zu Schritt', preset: { source_step_order: 1, field: 'status', operator: 'status_is', value: 'completed', action: 'redirect', target_step_order: formData.order + 1, message: 'Weiterleitung...' } },
                                    ].map((p, i) => (
                                        <button key={i} type="button" onClick={() => setFormData({ ...formData, conditions: [...formData.conditions, { ...p.preset, target_step_order: p.preset.target_step_order || null }] })}
                                            className="px-2 py-1 text-xs bg-card border border-border rounded-sm hover:bg-muted transition-colors" data-testid={`condition-preset-${i}`}>
                                            {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <p className="text-xs text-muted-foreground">Wenn eine Bedingung zutrifft, wird die konfigurierte Aktion ausgeführt.</p>
                            {formData.conditions.map((c, i) => (
                                <div key={i} className="p-3 bg-muted rounded-sm space-y-2 border border-border">
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                        <div><Label className="text-xs">Quell-Schritt Nr.</Label><Input type="number" min="1" value={c.source_step_order || ''} onChange={(e) => updateCondition(i, 'source_step_order', e.target.value)} className="h-8 text-sm" /></div>
                                        <div><Label className="text-xs">Feld</Label><Input value={c.field || ''} onChange={(e) => updateCondition(i, 'field', e.target.value)} className="h-8 text-sm" placeholder="status / feldname" /></div>
                                        <div><Label className="text-xs">Operator</Label>
                                            <Select value={c.operator} onValueChange={(val) => updateCondition(i, 'operator', val)}>
                                                <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="status_is">Status ist</SelectItem>
                                                    <SelectItem value="status_not">Status ist nicht</SelectItem>
                                                    <SelectItem value="equals">Gleich</SelectItem>
                                                    <SelectItem value="not_equals">Ungleich</SelectItem>
                                                    <SelectItem value="contains">Enthält</SelectItem>
                                                    <SelectItem value="not_empty">Nicht leer</SelectItem>
                                                    <SelectItem value="empty">Leer</SelectItem>
                                                    <SelectItem value="has_upload">Hat Upload</SelectItem>
                                                    <SelectItem value="missing_upload">Fehlt Upload</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div><Label className="text-xs">Wert</Label><Input value={c.value || ''} onChange={(e) => updateCondition(i, 'value', e.target.value)} className="h-8 text-sm" placeholder="completed / Visum" /></div>
                                    </div>
                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 items-end">
                                        <div><Label className="text-xs">Aktion</Label>
                                            <Select value={c.action} onValueChange={(val) => updateCondition(i, 'action', val)}>
                                                <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="block">Blockieren</SelectItem>
                                                    <SelectItem value="allow_next">Weiter erlauben</SelectItem>
                                                    <SelectItem value="redirect">Zu Schritt weiterleiten</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        {c.action === 'redirect' && <div><Label className="text-xs">Ziel-Schritt Nr.</Label><Input type="number" min="1" value={c.target_step_order || ''} onChange={(e) => updateCondition(i, 'target_step_order', e.target.value)} className="h-8 text-sm" /></div>}
                                        <div><Label className="text-xs">Nachricht</Label><Input value={c.message || ''} onChange={(e) => updateCondition(i, 'message', e.target.value)} className="h-8 text-sm" placeholder="Optionale Nachricht" /></div>
                                        <Button type="button" variant="ghost" size="sm" onClick={() => removeCondition(i)} className="text-red-500 h-8"><Trash size={14} /></Button>
                                    </div>
                                </div>
                            ))}
                            {formData.conditions.length === 0 && <p className="text-sm text-muted-foreground p-4 bg-muted rounded-sm text-center">Keine Bedingungen konfiguriert. Alle Benutzer können diesen Schritt erreichen.</p>}
                        </div>
                    )}

                    {/* NOTIFICATIONS + EMAIL TEMPLATES */}
                    {activeSection === 'notifications' && (
                        <div className="space-y-4">
                            <div className="space-y-3">
                                {[['email_on_enter', 'Bei Schritt-Eintritt'], ['email_on_edit', 'Bei Bearbeitung'], ['email_on_leave', 'Bei Schritt-Abschluss']].map(([key, label]) => (
                                    <div key={key} className="flex items-center justify-between"><span className="text-sm">{label}</span><Switch checked={formData[key]} onCheckedChange={(val) => setFormData({ ...formData, [key]: val })} /></div>
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

                    <div className="flex justify-end gap-3 pt-4 border-t border-border">
                        <Button type="button" variant="outline" onClick={onClose}>Abbrechen</Button>
                        <Button type="submit" className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-step-btn">{step ? 'Aktualisieren' : 'Erstellen'}</Button>
                    </div>
                </form>

                {showFieldForm && <FieldForm field={editingField !== null ? formData.fields[editingField] : null} onSave={handleAddField} onCancel={() => { setShowFieldForm(false); setEditingField(null); }} />}
            </DialogContent>
        </Dialog>
    );
}

function FieldForm({ field, onSave, onCancel }) {
    const [data, setData] = useState({
        name: field?.name || '', field_type: field?.field_type || 'text',
        label: field?.label || '', placeholder: field?.placeholder || '',
        required: field?.required || false, options: field?.options || []
    });
    const [optionsText, setOptionsText] = useState((field?.options || []).join('\n'));

    const handleSubmit = () => {
        const options = ['select', 'selectbox', 'multiupload'].includes(data.field_type) ? optionsText.split('\n').filter(o => o.trim()) : undefined;
        onSave({ ...data, options });
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card p-6 rounded-sm w-full max-w-md">
                <h3 className="font-semibold mb-4">{field ? 'Edit Field' : 'Add Field'}</h3>
                <div className="space-y-4">
                    <div>
                        <Label>Field Name (ID)</Label>
                        <Input value={data.name} onChange={(e) => setData({ ...data, name: e.target.value.toLowerCase().replace(/\s/g, '_') })} className="mt-1" placeholder="e.g., phone_number" data-testid="field-name-input" />
                    </div>
                    <div>
                        <Label>Label</Label>
                        <Input value={data.label} onChange={(e) => setData({ ...data, label: e.target.value })} className="mt-1" placeholder="e.g., Phone Number" data-testid="field-label-input" />
                    </div>
                    <div>
                        <Label>Type</Label>
                        <Select value={data.field_type} onValueChange={(val) => setData({ ...data, field_type: val })}>
                            <SelectTrigger className="mt-1" data-testid="field-type-select"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="text">Text</SelectItem>
                                <SelectItem value="email">Email</SelectItem>
                                <SelectItem value="phone">Phone</SelectItem>
                                <SelectItem value="textarea">Text Area</SelectItem>
                                <SelectItem value="select">Dropdown</SelectItem>
                                <SelectItem value="selectbox">Selectbox</SelectItem>
                                <SelectItem value="date">Date</SelectItem>
                                <SelectItem value="file">File Upload</SelectItem>
                                <SelectItem value="multiupload">Multi-Upload</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <Label>Placeholder</Label>
                        <Input value={data.placeholder} onChange={(e) => setData({ ...data, placeholder: e.target.value })} className="mt-1" data-testid="field-placeholder-input" />
                    </div>
                    {(data.field_type === 'select' || data.field_type === 'selectbox' || data.field_type === 'multiupload') && (
                        <div>
                            <Label>Options (one per line){data.field_type === 'multiupload' ? ' - Dokumenttypen' : ''}</Label>
                            <Textarea value={optionsText} onChange={(e) => setOptionsText(e.target.value)} className="mt-1" placeholder={"Option 1\nOption 2\nOption 3"} data-testid="field-options-input" />
                        </div>
                    )}
                    <div className="flex items-center justify-between">
                        <Label>Required</Label>
                        <Switch checked={data.required} onCheckedChange={(val) => setData({ ...data, required: val })} />
                    </div>
                </div>
                <div className="flex justify-end gap-3 mt-6">
                    <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
                    <Button onClick={handleSubmit} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-field-btn">
                        {field ? 'Update' : 'Add'} Field
                    </Button>
                </div>
            </div>
        </div>
    );
}

function PartnerDialog({ open, onClose, partner, onSave }) {
    const [formData, setFormData] = useState({
        name: '', description: '', logo_url: '', website: '',
        contact_email: '', category: '', tags: [], is_active: true
    });
    const [tagsText, setTagsText] = useState('');

    useEffect(() => {
        if (partner) {
            setFormData({
                name: partner.name || '', description: partner.description || '',
                logo_url: partner.logo_url || '', website: partner.website || '',
                contact_email: partner.contact_email || '', category: partner.category || '',
                tags: partner.tags || [], is_active: partner.is_active !== false
            });
            setTagsText((partner.tags || []).join(', '));
        } else {
            setFormData({ name: '', description: '', logo_url: '', website: '', contact_email: '', category: '', tags: [], is_active: true });
            setTagsText('');
        }
    }, [partner]);

    const handleSubmit = (e) => {
        e.preventDefault();
        const tags = tagsText.split(',').map(t => t.trim()).filter(Boolean);
        onSave({ ...formData, tags });
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>{partner ? 'Edit Partner' : 'Add Partner'}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <Label>Name</Label>
                        <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="mt-1" required data-testid="partner-name-input" />
                    </div>
                    <div>
                        <Label>Description</Label>
                        <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="mt-1" required data-testid="partner-description-input" />
                    </div>
                    <div>
                        <Label>Logo URL</Label>
                        <Input value={formData.logo_url} onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })} className="mt-1" placeholder="https://..." data-testid="partner-logo-input" />
                    </div>
                    <div>
                        <Label>Website</Label>
                        <Input value={formData.website} onChange={(e) => setFormData({ ...formData, website: e.target.value })} className="mt-1" placeholder="https://..." data-testid="partner-website-input" />
                    </div>
                    <div>
                        <Label>Contact Email</Label>
                        <Input type="email" value={formData.contact_email} onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })} className="mt-1" data-testid="partner-email-input" />
                    </div>
                    <div>
                        <Label>Category</Label>
                        <Input value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} className="mt-1" placeholder="e.g., Investment, Consulting" data-testid="partner-category-input" />
                    </div>
                    <div>
                        <Label>Tags (kommagetrennt)</Label>
                        <Input value={tagsText} onChange={(e) => setTagsText(e.target.value)} className="mt-1" placeholder="z.B. Antragstellung, Kenntnisprüfung" data-testid="partner-tags-input" />
                    </div>
                    <div className="flex items-center justify-between">
                        <Label>Active</Label>
                        <Switch checked={formData.is_active} onCheckedChange={(val) => setFormData({ ...formData, is_active: val })} />
                    </div>
                    <div className="flex justify-end gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                        <Button type="submit" className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-partner-btn">
                            {partner ? 'Update Partner' : 'Add Partner'}
                        </Button>
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
