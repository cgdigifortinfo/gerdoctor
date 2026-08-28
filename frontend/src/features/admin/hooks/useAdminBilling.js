import { useState } from 'react';
import { DEFAULT_SITE_SETTINGS } from '../adminControllerDomain';

export function useAdminBilling() {
    const [adminBilling, setAdminBilling] = useState({ partners: [], totals: {} });
    const [stripeAudit, setStripeAudit] = useState(null);
    const [stripeAuditLoading, setStripeAuditLoading] = useState(false);
    const [siteSettings, setSiteSettings] = useState(DEFAULT_SITE_SETTINGS);
    const [settingsSaving, setSettingsSaving] = useState(false);
    return { adminBilling, setAdminBilling, stripeAudit, setStripeAudit, stripeAuditLoading, setStripeAuditLoading, siteSettings, setSiteSettings, settingsSaving, setSettingsSaving };
}
