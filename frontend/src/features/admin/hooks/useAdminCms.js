import { useState } from 'react';

export function useAdminCms() {
    const [cmsHome, setCmsHome] = useState({});
    const [cmsAbout, setCmsAbout] = useState({});
    const [cmsPartners, setCmsPartners] = useState({});
    const [cmsLandingPages, setCmsLandingPages] = useState({ pages: [] });
    const [cmsHomeTrans, setCmsHomeTrans] = useState({});
    const [cmsAboutTrans, setCmsAboutTrans] = useState({});
    const [cmsPartnersTrans, setCmsPartnersTrans] = useState({});
    const [cmsLandingPagesTrans, setCmsLandingPagesTrans] = useState({});
    const [cmsLang, setCmsLang] = useState('de');
    const [cmsSaving, setCmsSaving] = useState(false);
    return { cmsHome, setCmsHome, cmsAbout, setCmsAbout, cmsPartners, setCmsPartners, cmsLandingPages, setCmsLandingPages, cmsHomeTrans, setCmsHomeTrans, cmsAboutTrans, setCmsAboutTrans, cmsPartnersTrans, setCmsPartnersTrans, cmsLandingPagesTrans, setCmsLandingPagesTrans, cmsLang, setCmsLang, cmsSaving, setCmsSaving };
}
