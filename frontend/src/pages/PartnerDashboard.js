import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { partnerDashboardAPI, formatApiError, filesAPI } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Progress } from '../components/ui/progress';
import {
    SignOut, FileText, Gear, Eye, Check, ArrowRight, WarningCircle, CheckCircle,
    DownloadSimple, UserSwitch, CaretUp, CaretDown, UsersThree, UserList, Funnel
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { Logo } from '../components/Logo';

// ===== Shared sortable/filterable user table =====
function UserTable({ data, onViewUser, showStatus = false, tableId = 'table', t }) {
    const [sortKey, setSortKey] = useState(null);
    const [sortDir, setSortDir] = useState('asc');
    const [forecastFrom, setForecastFrom] = useState('');
    const [forecastTo, setForecastTo] = useState('');
    const [fieldFilter, setFieldFilter] = useState('all');

    // Collect unique Fachgebiet values
    const fachgebiete = useMemo(() => {
        const set = new Set();
        data.forEach(u => { if (u.field_of_study) set.add(u.field_of_study); });
        return Array.from(set).sort();
    }, [data]);

    const handleSort = (key) => {
        if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortKey(key); setSortDir('asc'); }
    };

    const SortHeader = ({ label, sortField, className = '' }) => (
        <th
            className={`px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors ${className}`}
            onClick={() => handleSort(sortField)}
            data-testid={`sort-${tableId}-${sortField}`}
        >
            <div className="flex items-center gap-1">
                {label}
                <span className="inline-flex flex-col leading-none">
                    <CaretUp size={10} weight={sortKey === sortField && sortDir === 'asc' ? 'bold' : 'regular'} className={sortKey === sortField && sortDir === 'asc' ? 'text-[#114f55]' : 'text-muted-foreground/40'} />
                    <CaretDown size={10} weight={sortKey === sortField && sortDir === 'desc' ? 'bold' : 'regular'} className={sortKey === sortField && sortDir === 'desc' ? 'text-[#114f55]' : 'text-muted-foreground/40'} />
                </span>
            </div>
        </th>
    );

    const filtered = useMemo(() => {
        let result = [...data];
        // Fachgebiet filter
        if (fieldFilter && fieldFilter !== 'all') {
            result = result.filter(u => u.field_of_study === fieldFilter);
        }
        // Forecast date filter
        if (forecastFrom) {
            const from = new Date(forecastFrom);
            result = result.filter(u => u.estimated_completion && new Date(u.estimated_completion) >= from);
        }
        if (forecastTo) {
            const to = new Date(forecastTo); to.setHours(23, 59, 59);
            result = result.filter(u => u.estimated_completion && new Date(u.estimated_completion) <= to);
        }
        // Sort
        if (sortKey) {
            result.sort((a, b) => {
                let va = a[sortKey] ?? '';
                let vb = b[sortKey] ?? '';
                if (sortKey === 'completion_pct') { va = Number(va); vb = Number(vb); }
                else if (sortKey === 'estimated_completion' || sortKey === 'created_at') {
                    va = va ? new Date(va).getTime() : 0;
                    vb = vb ? new Date(vb).getTime() : 0;
                } else { va = String(va).toLowerCase(); vb = String(vb).toLowerCase(); }
                if (va < vb) return sortDir === 'asc' ? -1 : 1;
                if (va > vb) return sortDir === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return result;
    }, [data, fieldFilter, forecastFrom, forecastTo, sortKey, sortDir]);

    return (
        <div>
            {/* Filters */}
            <div className="flex flex-wrap items-end gap-4 p-4 border-b border-border bg-muted/30">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground"><Funnel size={14} /> {t('partner_filter')}:</div>
                <div className="w-48">
                    <Label className="text-xs text-muted-foreground">{t('partner_filter_fachgebiet')}</Label>
                    <Select value={fieldFilter} onValueChange={setFieldFilter}>
                        <SelectTrigger className="h-8 text-xs mt-0.5" data-testid={`filter-${tableId}-fachgebiet`}>
                            <SelectValue placeholder={t('partner_filter_all')} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">{t('partner_filter_all')}</SelectItem>
                            {fachgebiete.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}
                        </SelectContent>
                    </Select>
                </div>
                <div>
                    <Label className="text-xs text-muted-foreground">{t('partner_filter_forecast_from')}</Label>
                    <Input type="date" value={forecastFrom} onChange={e => setForecastFrom(e.target.value)} className="h-8 text-xs mt-0.5 w-36" data-testid={`filter-${tableId}-forecast-from`} />
                </div>
                <div>
                    <Label className="text-xs text-muted-foreground">{t('partner_filter_forecast_to')}</Label>
                    <Input type="date" value={forecastTo} onChange={e => setForecastTo(e.target.value)} className="h-8 text-xs mt-0.5 w-36" data-testid={`filter-${tableId}-forecast-to`} />
                </div>
                {(fieldFilter !== 'all' || forecastFrom || forecastTo) && (
                    <Button variant="ghost" size="sm" onClick={() => { setFieldFilter('all'); setForecastFrom(''); setForecastTo(''); }} className="text-xs h-8 text-muted-foreground" data-testid={`filter-${tableId}-reset`}>
                        {t('partner_filter_reset')}
                    </Button>
                )}
                <span className="text-xs text-muted-foreground ml-auto">{filtered.length} {t('partner_entries')}</span>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full" data-testid={`${tableId}-table`}>
                    <thead className="bg-background">
                        <tr>
                            <SortHeader label={t('name')} sortField="user_name" />
                            <SortHeader label={t('email')} sortField="user_email" />
                            <SortHeader label={t('partner_filter_fachgebiet')} sortField="field_of_study" />
                            <SortHeader label={t('admin_progress')} sortField="completion_pct" />
                            {showStatus && <SortHeader label={t('status')} sortField="status" />}
                            <SortHeader label={t('admin_forecast')} sortField="estimated_completion" />
                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">{t('actions')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map((item) => (
                            <tr key={item.user_id || item.id} className="border-t border-border table-row-hover">
                                <td className="px-4 py-3 text-sm text-foreground font-medium">{item.user_name}</td>
                                <td className="px-4 py-3 text-sm text-muted-foreground">{item.user_email}</td>
                                <td className="px-4 py-3 text-sm text-muted-foreground">{item.field_of_study || '-'}</td>
                                <td className="px-4 py-3">
                                    <div className="flex items-center gap-2 min-w-[100px]">
                                        <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                                            <div className="h-full bg-[#114f55] rounded-full transition-all" style={{ width: `${item.completion_pct || 0}%` }} />
                                        </div>
                                        <span className="text-xs font-medium text-muted-foreground w-8 text-right">{item.completion_pct || 0}%</span>
                                    </div>
                                </td>
                                {showStatus && (
                                    <td className="px-4 py-3">
                                        <span className={`px-2 py-1 text-xs rounded-sm ${
                                            item.status === 'submitted' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                                            item.status === 'reviewed' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                                            'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                                        }`}>
                                            {item.status || '-'}
                                        </span>
                                    </td>
                                )}
                                <td className="px-4 py-3 text-sm text-muted-foreground">
                                    {item.estimated_completion ? new Date(item.estimated_completion).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '-'}
                                </td>
                                <td className="px-4 py-3">
                                    <Button variant="ghost" size="sm" onClick={() => onViewUser(item)} data-testid={`view-user-${item.user_id || item.id}`}>
                                        <Eye size={18} className="mr-1" /> Details
                                    </Button>
                                </td>
                            </tr>
                        ))}
                        {filtered.length === 0 && (
                            <tr><td colSpan={showStatus ? 7 : 6} className="px-4 py-8 text-center text-muted-foreground">{t('partner_no_entries')}</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ===== Main Partner Dashboard =====
export default function PartnerDashboard() {
    const { user, logout, impersonating, stopImpersonation } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const [submissions, setSubmissions] = useState([]);
    const [otherUsers, setOtherUsers] = useState([]);
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('my-users');
    const [selectedSubmission, setSelectedSubmission] = useState(null);
    const [userDetail, setUserDetail] = useState(null);
    const [userDetailLoading, setUserDetailLoading] = useState(false);
    const [editingProfile, setEditingProfile] = useState(false);
    const [profileForm, setProfileForm] = useState({});

    const loadData = useCallback(async () => {
        try {
            const [subsRes, otherRes, profileRes] = await Promise.all([
                partnerDashboardAPI.getSubmissions(),
                partnerDashboardAPI.getOtherUsers(),
                partnerDashboardAPI.getProfile()
            ]);
            setSubmissions(subsRes.data);
            setOtherUsers(otherRes.data);
            setProfile(profileRes.data);
            setProfileForm(profileRes.data);
        } catch (error) {
            console.error('Failed to load data:', error);
            if (error.response?.status === 400) toast.error('Your account is not linked to a partner');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const handleLogout = async () => { await logout(); navigate('/'); };

    const handleSaveProfile = async () => {
        try {
            await partnerDashboardAPI.updateProfile(profileForm);
            toast.success('Profile updated');
            setEditingProfile(false);
            loadData();
        } catch (error) { toast.error(formatApiError(error)); }
    };

    const handleViewUser = async (item) => {
        setSelectedSubmission(item);
        setUserDetail(null);
        setUserDetailLoading(true);
        try {
            const res = await partnerDashboardAPI.getUserDetail(item.user_id);
            setUserDetail(res.data);
        } catch (error) {
            // For "other users" the partner may not have access - show basic info
            if (error.response?.status === 403) {
                setUserDetail({ noAccess: true, name: item.user_name, email: item.user_email });
            } else {
                console.error('Failed to load user detail:', error);
            }
        } finally { setUserDetailLoading(false); }
    };

    const handleUpdateStepStatus = async (userId, stepId, newStatus) => {
        try {
            await partnerDashboardAPI.updateUserProgress(userId, stepId, newStatus, {});
            toast.success('Step status updated');
            const res = await partnerDashboardAPI.getUserDetail(userId);
            setUserDetail(res.data);
            loadData();
        } catch (error) { toast.error(formatApiError(error)); }
    };

    if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><div className="text-muted-foreground">Loading...</div></div>;

    return (
        <div className="min-h-screen bg-background">
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <Logo />
                            <span className="text-xs font-bold tracking-wider uppercase text-green-700 px-2 py-1 bg-green-50 rounded">Partner</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-sm text-muted-foreground hidden sm:block">{profile?.name || user?.name}</span>
                            <ThemeLangToggle />
                            {impersonating && (
                                <Button size="sm" onClick={() => { stopImpersonation(); navigate('/admin'); }} className="bg-red-600 hover:bg-red-700 text-white" data-testid="stop-impersonation-btn">
                                    <UserSwitch size={16} className="mr-1" /> Beenden
                                </Button>
                            )}
                            {!impersonating && (
                                <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground" data-testid="partner-logout-btn"><SignOut size={20} /></Button>
                            )}
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {!profile ? (
                    <div className="bg-card border border-border rounded-sm p-8 text-center">
                        <h2 className="text-xl font-semibold text-foreground mb-4">Account Not Linked</h2>
                        <p className="text-muted-foreground">Your account is not yet linked to a partner organization. Please contact an administrator.</p>
                    </div>
                ) : (
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="mb-6 bg-card border border-border">
                            <TabsTrigger value="my-users" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white" data-testid="tab-my-users">
                                <UserList size={18} className="mr-2" />
                                {t('partner_my_users')} ({submissions.length})
                            </TabsTrigger>
                            <TabsTrigger value="other-users" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white" data-testid="tab-other-users">
                                <UsersThree size={18} className="mr-2" />
                                {t('partner_other_users')} ({otherUsers.length})
                            </TabsTrigger>
                            <TabsTrigger value="profile" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white" data-testid="tab-profile">
                                <Gear size={18} className="mr-2" />
                                {t('partner_profile')}
                            </TabsTrigger>
                        </TabsList>

                        {/* Tab 1: My Users (submitted to this partner) */}
                        <TabsContent value="my-users">
                            <div className="bg-card border border-border rounded-sm overflow-hidden">
                                <div className="p-4 border-b border-border">
                                    <h2 className="text-lg font-semibold text-foreground">{t('partner_my_users')}</h2>
                                    <p className="text-sm text-muted-foreground">{t('partner_my_users_desc')}</p>
                                </div>
                                <UserTable data={submissions} onViewUser={handleViewUser} showStatus={true} tableId="my-users" t={t} />
                            </div>
                        </TabsContent>

                        {/* Tab 2: Other Users (not submitted to this partner) */}
                        <TabsContent value="other-users">
                            <div className="bg-card border border-border rounded-sm overflow-hidden">
                                <div className="p-4 border-b border-border">
                                    <h2 className="text-lg font-semibold text-foreground">{t('partner_other_users')}</h2>
                                    <p className="text-sm text-muted-foreground">{t('partner_other_users_desc')}</p>
                                </div>
                                <UserTable data={otherUsers} onViewUser={handleViewUser} showStatus={false} tableId="other-users" t={t} />
                            </div>
                        </TabsContent>

                        {/* Profile Tab */}
                        <TabsContent value="profile">
                            <div className="bg-card border border-border rounded-sm">
                                <div className="p-4 border-b border-border flex justify-between items-center">
                                    <h2 className="text-lg font-semibold text-foreground">{t('partner_profile')}</h2>
                                    {!editingProfile && <Button variant="outline" onClick={() => setEditingProfile(true)} data-testid="edit-profile-btn">{t('admin_edit')}</Button>}
                                </div>
                                <div className="p-6">
                                    {editingProfile ? (
                                        <div className="space-y-4 max-w-lg">
                                            <div><Label>Name</Label><Input value={profileForm.name || ''} onChange={e => setProfileForm({ ...profileForm, name: e.target.value })} className="mt-1" data-testid="profile-name-input" /></div>
                                            <div><Label>Beschreibung</Label><Textarea value={profileForm.description || ''} onChange={e => setProfileForm({ ...profileForm, description: e.target.value })} className="mt-1" data-testid="profile-description-input" /></div>
                                            <div><Label>Logo URL</Label><Input value={profileForm.logo_url || ''} onChange={e => setProfileForm({ ...profileForm, logo_url: e.target.value })} className="mt-1" data-testid="profile-logo-input" /></div>
                                            <div><Label>Website</Label><Input value={profileForm.website || ''} onChange={e => setProfileForm({ ...profileForm, website: e.target.value })} className="mt-1" data-testid="profile-website-input" /></div>
                                            <div><Label>Kontakt-Email</Label><Input type="email" value={profileForm.contact_email || ''} onChange={e => setProfileForm({ ...profileForm, contact_email: e.target.value })} className="mt-1" data-testid="profile-email-input" /></div>
                                            <div><Label>Kategorie</Label><Input value={profileForm.category || ''} onChange={e => setProfileForm({ ...profileForm, category: e.target.value })} className="mt-1" data-testid="profile-category-input" /></div>
                                            <div className="flex gap-3 pt-4">
                                                <Button variant="outline" onClick={() => { setEditingProfile(false); setProfileForm(profile); }}>{t('cancel')}</Button>
                                                <Button onClick={handleSaveProfile} className="bg-[#114f55] hover:bg-[#0d3d42] text-white" data-testid="save-profile-btn">{t('save')}</Button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="space-y-6">
                                            <div className="flex items-start gap-6">
                                                {profile.logo_url && <img src={profile.logo_url} alt={profile.name} className="w-24 h-24 object-cover rounded-sm" />}
                                                <div>
                                                    <h3 className="text-xl font-semibold text-foreground">{profile.name}</h3>
                                                    {profile.category && <span className="inline-block mt-1 px-2 py-1 text-xs bg-background text-muted-foreground rounded-sm">{profile.category}</span>}
                                                </div>
                                            </div>
                                            <div><Label className="text-muted-foreground">Beschreibung</Label><p className="mt-1">{profile.description}</p></div>
                                            <div className="grid md:grid-cols-2 gap-4">
                                                <div><Label className="text-muted-foreground">Website</Label><p className="mt-1">{profile.website ? <a href={profile.website} target="_blank" rel="noopener noreferrer" className="text-[#114f55] hover:underline">{profile.website}</a> : '-'}</p></div>
                                                <div><Label className="text-muted-foreground">Kontakt-Email</Label><p className="mt-1">{profile.contact_email || '-'}</p></div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </TabsContent>
                    </Tabs>
                )}
            </div>

            {/* User Detail Dialog */}
            <Dialog open={!!selectedSubmission} onOpenChange={() => { setSelectedSubmission(null); setUserDetail(null); }}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>{t('admin_user_detail')}</DialogTitle>
                    </DialogHeader>
                    {selectedSubmission && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div><Label className="text-muted-foreground">Name</Label><p className="font-medium" data-testid="detail-user-name">{selectedSubmission.user_name}</p></div>
                                <div><Label className="text-muted-foreground">Email</Label><p className="font-medium" data-testid="detail-user-email">{selectedSubmission.user_email}</p></div>
                            </div>

                            {userDetailLoading ? (
                                <div className="text-center py-4 text-muted-foreground">{t('loading')}</div>
                            ) : userDetail?.noAccess ? (
                                <div className="p-6 bg-muted rounded-sm text-center">
                                    <p className="text-muted-foreground">Dieser Nutzer hat noch keinen Antrag bei Ihnen eingereicht. Detaillierte Schrittdaten sind daher nicht verfügbar.</p>
                                </div>
                            ) : userDetail ? (
                                <div>
                                    <div className="flex items-center justify-between mb-3">
                                        <Label className="text-muted-foreground">Fortschritt</Label>
                                        <span className="text-sm font-medium text-[#114f55]" data-testid="detail-completion-pct">{userDetail.completion_pct}%</span>
                                    </div>
                                    <Progress value={userDetail.completion_pct} className="h-2 mb-4" />
                                    <div className="space-y-3">
                                        {userDetail.steps?.map((step) => {
                                            const prog = userDetail.progress?.find(p => p.step_id === step.id);
                                            const status = prog?.status || 'pending';
                                            const stepData = prog?.data || {};
                                            return (
                                                <div key={step.id} className="border border-border rounded-sm overflow-hidden" data-testid={`detail-step-${step.order}`}>
                                                    <div className="flex items-center justify-between px-4 py-3 bg-muted/50">
                                                        <div className="flex items-center gap-3">
                                                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${status === 'completed' ? 'bg-green-500 text-white' : status === 'in_progress' ? 'bg-[#114f55] text-white' : 'bg-muted text-muted-foreground'}`}>
                                                                {status === 'completed' ? <Check size={12} weight="bold" /> : step.order}
                                                            </div>
                                                            <div>
                                                                <p className="text-sm font-semibold text-foreground">{step.title}</p>
                                                                <p className="text-xs text-muted-foreground">{step.step_type}</p>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <span className={`px-2 py-0.5 text-xs font-medium rounded-sm ${status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : status === 'in_progress' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'bg-muted text-muted-foreground'}`}>
                                                                {status === 'completed' ? t('completed') : status === 'in_progress' ? t('in_progress') : t('pending')}
                                                            </span>
                                                            {status !== 'completed' && (
                                                                <Button size="sm" onClick={() => handleUpdateStepStatus(userDetail.id, step.id, 'completed')} className="bg-green-600 hover:bg-green-700 text-white text-xs h-7 px-2" data-testid={`complete-step-${step.order}`}>
                                                                    <CheckCircle size={14} className="mr-1" /> {t('partner_complete_step')}
                                                                </Button>
                                                            )}
                                                        </div>
                                                    </div>
                                                    {stepData && Object.keys(stepData).length > 0 && (
                                                        <div className="px-4 py-3 border-t border-border bg-background/50">
                                                            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                                                                {Object.entries(stepData).map(([key, value]) => {
                                                                    if (key === 'skipped') return null;
                                                                    const fieldDef = step.fields?.find(f => f.name === key);
                                                                    const label = fieldDef?.label || key.replace(/_/g, ' ');
                                                                    const fieldType = fieldDef?.field_type;
                                                                    if (fieldType === 'multiupload' && Array.isArray(value)) {
                                                                        return (
                                                                            <div key={key} className="col-span-2" data-testid={`step-data-${step.order}-${key}`}>
                                                                                <span className="text-xs text-muted-foreground capitalize">{label}</span>
                                                                                <div className="mt-1 space-y-1.5">
                                                                                    {value.map((entry, i) => (
                                                                                        <div key={i} className="flex items-center gap-2 text-sm">
                                                                                            {entry.document_type && <span className="px-2 py-0.5 text-xs font-medium bg-[#114f55]/10 text-[#114f55] rounded-sm">{entry.document_type}</span>}
                                                                                            {entry.file_id ? (
                                                                                                <a href={filesAPI.getUrl(entry.file_id)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[#114f55] hover:underline font-medium" data-testid={`download-${step.order}-${key}-${i}`}>
                                                                                                    <DownloadSimple size={14} />{entry.filename || 'Download'}
                                                                                                </a>
                                                                                            ) : <span className="text-muted-foreground">{entry.filename || '-'}</span>}
                                                                                        </div>
                                                                                    ))}
                                                                                </div>
                                                                            </div>
                                                                        );
                                                                    }
                                                                    if (fieldType === 'file' && value) {
                                                                        return (
                                                                            <div key={key} data-testid={`step-data-${step.order}-${key}`}>
                                                                                <span className="text-xs text-muted-foreground capitalize">{label}</span>
                                                                                <div className="mt-0.5"><a href={filesAPI.getUrl(value)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-[#114f55] hover:underline font-medium"><DownloadSimple size={14} />Download</a></div>
                                                                            </div>
                                                                        );
                                                                    }
                                                                    let displayValue;
                                                                    if (Array.isArray(value)) displayValue = value.map(v => typeof v === 'object' ? JSON.stringify(v) : String(v)).join(', ') || '-';
                                                                    else if (typeof value === 'object' && value !== null) displayValue = JSON.stringify(value);
                                                                    else displayValue = String(value || '-');
                                                                    return (
                                                                        <div key={key} data-testid={`step-data-${step.order}-${key}`}>
                                                                            <span className="text-xs text-muted-foreground capitalize">{label}</span>
                                                                            <p className="text-sm font-medium text-foreground">{displayValue}</p>
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        </div>
                                                    )}
                                                    {(!stepData || Object.keys(stepData).length === 0) && status !== 'pending' && (
                                                        <div className="px-4 py-2 border-t border-border bg-background/50">
                                                            <p className="text-xs text-muted-foreground italic">{t('dash_no_data')}</p>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            ) : null}
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
