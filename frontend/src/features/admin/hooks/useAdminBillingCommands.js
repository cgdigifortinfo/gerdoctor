import { adminAPI, formatApiError, settingsAPI } from '../../../lib/api';
import { toast } from 'sonner';

export function useAdminBillingCommands({ setSettingsSaving, siteSettings, loadData, setStripeAuditLoading, setStripeAudit }) {
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
    return { handleSaveSettings, auditStripeConnections, repairStripeConnection, repairAllStripeConnections };
}
