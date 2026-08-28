

import { Button } from '../../../components/ui/button';



import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';


import { Checkbox } from '../../../components/ui/checkbox';
import { TabsContent } from '../../../components/ui/tabs';
import {    Eye,       UserPlus,   DownloadSimple,       UserSwitch } from '@phosphor-icons/react';



import PermissionGroupsManager from '../../../components/admin/PermissionGroupsManager';
import { PaginationControls } from '../../../components/PaginationControls';
import { SearchToolbar, SegmentedControl, TableEmptyState } from '../../../components/collections';
import { allUsersSelected, hasItems, registrationBadge, userCompletion } from '../adminTabViewModels';



// Stryker disable all: declarative adapter; presentation derivations live in adminTabViewModels.
export function UsersTab(props) {
    const { t, users, userSearch, setUserSearch, userRoleFilter, setUserRoleFilter, setShowCreateUserDialog, userManagementView, setUserManagementView, permissionGroups, permissionCatalog, selectedUserIds, setSelectedUserIds, bulkRole, setBulkRole, can, handleImpersonate, loadPermissionData, filteredUsers, usersPagination, handleViewUser, handleUpdateUserRole, toggleUserSelection, toggleSelectAll, handleBulkRoleUpdate, handleExportCsv } = props;
    return (
<TabsContent value="users">
                        <SegmentedControl className="mb-4" value={userManagementView} onChange={setUserManagementView} testId="user-management-sections" options={[
                            { value: 'users', label: 'Benutzer', testId: 'show-user-list', hidden: !can('users.view') },
                            { value: 'groups', label: 'Nutzergruppen & Rechte', testId: 'show-permission-groups', hidden: !can('groups.view') },
                        ]} />
                        {userManagementView === 'groups' && can('groups.view') && <PermissionGroupsManager groups={permissionGroups} catalog={permissionCatalog} onRefresh={loadPermissionData} canCreate={can('groups.create')} canUpdate={can('groups.update')} canDelete={can('groups.delete')} />}
                        <div className={`bg-card border border-border rounded-sm ${userManagementView === 'groups' || !can('users.view') ? 'hidden' : ''}`}>
                            <div className="p-4 border-b border-border">
                                <h2 className="mb-3 text-lg font-semibold text-foreground">User Management</h2>
                                <SearchToolbar value={userSearch} onChange={setUserSearch} placeholder="Search by name or email..." inputTestId="user-search-input" summary={`${filteredUsers.length} of ${users.length} users`} filters={
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
                                } actions={<>
                                        {can('users.export') && <Button variant="outline" onClick={handleExportCsv} className="border-border text-muted-foreground" data-testid="export-csv-btn">
                                            <DownloadSimple size={16} className="mr-1" /> Export CSV
                                        </Button>}
                                        {can('users.create') && <Button onClick={() => setShowCreateUserDialog(true)} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white" data-testid="create-user-btn">
                                            <UserPlus size={16} className="mr-1" /> {t('admin_create_user')}
                                        </Button>}
                                </>} />
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
                                                    checked={allUsersSelected(selectedUserIds, filteredUsers)}
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
                                        {usersPagination.paginatedItems.map((u) => {
                                            const registration = registrationBadge(u.pending_registrations, u.role);
                                            return (
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
                                                    {registration.kind === 'admin' ? (
                                                        <span className="text-xs text-muted-foreground">-</span>
                                                    ) : registration.kind === 'pending' ? (
                                                        <span
                                                            className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 rounded-full"
                                                            title={registration.title}
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
                                                    {hasItems(u.partner_names) ? (
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
                                                    {hasItems(u.orphaned_partner_references) && (
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
                                                            <div className="h-full bg-[var(--brand-primary)] rounded-full transition-all" style={{ width: `${userCompletion(u)}%` }} />
                                                        </div>
                                                        <span className="text-xs text-muted-foreground font-medium">{userCompletion(u)}%</span>
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
                                            );
                                        })}
                                        {filteredUsers.length === 0 && <TableEmptyState colSpan={10} title="No users found" />}
                                    </tbody>
                                </table>
                            </div>
                            <PaginationControls pagination={usersPagination} id="admin-users" />
                        </div>
                    </TabsContent>
    );
}
