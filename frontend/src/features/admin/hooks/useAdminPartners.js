import { useMemo, useState } from 'react';
import { usePagination } from '../../../components/PaginationControls';

export function useAdminPartners() {
    const [partners, setPartners] = useState([]);
    const [editingPartner, setEditingPartner] = useState(null);
    const [showPartnerDialog, setShowPartnerDialog] = useState(false);
    const [showLinkDialog, setShowLinkDialog] = useState(null);
    const [partnerView, setPartnerView] = useState('active');
    const visiblePartners = useMemo(() => partners.filter((partner) => partnerView === 'pending' ? partner.registration_status === 'pending' : partner.registration_status !== 'pending'), [partners, partnerView]);
    const partnersPagination = usePagination(visiblePartners, `admin-partners-${partnerView}`);
    return { partners, setPartners, editingPartner, setEditingPartner, showPartnerDialog, setShowPartnerDialog, showLinkDialog, setShowLinkDialog, partnerView, setPartnerView, visiblePartners, partnersPagination };
}
