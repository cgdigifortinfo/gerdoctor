import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { cmsAPI, partnersAPI } from '../lib/api';
import { Button } from '../components/ui/button';
import { List, X, ArrowRight, Buildings, Users, CheckCircle } from '@phosphor-icons/react';
import { ThemeLangToggle } from '../components/ThemeLangToggle';

export default function Landing() {
    const { user, loading } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [homeContent, setHomeContent] = useState({});
    const [aboutContent, setAboutContent] = useState({});
    const [partnersContent, setPartnersContent] = useState({});
    const [partners, setPartners] = useState([]);

    useEffect(() => {
        // Load CMS content
        const loadContent = async () => {
            try {
                const [homeRes, aboutRes, partnersRes, partnersListRes] = await Promise.all([
                    cmsAPI.get('home'),
                    cmsAPI.get('about'),
                    cmsAPI.get('partners'),
                    partnersAPI.getAll()
                ]);
                setHomeContent(homeRes.data.content || {});
                setAboutContent(aboutRes.data.content || {});
                setPartnersContent(partnersRes.data.content || {});
                setPartners(partnersListRes.data || []);
            } catch (error) {
                console.error('Failed to load content:', error);
            }
        };
        loadContent();
    }, []);

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

    const scrollToSection = (id) => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
        setMobileMenuOpen(false);
    };

    return (
        <div className="min-h-screen bg-background text-foreground">
            {/* Header */}
            <header className="fixed top-0 left-0 right-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <Link to="/" className="font-black text-xl tracking-tight text-foreground" data-testid="logo">
                            GuidedJourney
                        </Link>

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
                            <Link to="/login">
                                <Button 
                                    className="bg-[#114f55] hover:bg-[#0d3d42] text-white text-sm font-medium px-6"
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
                                Home
                            </button>
                            <button 
                                onClick={() => scrollToSection('about')} 
                                className="block w-full text-left py-2 text-foreground font-medium"
                                data-testid="mobile-nav-about"
                            >
                                About Us
                            </button>
                            <button 
                                onClick={() => scrollToSection('partners')} 
                                className="block w-full text-left py-2 text-foreground font-medium"
                                data-testid="mobile-nav-partners"
                            >
                                Partners
                            </button>
                            <Link to="/login" className="block">
                                <Button 
                                    className="w-full bg-[#114f55] hover:bg-[#0d3d42] text-white"
                                    data-testid="mobile-nav-login-btn"
                                >
                                    Login
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
                            <p className="text-xs tracking-[0.2em] uppercase font-bold text-[#114f55] mb-4">
                                Your Partner Network
                            </p>
                            <h1 className="text-4xl sm:text-5xl lg:text-6xl tracking-tighter leading-none font-black text-foreground mb-6">
                                {homeContent.hero_title || 'Transform Your Business Journey'}
                            </h1>
                            <p className="text-base leading-relaxed text-muted-foreground mb-8 max-w-lg">
                                {homeContent.hero_subtitle || 'A guided experience to connect you with the right partners and accelerate your growth.'}
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Link to="/register">
                                    <Button 
                                        className="w-full sm:w-auto bg-[#114f55] hover:bg-[#0d3d42] text-white px-8 py-3 text-sm font-medium"
                                        data-testid="hero-cta-btn"
                                    >
                                        {homeContent.hero_cta || 'Get Started'}
                                        <ArrowRight className="ml-2" size={16} />
                                    </Button>
                                </Link>
                                <Button 
                                    variant="outline" 
                                    className="w-full sm:w-auto border-border text-foreground hover:bg-background px-8 py-3 text-sm font-medium"
                                    onClick={() => scrollToSection('about')}
                                    data-testid="hero-learn-more-btn"
                                >
                                    Learn More
                                </Button>
                            </div>
                        </div>
                        <div className="relative">
                            <img 
                                src="https://images.pexels.com/photos/3137084/pexels-photo-3137084.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" 
                                alt="Modern architecture"
                                className="rounded-sm shadow-2xl max-h-[60vh] w-full object-cover"
                            />
                            <div className="absolute -bottom-6 -left-6 bg-card p-6 shadow-lg rounded-sm border border-border">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center">
                                        <CheckCircle size={24} className="text-white" />
                                    </div>
                                    <div>
                                        <p className="text-2xl font-black text-foreground">500+</p>
                                        <p className="text-sm text-muted-foreground">Successful Partnerships</p>
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
                        <div className="p-8 border border-border rounded-sm card-hover">
                            <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center mb-6">
                                <Users size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold tracking-tight text-foreground mb-3">Guided Onboarding</h3>
                            <p className="text-muted-foreground">Step-by-step process to complete your profile and find the perfect partner match.</p>
                        </div>
                        <div className="p-8 border border-border rounded-sm card-hover">
                            <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center mb-6">
                                <Buildings size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold tracking-tight text-foreground mb-3">Partner Network</h3>
                            <p className="text-muted-foreground">Access our curated network of industry-leading partners across multiple sectors.</p>
                        </div>
                        <div className="p-8 border border-border rounded-sm card-hover">
                            <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center mb-6">
                                <CheckCircle size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold tracking-tight text-foreground mb-3">Progress Tracking</h3>
                            <p className="text-muted-foreground">Monitor your journey with real-time progress updates and status notifications.</p>
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
                            <p className="text-xs tracking-[0.2em] uppercase font-bold text-[#114f55] mb-4">
                                Who We Are
                            </p>
                            <h2 className="text-2xl sm:text-3xl lg:text-4xl tracking-tight leading-tight font-bold text-foreground mb-6">
                                {aboutContent.title || 'About Us'}
                            </h2>
                            <p className="text-base leading-relaxed text-muted-foreground mb-6">
                                {aboutContent.description || 'We help businesses connect with the right partners through a streamlined onboarding process. Our platform simplifies the journey from initial contact to successful partnership.'}
                            </p>
                            <p className="text-base leading-relaxed text-muted-foreground">
                                {aboutContent.mission || 'Our mission is to simplify business partnerships and create meaningful connections that drive growth and innovation.'}
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Partners Section */}
            <section id="partners" className="py-20 px-4 sm:px-6 lg:px-8 bg-card border-t border-border">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-12">
                        <p className="text-xs tracking-[0.2em] uppercase font-bold text-[#114f55] mb-4">
                            Our Network
                        </p>
                        <h2 className="text-2xl sm:text-3xl lg:text-4xl tracking-tight leading-tight font-bold text-foreground mb-4">
                            {partnersContent.title || 'Our Partners'}
                        </h2>
                        <p className="text-muted-foreground max-w-2xl mx-auto">
                            {partnersContent.description || 'Work with industry-leading partners to achieve your goals.'}
                        </p>
                    </div>
                    
                    <div className="grid md:grid-cols-3 gap-6">
                        {partners.length > 0 ? partners.slice(0, 6).map((partner) => (
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
                                Partners will be displayed here
                            </div>
                        )}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-foreground">
                <div className="max-w-3xl mx-auto text-center">
                    <h2 className="text-2xl sm:text-3xl lg:text-4xl tracking-tight leading-tight font-bold text-white mb-6">
                        Ready to Start Your Journey?
                    </h2>
                    <p className="text-[#A1A1AA] mb-8">
                        Join hundreds of businesses that have found their perfect partners through our platform.
                    </p>
                    <Link to="/register">
                        <Button 
                            className="bg-[#114f55] hover:bg-[#0d3d42] text-white px-8 py-3 text-sm font-medium"
                            data-testid="cta-register-btn"
                        >
                            Create Your Account
                            <ArrowRight className="ml-2" size={16} />
                        </Button>
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-border">
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                        <p className="font-black text-lg text-foreground">GuidedJourney</p>
                        <p className="text-sm text-muted-foreground">&copy; 2026 GuidedJourney. All rights reserved.</p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
