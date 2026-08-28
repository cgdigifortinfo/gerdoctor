import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
    SignOut, Users, ListChecks, Buildings, ChartBar, Notebook,
    ClockCounterClockwise, GearSix, Envelope, BellRinging
} from '@phosphor-icons/react';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { Logo } from '../components/Logo';
import { useAdminDashboardController } from '../features/admin/useAdminDashboardController';
import { AdminDialogs } from '../features/admin/AdminDialogs';
import { AnalyticsTab } from '../features/admin/tabs/AnalyticsTab';
import { UsersTab } from '../features/admin/tabs/UsersTab';
import { StepsTab } from '../features/admin/tabs/StepsTab';
import { PartnersTab } from '../features/admin/tabs/PartnersTab';
import { CmsTab } from '../features/admin/tabs/CmsTab';
import { EmailTemplatesTab } from '../features/admin/tabs/EmailTemplatesTab';
import { EventsTab } from '../features/admin/tabs/EventsTab';
import { AuditTab } from '../features/admin/tabs/AuditTab';
import { SettingsTab } from '../features/admin/tabs/SettingsTab';

// Stryker disable all: declarative dashboard composition; controller and tabs own the logic.
export default function AdminDashboard() {
    const controller = useAdminDashboardController();
    const { user, t, activeTab, setActiveTab, partners, can, handleLogout, loading } = controller;
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
                    <AnalyticsTab analytics={controller.analytics} analyticsPagination={controller.analyticsPagination} />

                    {/* ============ USERS TAB ============ */}
                    <UsersTab t={controller.t} users={controller.users} userSearch={controller.userSearch} setUserSearch={controller.setUserSearch} userRoleFilter={controller.userRoleFilter} setUserRoleFilter={controller.setUserRoleFilter} setShowCreateUserDialog={controller.setShowCreateUserDialog} userManagementView={controller.userManagementView} setUserManagementView={controller.setUserManagementView} permissionGroups={controller.permissionGroups} permissionCatalog={controller.permissionCatalog} selectedUserIds={controller.selectedUserIds} setSelectedUserIds={controller.setSelectedUserIds} bulkRole={controller.bulkRole} setBulkRole={controller.setBulkRole} can={controller.can} handleImpersonate={controller.handleImpersonate} loadPermissionData={controller.loadPermissionData} filteredUsers={controller.filteredUsers} usersPagination={controller.usersPagination} handleViewUser={controller.handleViewUser} handleUpdateUserRole={controller.handleUpdateUserRole} toggleUserSelection={controller.toggleUserSelection} toggleSelectAll={controller.toggleSelectAll} handleBulkRoleUpdate={controller.handleBulkRoleUpdate} handleExportCsv={controller.handleExportCsv} />

                    {/* ============ STEPS TAB ============ */}
                    <StepsTab t={controller.t} steps={controller.steps} surveys={controller.surveys} activeSurveyId={controller.activeSurveyId} setEditingStep={controller.setEditingStep} setShowStepDialog={controller.setShowStepDialog} stepTemplates={controller.stepTemplates} showTemplatesPanel={controller.showTemplatesPanel} setShowTemplatesPanel={controller.setShowTemplatesPanel} stepsView={controller.stepsView} setStepsView={controller.setStepsView} loadData={controller.loadData} sortedSteps={controller.sortedSteps} templatesPagination={controller.templatesPagination} stepsPagination={controller.stepsPagination} handleCreateSurvey={controller.handleCreateSurvey} handleSurveyChange={controller.handleSurveyChange} handleDeleteStep={controller.handleDeleteStep} handleMoveStep={controller.handleMoveStep} handleSaveStepAsTemplate={controller.handleSaveStepAsTemplate} handleApplyTemplate={controller.handleApplyTemplate} handleDeleteTemplate={controller.handleDeleteTemplate} />

                    {/* ============ PARTNERS TAB ============ */}
                    <PartnersTab users={controller.users} partners={controller.partners} setEditingPartner={controller.setEditingPartner} setShowPartnerDialog={controller.setShowPartnerDialog} setShowLinkDialog={controller.setShowLinkDialog} partnerView={controller.partnerView} setPartnerView={controller.setPartnerView} partnersPagination={controller.partnersPagination} handleDeletePartner={controller.handleDeletePartner} handleUnlinkUser={controller.handleUnlinkUser} />

                    {/* ============ CMS TAB ============ */}
                    <CmsTab surveys={controller.surveys} cmsHome={controller.cmsHome} setCmsHome={controller.setCmsHome} cmsAbout={controller.cmsAbout} setCmsAbout={controller.setCmsAbout} cmsPartners={controller.cmsPartners} setCmsPartners={controller.setCmsPartners} cmsLandingPages={controller.cmsLandingPages} setCmsLandingPages={controller.setCmsLandingPages} cmsHomeTrans={controller.cmsHomeTrans} setCmsHomeTrans={controller.setCmsHomeTrans} cmsAboutTrans={controller.cmsAboutTrans} setCmsAboutTrans={controller.setCmsAboutTrans} cmsPartnersTrans={controller.cmsPartnersTrans} setCmsPartnersTrans={controller.setCmsPartnersTrans} cmsLandingPagesTrans={controller.cmsLandingPagesTrans} setCmsLandingPagesTrans={controller.setCmsLandingPagesTrans} cmsSaving={controller.cmsSaving} handleSaveCms={controller.handleSaveCms} />

                    {/* ============ MESSAGE TEMPLATES TAB ============ */}
                    <EmailTemplatesTab  />

                    {/* ============ DOMAIN EVENTS TAB ============ */}
                    <EventsTab  />

                    {/* ============ AUDIT LOG TAB ============ */}
                    <AuditTab t={controller.t} auditLogs={controller.auditLogs} auditActionTypes={controller.auditActionTypes} auditFilter={controller.auditFilter} setAuditFilter={controller.setAuditFilter} auditDateFrom={controller.auditDateFrom} setAuditDateFrom={controller.setAuditDateFrom} auditDateTo={controller.auditDateTo} setAuditDateTo={controller.setAuditDateTo} auditPagination={controller.auditPagination} handleAuditFilter={controller.handleAuditFilter} handleClearAuditFilter={controller.handleClearAuditFilter} />

                    {/* ============ SETTINGS TAB ============ */}
                    <SettingsTab t={controller.t} adminBilling={controller.adminBilling} stripeAudit={controller.stripeAudit} stripeAuditLoading={controller.stripeAuditLoading} siteSettings={controller.siteSettings} setSiteSettings={controller.setSiteSettings} settingsSaving={controller.settingsSaving} handleSaveSettings={controller.handleSaveSettings} auditStripeConnections={controller.auditStripeConnections} repairStripeConnection={controller.repairStripeConnection} repairAllStripeConnections={controller.repairAllStripeConnections} />
                </Tabs>
            </div>

            <AdminDialogs t={controller.t} users={controller.users} steps={controller.steps} surveys={controller.surveys} activeSurveyId={controller.activeSurveyId} partners={controller.partners} selectedUser={controller.selectedUser} showUserDialog={controller.showUserDialog} setShowUserDialog={controller.setShowUserDialog} showCreateUserDialog={controller.showCreateUserDialog} setShowCreateUserDialog={controller.setShowCreateUserDialog} permissionGroups={controller.permissionGroups} userPermissionDraft={controller.userPermissionDraft} setUserPermissionDraft={controller.setUserPermissionDraft} savingUserPermissions={controller.savingUserPermissions} editingStep={controller.editingStep} setEditingStep={controller.setEditingStep} showStepDialog={controller.showStepDialog} setShowStepDialog={controller.setShowStepDialog} editingPartner={controller.editingPartner} setEditingPartner={controller.setEditingPartner} showPartnerDialog={controller.showPartnerDialog} setShowPartnerDialog={controller.setShowPartnerDialog} showLinkDialog={controller.showLinkDialog} setShowLinkDialog={controller.setShowLinkDialog} confirmDialog={controller.confirmDialog} setConfirmDialog={controller.setConfirmDialog} siteSettings={controller.siteSettings} can={controller.can} permissionOptions={controller.permissionOptions} selectedUserGroupOptions={controller.selectedUserGroupOptions} handleSaveUserPermissions={controller.handleSaveUserPermissions} handleUpdateUserProgress={controller.handleUpdateUserProgress} handleSaveStep={controller.handleSaveStep} handleSurveyChange={controller.handleSurveyChange} handleSavePartner={controller.handleSavePartner} handleLinkUser={controller.handleLinkUser} handleCreateUser={controller.handleCreateUser} />
        </div>
    );
}
