









import { TabsContent } from '../../../components/ui/tabs';







import { LandingPagesSection, CmsSection } from '../AdminDashboardComponents/AdminCmsSections';

// Stryker disable all: declarative React adapter over tested CMS commands and state.
export function CmsTab(props) {
    const { surveys, cmsHome, setCmsHome, cmsAbout, setCmsAbout, cmsPartners, setCmsPartners, cmsLandingPages, setCmsLandingPages, cmsHomeTrans, setCmsHomeTrans, cmsAboutTrans, setCmsAboutTrans, cmsPartnersTrans, setCmsPartnersTrans, cmsLandingPagesTrans, setCmsLandingPagesTrans, cmsSaving, handleSaveCms } = props;
    return (
<TabsContent value="cms">
                        <div className="space-y-6">
                            <LandingPagesSection
                                content={cmsLandingPages}
                                onChange={setCmsLandingPages}
                                translations={cmsLandingPagesTrans}
                                onTransChange={setCmsLandingPagesTrans}
                                surveys={surveys}
                                onSave={() => handleSaveCms('landing_pages', cmsLandingPages, cmsLandingPagesTrans)}
                                saving={cmsSaving}
                            />

                            {/* Home Section */}
                            <CmsSection
                                title="Home / Hero Section"
                                fields={[
                                    { key: 'hero_title', label: 'Hero Title', type: 'text', placeholder: 'Transform Your Business Journey' },
                                    { key: 'hero_subtitle', label: 'Hero Subtitle', type: 'textarea', placeholder: 'A guided experience to connect you with the right partners' },
                                    { key: 'hero_cta', label: 'CTA Button Text', type: 'text', placeholder: 'Get Started' },
                                    { key: 'box1_title', label: 'Feature-Box 1 · Titel', type: 'text', placeholder: 'Guided Onboarding' },
                                    { key: 'box1_description', label: 'Feature-Box 1 · Beschreibung', type: 'textarea', placeholder: 'Step-by-step process to complete your profile…' },
                                    { key: 'box2_title', label: 'Feature-Box 2 · Titel', type: 'text', placeholder: 'Partner Network' },
                                    { key: 'box2_description', label: 'Feature-Box 2 · Beschreibung', type: 'textarea', placeholder: 'Access our curated network…' },
                                    { key: 'box3_title', label: 'Feature-Box 3 · Titel', type: 'text', placeholder: 'Progress Tracking' },
                                    { key: 'box3_description', label: 'Feature-Box 3 · Beschreibung', type: 'textarea', placeholder: 'Monitor your journey…' },
                                ]}
                                content={cmsHome}
                                onChange={setCmsHome}
                                translations={cmsHomeTrans}
                                onTransChange={setCmsHomeTrans}
                                onSave={() => handleSaveCms('home', cmsHome, cmsHomeTrans)}
                                saving={cmsSaving}
                            />

                            {/* About Section */}
                            <CmsSection
                                title="About Us Section"
                                fields={[
                                    { key: 'title', label: 'Section Title', type: 'text', placeholder: 'About Us' },
                                    { key: 'description', label: 'Description', type: 'textarea', placeholder: 'We help businesses connect...' },
                                    { key: 'mission', label: 'Mission Statement', type: 'textarea', placeholder: 'Our mission is to...' }
                                ]}
                                content={cmsAbout}
                                onChange={setCmsAbout}
                                translations={cmsAboutTrans}
                                onTransChange={setCmsAboutTrans}
                                onSave={() => handleSaveCms('about', cmsAbout, cmsAboutTrans)}
                                saving={cmsSaving}
                            />

                            {/* Partners Section */}
                            <CmsSection
                                title="Partners Section"
                                fields={[
                                    { key: 'title', label: 'Section Title', type: 'text', placeholder: 'Our Partners' },
                                    { key: 'description', label: 'Description', type: 'textarea', placeholder: 'Work with industry-leading partners...' }
                                ]}
                                content={cmsPartners}
                                onChange={setCmsPartners}
                                translations={cmsPartnersTrans}
                                onTransChange={setCmsPartnersTrans}
                                onSave={() => handleSaveCms('partners', cmsPartners, cmsPartnersTrans)}
                                saving={cmsSaving}
                            />
                        </div>
                    </TabsContent>
    );
}
