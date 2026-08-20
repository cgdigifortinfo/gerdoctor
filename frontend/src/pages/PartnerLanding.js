import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Buildings, CheckCircle, ShieldCheck, UsersThree } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Logo } from '../components/Logo';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { formatApiError, partnerRegistrationAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

export default function PartnerLanding() {
    const navigate = useNavigate();
    const { user, loading, checkAuth } = useAuth();
    const [config, setConfig] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({ company_name: '', contact_name: '', email: '', password: '', website: '', description: '', country: 'DE' });

    useEffect(() => { partnerRegistrationAPI.config().then(r => setConfig(r.data)).catch(() => setConfig({ stripe: { configured: false } })); }, []);
    useEffect(() => {
        if (!loading && user) {
            const partnerPaid = ['paid', 'active', 'trialing'].includes(user.partner_billing_status);
            navigate(user.role === 'admin' ? '/admin' : user.role === 'partner' ? (user.partner_payment_required && !partnerPaid ? '/partner-payment' : '/partner-dashboard') : '/dashboard');
        }
    }, [loading, user, navigate]);

    const submit = async (event) => {
        event.preventDefault();
        setSaving(true);
        try {
            await partnerRegistrationAPI.register(form);
            await checkAuth();
            toast.success('Registrierung erfolgreich. Ihr Partnerprofil wartet auf die Survey-Zuordnung.');
            navigate('/partner-payment');
        } catch (error) { toast.error(formatApiError(error)); }
        finally { setSaving(false); }
    };

    return <div className="min-h-screen bg-background text-foreground">
        <header className="border-b border-border bg-card/90 sticky top-0 z-20">
            <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                <Logo /><nav className="flex items-center gap-3"><Link to="/aerzte" className="text-sm hover:text-[var(--brand-primary)]">Ärzte</Link><Link to="/pflege" className="text-sm hover:text-[var(--brand-primary)]">Pflege</Link><Link to="/login"><Button variant="outline">Einloggen</Button></Link><ThemeLangToggle /></nav>
            </div>
        </header>
        <main>
            <section className="max-w-7xl mx-auto px-6 py-20 grid lg:grid-cols-2 gap-14 items-start">
                <div className="pt-8">
                    <p className="uppercase tracking-[.22em] text-sm font-semibold text-[var(--brand-primary)]">Partnernetzwerk</p>
                    <h1 className="text-4xl md:text-6xl font-black leading-tight mt-4">Werden Sie Partner für internationale Fachkräfte.</h1>
                    <p className="text-lg text-muted-foreground mt-6 max-w-xl">Registrieren Sie Ihr Unternehmen, verwalten Sie Leads und Abrechnung zentral und werden Sie nach Prüfung einem oder mehreren Surveys zugeordnet.</p>
                    <div className="grid sm:grid-cols-3 gap-4 mt-10">
                        {[['Registrieren', Buildings], ['Freischalten', ShieldCheck], ['Kandidaten begleiten', UsersThree]].map(([label, Icon]) => <div key={label} className="border border-border bg-card rounded-lg p-4"><Icon size={28} className="text-[var(--brand-primary)]"/><p className="font-semibold mt-3">{label}</p></div>)}
                    </div>
                    <div className="mt-8 flex gap-2 text-sm text-muted-foreground"><CheckCircle size={20} className="text-emerald-600 shrink-0"/>Die Registrierung ist auch möglich, wenn Stripe noch nicht eingerichtet wurde. Die Abrechnungsfunktionen werden dann später freigeschaltet.</div>
                </div>
                <form onSubmit={submit} className="bg-card border border-border rounded-xl shadow-sm p-7 space-y-5" data-testid="partner-registration-form">
                    <div><h2 className="text-2xl font-bold">Als Partner registrieren</h2><p className="text-sm text-muted-foreground mt-1">Nach der Registrierung prüft ein Administrator die Zuordnung.</p></div>
                    <div className="grid sm:grid-cols-2 gap-4">
                        <div><Label htmlFor="partner-company">Unternehmen *</Label><Input id="partner-company" required minLength={2} value={form.company_name} onChange={e => setForm({...form, company_name:e.target.value})}/></div>
                        <div><Label htmlFor="partner-contact">Ansprechpartner *</Label><Input id="partner-contact" required minLength={2} value={form.contact_name} onChange={e => setForm({...form, contact_name:e.target.value})}/></div>
                        <div><Label htmlFor="partner-email">E-Mail *</Label><Input id="partner-email" required type="email" value={form.email} onChange={e => setForm({...form, email:e.target.value})}/></div>
                        <div><Label htmlFor="partner-password">Passwort *</Label><Input id="partner-password" required minLength={8} type="password" value={form.password} onChange={e => setForm({...form, password:e.target.value})}/></div>
                    </div>
                    <div><Label>Website</Label><Input type="url" placeholder="https://" value={form.website} onChange={e => setForm({...form, website:e.target.value})}/></div>
                    <div><Label>Leistungen</Label><Textarea rows={4} value={form.description} onChange={e => setForm({...form, description:e.target.value})}/></div>
                    <Button className="w-full bg-[var(--brand-primary)] text-white" disabled={saving}>{saving ? 'Registrierung läuft…' : <>Partnerkonto erstellen <ArrowRight className="ml-2"/></>}</Button>
                    {config && <p className="text-xs text-center text-muted-foreground" data-testid="stripe-availability">Stripe: {config.stripe?.configured ? (config.stripe.sandbox_mode ? 'Sandbox verfügbar' : 'Live-Verbindung verfügbar') : 'noch nicht konfiguriert – Registrierung trotzdem möglich'}</p>}
                </form>
            </section>
        </main>
    </div>;
}
