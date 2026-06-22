import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { cmsAPI, partnersAPI, surveysAPI } from '../lib/api';
import { Button } from '../components/ui/button';
import { List, X, ArrowRight, Buildings, Users, CheckCircle } from '@phosphor-icons/react';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { Logo } from '../components/Logo';

export default function Landing() {
    const { user, loading } = useAuth();
    const { surveySlug, landingSlug } = useParams();
    const location = useLocation();
    const { t, localizeCms, lang } = useLanguage();
    const navigate = useNavigate();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [homeContent, setHomeContent] = useState({});
    const [homeTrans, setHomeTrans] = useState({});
    const [aboutContent, setAboutContent] = useState({});
    const [aboutTrans, setAboutTrans] = useState({});
    const [partnersContent, setPartnersContent] = useState({});
    const [partnersTrans, setPartnersTrans] = useState({});
    const [landingPages, setLandingPages] = useState([]);
    const [landingTrans, setLandingTrans] = useState({});
    const [partners, setPartners] = useState([]);
    const [survey, setSurvey] = useState(null);

    useEffect(() => {
        // Load CMS content
        const loadContent = async () => {
            try {
                const [homeRes, aboutRes, partnersRes, landingRes, partnersListRes, surveyRes] = await Promise.all([
                    cmsAPI.get('home'),
                    cmsAPI.get('about'),
                    cmsAPI.get('partners'),
                    cmsAPI.get('landing_pages'),
                    partnersAPI.getAll(),
                    surveySlug ? surveysAPI.getBySlug(surveySlug).catch(() => ({ data: null })) : Promise.resolve({ data: null })
                ]);
                setHomeContent(homeRes.data.content || {});
                setHomeTrans(homeRes.data.translations || {});
                setAboutContent(aboutRes.data.content || {});
                setAboutTrans(aboutRes.data.translations || {});
                setPartnersContent(partnersRes.data.content || {});
                setPartnersTrans(partnersRes.data.translations || {});
                setLandingPages(landingRes.data.content?.pages || []);
                setLandingTrans(landingRes.data.translations || {});
                setPartners(partnersListRes.data || []);
                setSurvey(surveyRes.data);
            } catch (error) {
                console.error('Failed to load content:', error);
            }
        };
        loadContent();
    }, [surveySlug]);

    useEffect(() => {
        // Redirect if logged in
        if (!loading && user) {
            if (user.role === 'admin') {
                navigate('/admin');
            } else if (user.role === 'partner') {
                navigate('/partner-dashboard');
            } else {
                navigate('/dashboard');
            }
        }
    }, [user, loading, navigate]);

    const hc = (field) => localizeCms(homeContent, field, homeTrans);
    const ac = (field) => localizeCms(aboutContent, field, aboutTrans);
    const pc = (field) => localizeCms(partnersContent, field, partnersTrans);
    const scrollToSection = (id) => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
        setMobileMenuOpen(false);
    };
    const normalizePath = (value) => {
        if (!value || value === '/') return '/';
        return value.startsWith('/') ? value.replace(/\/+$/, '') : `/${value.replace(/^\/+|\/+$/g, '')}`;
    };
    const fallbackLandingPages = [
        { id: 'aerzte', path: '/', survey_slug: 'aerzte' },
        {
            id: 'pflege',
            title: 'FSP Pflege',
            path: '/pflege',
            survey_slug: 'pflege',
            partner_tags: 'Pflege Sprachschulung,Pflege Anerkennung,Pflege Arbeitgeber',
            eyebrow: 'Pflege in Deutschland',
            hero_title: 'Anerkennung als Pflegefachkraft in Deutschland',
            hero_subtitle: 'Wir begleiten internationale Pflegekräfte von Registrierung, Fachsprache und Anerkennung bis zum Arbeitseinstieg in Deutschland.',
            hero_cta: 'Jetzt registrieren',
            learn_more_label: 'Mehr zur Pflege-Anerkennung',
            stat_label: 'Von der Anerkennung bis zum Pflegejob',
            box1_title: 'Geführte Anerkennung',
            box1_description: 'Alle Schritte von Unterlagen, Sprache und Bescheid bleiben sichtbar.',
            box2_title: 'Partner für Sprache und Einstieg',
            box2_description: 'Sprachschulen, Vorbereitungspartner und Arbeitgeber können passend eingebunden werden.',
            box3_title: 'Planbarer Fortschritt',
            box3_description: 'Nutzer sehen, was erledigt ist und welcher Schritt als nächstes ansteht.',
            about_eyebrow: 'Für internationale Pflegekräfte',
            about_title: 'Ihr Weg in die Pflege in Deutschland',
            about_description: 'Die Plattform begleitet Pflegekräfte aus dem Ausland bei Registrierung, Fachsprache, Dokumenten und passenden nächsten Schritten.',
            about_mission: 'Unser Ziel: ein verständlicher, planbarer und digital begleiteter Einstieg in den deutschen Pflegeberuf.',
            partners_eyebrow: 'Partner & Vorbereitung',
            partners_title: 'Unterstützung für Prüfung, Anerkennung und Einstieg',
            partners_description: 'Pflege-Surveys können eigene Partner, Prüfungsorte und Vorbereitungsschritte erhalten.',
            cta_title: 'Bereit für Ihren Pflegeweg in Deutschland?',
            cta_description: 'Registrieren Sie sich und starten Sie den passenden Prozess für Anerkennung, Fachsprache und Arbeitseinstieg.',
        },
    ];
    const effectiveLandingPages = landingPages.length ? landingPages : fallbackLandingPages;
    const currentPath = normalizePath(location.pathname);
    const currentLanding = effectiveLandingPages.find(page => normalizePath(page.path) === currentPath)
        || effectiveLandingPages.find(page => surveySlug && page.survey_slug === surveySlug)
        || effectiveLandingPages.find(page => landingSlug && normalizePath(page.path) === `/${landingSlug}`)
        || (surveySlug ? null : effectiveLandingPages.find(page => normalizePath(page.path) === '/'));
    const landingTranslation = currentLanding?.id ? landingTrans?.[lang]?.[currentLanding.id] : null;
    const lp = (field, fallback = '') => landingTranslation?.[field] || currentLanding?.[field] || fallback;
    const activeSurveySlug = currentLanding?.survey_slug || surveySlug || survey?.slug || '';
    const loginPath = activeSurveySlug ? `/s/${activeSurveySlug}/login` : '/login';
    const registerPath = activeSurveySlug ? `/s/${activeSurveySlug}/register` : '/register';
    const partnerTags = (lp('partner_tags') || 'Antragstellung,Kenntnisprüfung,Weiterbildung')
        .split(',')
        .map(tag => tag.trim())
        .filter(Boolean);
    const isCustomLanding = Boolean(currentLanding);

    return (
        <div className="min-h-screen bg-background text-foreground">
            {/* Header */}
            <header className="fixed top-0 left-0 right-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <Logo />

                        {/* Desktop Nav */}
                        <nav className="hidden md:flex items-center gap-8">
                            <button 
                                onClick={() => scrollToSection('home')} 
                                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                                data-testid="nav-home"
                            >
                                {t('nav_home')}
                            </button>
                            <button 
                                onClick={() => scrollToSection('about')} 
                                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                                data-testid="nav-about"
                            >
                                {t('nav_about')}
                            </button>
                            <button 
                                onClick={() => scrollToSection('partners')} 
                                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                                data-testid="nav-partners"
                            >
                                {t('nav_partners')}
                            </button>
                            <ThemeLangToggle />
                            <Link to={loginPath}>
                                <Button 
                                    className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white text-sm font-medium px-6"
                                    data-testid="nav-login-btn"
                                >
                                    {t('nav_login')}
                                </Button>
                            </Link>
                        </nav>

                        {/* Mobile Menu Button */}
                        <button 
                            className="md:hidden p-2"
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            data-testid="mobile-menu-btn"
                        >
                            {mobileMenuOpen ? <X size={24} /> : <List size={24} />}
                        </button>
                    </div>
                </div>

                {/* Mobile Menu */}
                {mobileMenuOpen && (
                    <div className="md:hidden bg-card border-t border-border">
                        <div className="px-4 py-4 space-y-3">
                            <button 
                                onClick={() => scrollToSection('home')} 
                                className="block w-full text-left py-2 text-foreground font-medium"
                                data-testid="mobile-nav-home"
                            >
                                {t('nav_home')}
                            </button>
                            <button 
                                onClick={() => scrollToSection('about')} 
                                className="block w-full text-left py-2 text-foreground font-medium"
                                data-testid="mobile-nav-about"
                            >
                                {t('nav_about')}
                            </button>
                            <button 
                                onClick={() => scrollToSection('partners')} 
                                className="block w-full text-left py-2 text-foreground font-medium"
                                data-testid="mobile-nav-partners"
                            >
                                {t('nav_partners')}
                            </button>
                            <div className="flex items-center gap-2 py-2">
                                <ThemeLangToggle />
                            </div>
                            <Link to={loginPath} className="block">
                                <Button 
                                    className="w-full bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white"
                                    data-testid="mobile-nav-login-btn"
                                >
                                    {t('nav_login')}
                                </Button>
                            </Link>
                        </div>
                    </div>
                )}
            </header>

            {/* Hero Section */}
            <section id="home" className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="grid md:grid-cols-2 gap-12 items-center">
                        <div className="animate-fadeIn">
                            <p className="text-xs tracking-[0.2em] uppercase font-bold text-[var(--brand-primary)] mb-4">
                                {lp('eyebrow', 'Praktizieren in Deutschland')}
                            </p>
                            <h1 className="text-3xl sm:text-4xl lg:text-5xl leading-none font-black text-foreground mb-6">
                                {lp('hero_title', hc('hero_title') || 'IHCA - dein persönlicher Weg zum Facharzt in Deutschland')}
                            </h1>
                            <p className="text-base leading-relaxed text-muted-foreground mb-8 max-w-lg">
                                {lp('hero_subtitle', hc('hero_subtitle') || 'Von der Vorbereitung bis zum Arbeitseinstieg unterstuetzen wir vollumfaenglich')}
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Link to={registerPath}>
                                    <Button 
                                        className="w-full sm:w-auto bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white px-8 py-3 text-sm font-medium"
                                        data-testid="hero-cta-btn"
                                    >
                                        {lp('hero_cta', hc('hero_cta') || 'Jetzt starten')}
                                        <ArrowRight className="ml-2" size={16} />
                                    </Button>
                                </Link>
                                <Button 
                                    variant="outline" 
                                    className="w-full sm:w-auto border-border text-foreground hover:bg-background px-8 py-3 text-sm font-medium"
                                    onClick={() => scrollToSection('about')}
                                    data-testid="hero-learn-more-btn"
                                >
                                    {lp('learn_more_label', 'Mehr erfahren')}
                                </Button>
                            </div>
                        </div>
                        <div className="relative">
                            <img 
                                src={lp('hero_image_url', 'https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/5fd3c87e94b794ef345545f4831b1564009ab10cecdbca63c977b897e96e5b8a.png')}
                                alt={lp('hero_image_alt', lp('hero_title', 'Anerkennungsprozess in Deutschland'))}
                                className="rounded-sm shadow-2xl max-h-[60vh] w-full object-cover"
                            />
                            <div className="absolute -bottom-6 -left-6 bg-card p-6 shadow-lg rounded-sm border border-border">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-[var(--brand-primary)] rounded-sm flex items-center justify-center">
                                        <CheckCircle size={24} className="text-white" />
                                    </div>
                                    <div>
                                        <p className="text-2xl font-black text-foreground">{lp('stat_value', '100%')}</p>
                                        <p className="text-sm text-muted-foreground">{lp('stat_label', 'Der schnellste Weg zur Approbation')}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-card border-y border-border">
                <div className="max-w-7xl mx-auto">
                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="p-8 border border-border rounded-sm card-hover" data-testid="feature-box-1">
                            <div className="w-12 h-12 bg-[var(--brand-primary)] rounded-sm flex items-center justify-center mb-6">
                                <Users size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-foreground mb-3">
                                {lp('box1_title', localizeCms(homeContent, 'box1_title', homeTrans) || 'Guided Onboarding')}
                            </h3>
                            <p className="text-muted-foreground">
                                {lp('box1_description', localizeCms(homeContent, 'box1_description', homeTrans) || 'Step-by-step process to complete your profile and find the perfect partner match.')}
                            </p>
                        </div>
                        <div className="p-8 border border-border rounded-sm card-hover" data-testid="feature-box-2">
                            <div className="w-12 h-12 bg-[var(--brand-primary)] rounded-sm flex items-center justify-center mb-6">
                                <Buildings size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-foreground mb-3">
                                {lp('box2_title', localizeCms(homeContent, 'box2_title', homeTrans) || 'Partner Network')}
                            </h3>
                            <p className="text-muted-foreground">
                                {lp('box2_description', localizeCms(homeContent, 'box2_description', homeTrans) || 'Access our curated network of industry-leading partners across multiple sectors.')}
                            </p>
                        </div>
                        <div className="p-8 border border-border rounded-sm card-hover" data-testid="feature-box-3">
                            <div className="w-12 h-12 bg-[var(--brand-primary)] rounded-sm flex items-center justify-center mb-6">
                                <CheckCircle size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-foreground mb-3">
                                {lp('box3_title', localizeCms(homeContent, 'box3_title', homeTrans) || 'Progress Tracking')}
                            </h3>
                            <p className="text-muted-foreground">
                                {lp('box3_description', localizeCms(homeContent, 'box3_description', homeTrans) || 'Monitor your journey with real-time progress updates and status notifications.')}
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* About Section */}
            <section id="about" className="py-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="grid md:grid-cols-2 gap-12 items-center">
                        <div className="order-2 md:order-1">
                            <img 
                                src="https://images.unsplash.com/photo-1758873271902-a63ecd5b5235?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzh8MHwxfHNlYXJjaHwzfHxtb2Rlcm4lMjBzdGFydHVwJTIwdGVhbSUyMHdvcmtpbmd8ZW58MHx8fHwxNzc2MTUyMzY3fDA&ixlib=rb-4.1.0&q=85" 
                                alt="Team working"
                                className="rounded-sm shadow-lg max-h-[50vh] w-full object-cover"
                            />
                        </div>
                        <div className="order-1 md:order-2">
                            <p className="text-xs tracking-[0.2em] uppercase font-bold text-[var(--brand-primary)] mb-4">
                                {lp('about_eyebrow', 'Who We Are')}
                            </p>
                            <h2 className="text-2xl sm:text-3xl lg:text-4xl leading-tight font-bold text-foreground mb-6">
                                {lp('about_title', ac('title') || 'About Us')}
                            </h2>
                            <p className="text-base leading-relaxed text-muted-foreground mb-6">
                                {lp('about_description', ac('description') || 'We help connect international professionals with the right partners.')}
                            </p>
                            <p className="text-base leading-relaxed text-muted-foreground">
                                {lp('about_mission', ac('mission') || 'The easy way to your German recognition process.')}
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Partners Section */}
            <section id="partners" className="py-20 px-4 sm:px-6 lg:px-8 bg-card border-t border-border">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-12">
                        <p className="text-xs tracking-[0.2em] uppercase font-bold text-[var(--brand-primary)] mb-4">
                            {lp('partners_eyebrow', 'Our Network')}
                        </p>
                        <h2 className="text-2xl sm:text-3xl lg:text-4xl leading-tight font-bold text-foreground mb-4">
                            {lp('partners_title', pc('title') || 'Our Partners')}
                        </h2>
                        <p className="text-muted-foreground max-w-2xl mx-auto">
                            {lp('partners_description', pc('description') || 'Work with industry-leading partners.')}
                        </p>
                    </div>
                    
                    <div className="grid md:grid-cols-3 gap-6">
                        {(() => {
                            const filtered = partners.filter(p => (p.tags || []).some(t => partnerTags.includes(t)));
                            return filtered.length > 0 ? filtered.slice(0, 9).map((partner) => (
                            <div 
                                key={partner.id} 
                                className="partner-card p-6 rounded-sm bg-card"
                                data-testid={`partner-card-${partner.id}`}
                            >
                                {partner.logo_url && (
                                    <img 
                                        src={partner.logo_url} 
                                        alt={partner.name}
                                        className="w-16 h-16 object-cover rounded-sm mb-4"
                                    />
                                )}
                                <h3 className="text-lg font-semibold text-foreground mb-2">{partner.name}</h3>
                                <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{partner.description}</p>
                                {partner.category && (
                                    <span className="inline-block px-3 py-1 text-xs font-medium bg-background text-muted-foreground rounded-sm">
                                        {partner.category}
                                    </span>
                                )}
                            </div>
                        )) : (
                            <div className="col-span-3 text-center py-12 text-muted-foreground">
                                Partner werden hier angezeigt
                            </div>
                        );
                        })()}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-foreground">
                <div className="max-w-3xl mx-auto text-center">
                    <h2 className="text-2xl sm:text-3xl lg:text-4xl leading-tight font-bold text-white mb-6">
                        {lp('cta_title', 'Ready to Start Your Journey?')}
                    </h2>
                    <p className="text-[#A1A1AA] mb-8">
                        {lp('cta_description', 'Create your account and follow a guided recognition process.')}
                    </p>
                    <Link to={registerPath}>
                        <Button 
                            className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white px-8 py-3 text-sm font-medium"
                            data-testid="cta-register-btn"
                        >
                            {lp('hero_cta', 'Create Your Account')}
                            <ArrowRight className="ml-2" size={16} />
                        </Button>
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-border">
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                        <div className="flex items-center gap-2">
                            <img src={lp('footer_logo_url', 'https://fsp-pflege.de/wp-content/uploads/2025/02/FSPP-Logo-Final.png')} alt={lp('title', 'FSP Pflege')} className="h-9 w-auto object-contain" />
                            <span className="text-[10px] font-medium text-muted-foreground">Powered by DigiFORT</span>
                        </div>
                        <p className="text-sm text-muted-foreground">{lp('footer_text', isCustomLanding ? '' : '© 2026 FSP Pflege. Alle Rechte vorbehalten.')}</p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
