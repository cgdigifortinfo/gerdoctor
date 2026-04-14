import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { adminAPI, formatApiError } from '../lib/api';
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
    LinkBreak, UserPlus, ArrowRight, Check, DownloadSimple, ClockCounterClockwise
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Checkbox } from '../components/ui/checkbox';
import { useLanguage } from '../contexts/LanguageContext';
import { ThemeLangToggle } from '../components/ThemeLangToggle';

export default function AdminDashboard() {
    const { user, logout } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('analytics');
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

    const loadData = useCallback(async () => {
        try {
            const [usersRes, stepsRes, partnersRes, analyticsRes, homeRes, aboutRes, partnersContentRes, auditRes] = await Promise.all([
                adminAPI.getUsers(),
                adminAPI.getSteps(),
                adminAPI.getPartners(),
                adminAPI.getAnalytics(),
                adminAPI.getCmsContent('home'),
                adminAPI.getCmsContent('about'),
                adminAPI.getCmsContent('partners'),
                adminAPI.getAuditLog(50)
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
                            <Link to="/" className="font-black text-xl tracking-tight text-foreground">
                                GuidedJourney
                            </Link>
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
                                                <td className="px-4 py-3 text-sm text-muted-foreground">
                                                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <Button variant="outline" size="sm" onClick={() => handleViewUser(u.id)} className="border-border" data-testid={`view-user-${u.id}`}>
                                                        <Eye size={16} className="mr-1" /> View
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))}
                                        {filteredUsers.length === 0 && (
                                            <tr>
                                                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No users found</td>
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
                                {steps.sort((a, b) => a.order - b.order).map((step) => (
                                    <div key={step.id} className="border border-border rounded-sm p-4">
                                        <div className="flex justify-between items-start">
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
                            <div className="grid grid-cols-2 gap-4">
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

                            {/* Profile Data */}
                            {selectedUser.profile && Object.keys(selectedUser.profile).length > 0 && (
                                <div>
                                    <h4 className="font-semibold mb-3">Profile</h4>
                                    <div className="grid grid-cols-2 gap-3">
                                        {Object.entries(selectedUser.profile).map(([key, value]) => (
                                            <div key={key} className="p-2 bg-background rounded-sm">
                                                <span className="text-xs text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</span>
                                                <p className="text-sm font-medium">{String(value)}</p>
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
        step_type: 'form', fields: [],
        email_on_enter: false, email_on_edit: false, email_on_leave: false, is_active: true
    });
    const [showFieldForm, setShowFieldForm] = useState(false);
    const [editingField, setEditingField] = useState(null);

    useEffect(() => {
        if (step) {
            setFormData({
                title: step.title || '', description: step.description || '',
                order: step.order || existingSteps.length + 1,
                step_type: step.step_type || 'form', fields: step.fields || [],
                email_on_enter: step.email_on_enter || false,
                email_on_edit: step.email_on_edit || false,
                email_on_leave: step.email_on_leave || false,
                is_active: step.is_active !== false
            });
        } else {
            setFormData({
                title: '', description: '', order: existingSteps.length + 1,
                step_type: 'form', fields: [],
                email_on_enter: false, email_on_edit: false, email_on_leave: false, is_active: true
            });
        }
    }, [step, existingSteps.length]);

    const handleSubmit = (e) => { e.preventDefault(); onSave(formData); };

    const handleAddField = (field) => {
        if (editingField !== null) {
            const newFields = [...formData.fields];
            newFields[editingField] = field;
            setFormData({ ...formData, fields: newFields });
            setEditingField(null);
        } else {
            setFormData({ ...formData, fields: [...formData.fields, field] });
        }
        setShowFieldForm(false);
    };

    const handleRemoveField = (index) => {
        setFormData({ ...formData, fields: formData.fields.filter((_, i) => i !== index) });
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{step ? 'Edit Step' : 'Create Step'}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                            <Label>Title</Label>
                            <Input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} className="mt-1" required data-testid="step-title-input" />
                        </div>
                        <div className="col-span-2">
                            <Label>Description</Label>
                            <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="mt-1" required data-testid="step-description-input" />
                        </div>
                        <div>
                            <Label>Order</Label>
                            <Input type="number" min="1" value={formData.order} onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })} className="mt-1" required data-testid="step-order-input" />
                        </div>
                        <div>
                            <Label>Type</Label>
                            <Select value={formData.step_type} onValueChange={(val) => setFormData({ ...formData, step_type: val })}>
                                <SelectTrigger className="mt-1" data-testid="step-type-select"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="form">Form</SelectItem>
                                    <SelectItem value="partner_selection">Partner Selection</SelectItem>
                                    <SelectItem value="info">Information</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <Label>Email Notifications</Label>
                        {[
                            ['email_on_enter', 'On entering step'],
                            ['email_on_edit', 'On editing step'],
                            ['email_on_leave', 'On leaving step']
                        ].map(([key, label]) => (
                            <div key={key} className="flex items-center justify-between">
                                <span className="text-sm">{label}</span>
                                <Switch checked={formData[key]} onCheckedChange={(val) => setFormData({ ...formData, [key]: val })} />
                            </div>
                        ))}
                    </div>

                    <div className="flex items-center justify-between">
                        <Label>Active</Label>
                        <Switch checked={formData.is_active} onCheckedChange={(val) => setFormData({ ...formData, is_active: val })} />
                    </div>

                    {formData.step_type === 'form' && (
                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <Label>Form Fields</Label>
                                <Button type="button" variant="outline" size="sm" onClick={() => { setEditingField(null); setShowFieldForm(true); }} data-testid="add-field-btn">
                                    <Plus size={16} className="mr-1" /> Add Field
                                </Button>
                            </div>
                            <div className="space-y-2">
                                {formData.fields.map((field, index) => (
                                    <div key={index} className="flex items-center justify-between p-3 bg-background rounded-sm">
                                        <div>
                                            <span className="font-medium">{field.label}</span>
                                            <span className="text-xs text-muted-foreground ml-2">({field.field_type})</span>
                                            {field.required && <span className="text-red-500 ml-1">*</span>}
                                        </div>
                                        <div className="flex gap-2">
                                            <Button type="button" variant="ghost" size="sm" onClick={() => { setEditingField(index); setShowFieldForm(true); }}>
                                                <Pencil size={16} />
                                            </Button>
                                            <Button type="button" variant="ghost" size="sm" onClick={() => handleRemoveField(index)} className="text-red-500">
                                                <X size={16} />
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="flex justify-end gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                        <Button type="submit" className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-step-btn">
                            {step ? 'Update Step' : 'Create Step'}
                        </Button>
                    </div>
                </form>

                {showFieldForm && (
                    <FieldForm
                        field={editingField !== null ? formData.fields[editingField] : null}
                        onSave={handleAddField}
                        onCancel={() => { setShowFieldForm(false); setEditingField(null); }}
                    />
                )}
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
        const options = data.field_type === 'select' ? optionsText.split('\n').filter(o => o.trim()) : undefined;
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
                                <SelectItem value="date">Date</SelectItem>
                                <SelectItem value="file">File Upload</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <Label>Placeholder</Label>
                        <Input value={data.placeholder} onChange={(e) => setData({ ...data, placeholder: e.target.value })} className="mt-1" data-testid="field-placeholder-input" />
                    </div>
                    {data.field_type === 'select' && (
                        <div>
                            <Label>Options (one per line)</Label>
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
        contact_email: '', category: '', is_active: true
    });

    useEffect(() => {
        if (partner) {
            setFormData({
                name: partner.name || '', description: partner.description || '',
                logo_url: partner.logo_url || '', website: partner.website || '',
                contact_email: partner.contact_email || '', category: partner.category || '',
                is_active: partner.is_active !== false
            });
        } else {
            setFormData({ name: '', description: '', logo_url: '', website: '', contact_email: '', category: '', is_active: true });
        }
    }, [partner]);

    const handleSubmit = (e) => { e.preventDefault(); onSave(formData); };

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
