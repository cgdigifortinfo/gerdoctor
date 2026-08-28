import { adminAPI, formatApiError } from '../../../lib/api';
import { toast } from 'sonner';

export function useAdminPartnerCommands({ editingPartner, setShowPartnerDialog, setEditingPartner, loadData, setConfirmDialog, setShowLinkDialog }) {
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
    return { handleSavePartner, handleDeletePartner, handleLinkUser, handleUnlinkUser };
}
