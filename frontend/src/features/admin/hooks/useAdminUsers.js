import { useMemo, useState } from 'react';
import { usePagination } from '../../../components/PaginationControls';

export function useAdminUsers() {
    const [users, setUsers] = useState([]);
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
    const [selectedUserIds, setSelectedUserIds] = useState([]);
    const [bulkRole, setBulkRole] = useState('user');

    const filteredUsers = useMemo(() => users.filter((candidate) => {
        const search = userSearch.toLowerCase();
        const matchesSearch = !search || candidate.name.toLowerCase().includes(search) || candidate.email.toLowerCase().includes(search);
        return matchesSearch && (userRoleFilter === 'all' || candidate.role === userRoleFilter);
    }), [users, userSearch, userRoleFilter]);
    const permissionOptions = useMemo(() => (permissionCatalog.categories || []).flatMap((category) => category.permissions.map((permission) => ({
        value: permission.key,
        label: permission.label,
        description: category.category,
        keywords: `${permission.key} ${permission.description}`,
    }))), [permissionCatalog]);
    const selectedUserGroupOptions = useMemo(() => permissionGroups
        .filter((group) => !selectedUser || group.role === selectedUser.role)
        .map((group) => ({
            value: group.id,
            label: group.name,
            description: `${group.member_count} Mitglieder · ${group.permissions?.includes('*') ? 'Alle Rechte' : `${group.permissions?.length || 0} Rechte`}`,
            keywords: `${group.role} ${group.description || ''}`,
        })), [permissionGroups, selectedUser]);
    const usersPagination = usePagination(filteredUsers, 'admin-users', { resetKey: `${userSearch}|${userRoleFilter}` });

    return { users, setUsers, selectedUser, setSelectedUser, showUserDialog, setShowUserDialog, userSearch, setUserSearch, userRoleFilter, setUserRoleFilter, showCreateUserDialog, setShowCreateUserDialog, userManagementView, setUserManagementView, permissionGroups, setPermissionGroups, permissionCatalog, setPermissionCatalog, userPermissionDraft, setUserPermissionDraft, savingUserPermissions, setSavingUserPermissions, selectedUserIds, setSelectedUserIds, bulkRole, setBulkRole, filteredUsers, permissionOptions, selectedUserGroupOptions, usersPagination };
}
