import { adminAPI, formatApiError } from '../../../lib/api';
import { toast } from 'sonner';

export function useAdminUserCommands({ impersonate, navigate, setSelectedUser, setUserPermissionDraft, setShowUserDialog, selectedUser, setSavingUserPermissions, userPermissionDraft, loadPermissionData, loadData, setSelectedUserIds, selectedUserIds, filteredUsers, bulkRole, setShowCreateUserDialog }) {
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
    return { handleImpersonate, handleViewUser, handleSaveUserPermissions, handleUpdateUserRole, handleUpdateUserProgress, toggleUserSelection, toggleSelectAll, handleBulkRoleUpdate, handleExportCsv, handleCreateUser };
}
