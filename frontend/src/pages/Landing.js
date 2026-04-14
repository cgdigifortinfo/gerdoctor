import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { cmsAPI, partnersAPI } from '../lib/api';
import { Button } from '../components/ui/button';
import { List, X, ArrowRight, Buildings, Users, CheckCircle } from '@phosphor-icons/react';

export default function Landing() {
    const { user, loading } = useAuth();
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
        <div className="min-h-screen bg-[#FAFAFA]">
            {/* Header */}
            <header className="fixed top-0 left-0 right-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <Link to="/" className="font-black text-xl tracking-tight text-[#0A0A0A]" data-testid="logo">
                            GuidedJourney
                        </Link>

                        {/* Desktop Nav */}
                        <nav className="hidden md:flex items-center gap-8">
                            <button 
                                onClick={() => scrollToSection('home')} 
                                className="text-sm font-medium text-[#52525B] hover:text-[#0A0A0A] transition-colors"
                                data-testid="nav-home"
                            >
                                Home
                            </button>
                            <button 
                                onClick={() => scrollToSection('about')} 
                                className="text-sm font-medium text-[#52525B] hover:text-[#0A0A0A] transition-colors"
                                data-testid="nav-about"
                            >
                                About Us
                            </button>
                            <button 
                                onClick={() => scrollToSection('partners')} 
                                className="text-sm font-medium text-[#52525B] hover:text-[#0A0A0A] transition-colors"
                                data-testid="nav-partners"
                            >
                                Partners
                            </button>
                            <Link to="/login">
                                <Button 
                                    className="bg-[#114f55] hover:bg-[#0d3d42] text-white text-sm font-medium px-6"
                                    data-testid="nav-login-btn"
                                >
                                    Login
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
                    <div className="md:hidden bg-white border-t border-[#E4E4E7]">
                        <div className="px-4 py-4 space-y-3">
                            <button 
                                onClick={() => scrollToSection('home')} 
                                className="block w-full text-left py-2 text-[#0A0A0A] font-medium"
                                data-testid="mobile-nav-home"
                            >
                                Home
                            </button>
                            <button 
                                onClick={() => scrollToSection('about')} 
                                className="block w-full text-left py-2 text-[#0A0A0A] font-medium"
                                data-testid="mobile-nav-about"
                            >
                                About Us
                            </button>
                            <button 
                                onClick={() => scrollToSection('partners')} 
                                className="block w-full text-left py-2 text-[#0A0A0A] font-medium"
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
                            <h1 className="text-4xl sm:text-5xl lg:text-6xl tracking-tighter leading-none font-black text-[#0A0A0A] mb-6">
                                {homeContent.hero_title || 'Transform Your Business Journey'}
                            </h1>
                            <p className="text-base leading-relaxed text-[#52525B] mb-8 max-w-lg">
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
                                    className="w-full sm:w-auto border-[#E4E4E7] text-[#0A0A0A] hover:bg-[#FAFAFA] px-8 py-3 text-sm font-medium"
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
                            <div className="absolute -bottom-6 -left-6 bg-white p-6 shadow-lg rounded-sm border border-[#E4E4E7]">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center">
                                        <CheckCircle size={24} className="text-white" />
                                    </div>
                                    <div>
                                        <p className="text-2xl font-black text-[#0A0A0A]">500+</p>
                                        <p className="text-sm text-[#52525B]">Successful Partnerships</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white border-y border-[#E4E4E7]">
                <div className="max-w-7xl mx-auto">
                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="p-8 border border-[#E4E4E7] rounded-sm card-hover">
                            <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center mb-6">
                                <Users size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold tracking-tight text-[#0A0A0A] mb-3">Guided Onboarding</h3>
                            <p className="text-[#52525B]">Step-by-step process to complete your profile and find the perfect partner match.</p>
                        </div>
                        <div className="p-8 border border-[#E4E4E7] rounded-sm card-hover">
                            <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center mb-6">
                                <Buildings size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold tracking-tight text-[#0A0A0A] mb-3">Partner Network</h3>
                            <p className="text-[#52525B]">Access our curated network of industry-leading partners across multiple sectors.</p>
                        </div>
                        <div className="p-8 border border-[#E4E4E7] rounded-sm card-hover">
                            <div className="w-12 h-12 bg-[#114f55] rounded-sm flex items-center justify-center mb-6">
                                <CheckCircle size={24} className="text-white" />
                            </div>
                            <h3 className="text-xl font-semibold tracking-tight text-[#0A0A0A] mb-3">Progress Tracking</h3>
                            <p className="text-[#52525B]">Monitor your journey with real-time progress updates and status notifications.</p>
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
                            <h2 className="text-2xl sm:text-3xl lg:text-4xl tracking-tight leading-tight font-bold text-[#0A0A0A] mb-6">
                                {aboutContent.title || 'About Us'}
                            </h2>
                            <p className="text-base leading-relaxed text-[#52525B] mb-6">
                                {aboutContent.description || 'We help businesses connect with the right partners through a streamlined onboarding process. Our platform simplifies the journey from initial contact to successful partnership.'}
                            </p>
                            <p className="text-base leading-relaxed text-[#52525B]">
                                {aboutContent.mission || 'Our mission is to simplify business partnerships and create meaningful connections that drive growth and innovation.'}
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Partners Section */}
            <section id="partners" className="py-20 px-4 sm:px-6 lg:px-8 bg-white border-t border-[#E4E4E7]">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-12">
                        <p className="text-xs tracking-[0.2em] uppercase font-bold text-[#114f55] mb-4">
                            Our Network
                        </p>
                        <h2 className="text-2xl sm:text-3xl lg:text-4xl tracking-tight leading-tight font-bold text-[#0A0A0A] mb-4">
                            {partnersContent.title || 'Our Partners'}
                        </h2>
                        <p className="text-[#52525B] max-w-2xl mx-auto">
                            {partnersContent.description || 'Work with industry-leading partners to achieve your goals.'}
                        </p>
                    </div>
                    
                    <div className="grid md:grid-cols-3 gap-6">
                        {partners.length > 0 ? partners.slice(0, 6).map((partner) => (
                            <div 
                                key={partner.id} 
                                className="partner-card p-6 rounded-sm bg-white"
                                data-testid={`partner-card-${partner.id}`}
                            >
                                {partner.logo_url && (
                                    <img 
                                        src={partner.logo_url} 
                                        alt={partner.name}
                                        className="w-16 h-16 object-cover rounded-sm mb-4"
                                    />
                                )}
                                <h3 className="text-lg font-semibold text-[#0A0A0A] mb-2">{partner.name}</h3>
                                <p className="text-sm text-[#52525B] mb-3 line-clamp-2">{partner.description}</p>
                                {partner.category && (
                                    <span className="inline-block px-3 py-1 text-xs font-medium bg-[#FAFAFA] text-[#52525B] rounded-sm">
                                        {partner.category}
                                    </span>
                                )}
                            </div>
                        )) : (
                            <div className="col-span-3 text-center py-12 text-[#52525B]">
                                Partners will be displayed here
                            </div>
                        )}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-[#0A0A0A]">
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
            <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-[#E4E4E7]">
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                        <p className="font-black text-lg text-[#0A0A0A]">GuidedJourney</p>
                        <p className="text-sm text-[#52525B]">&copy; 2026 GuidedJourney. All rights reserved.</p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
