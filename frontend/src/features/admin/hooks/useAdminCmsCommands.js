import { adminAPI, formatApiError } from '../../../lib/api';
import { toast } from 'sonner';

export function useAdminCmsCommands({ setCmsSaving, loadData }) {
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
    return { handleSaveCms };
}
