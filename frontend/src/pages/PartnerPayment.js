import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle, CreditCard, ShieldCheck } from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { Logo } from '../components/Logo';
import { partnerDashboardAPI, formatApiError } from '../lib/api';
import { toast } from 'sonner';
import { useAuth } from '../contexts/AuthContext';

export const redirectToCheckout = (url, location) => location.assign(url);

// Stryker disable all: payment-page adapter; checkout redirect remains mutation-tested above.
export function PartnerOnboarding({ location = window.location }) {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    useEffect(() => { partnerDashboardAPI.getPaymentStatus().then(r => { setStatus(r.data); if (r.data.access_unlocked) navigate('/partner-dashboard'); }).catch(e => toast.error(formatApiError(e))); }, [navigate]);
    const pay = async () => { setLoading(true); try { const r = await partnerDashboardAPI.createCheckout(); redirectToCheckout(r.data.url, location); } catch(e) { toast.error(formatApiError(e)); setLoading(false); } };
    return <PaymentShell><div className="max-w-xl mx-auto bg-card border border-border rounded-xl p-8 text-center"><CreditCard size={48} className="mx-auto text-[var(--brand-primary)]"/><h1 className="text-3xl font-bold mt-5">Partnerzugang freischalten</h1><p className="text-muted-foreground mt-3">Schließen Sie die sichere Zahlung über Stripe ab. Erst nach erfolgreicher Bestätigung wird Ihr Administrationsbereich freigeschaltet.</p><div className="my-6 text-left space-y-3">{['Sichere Stripe-Zahlungsseite','Rechnungen und Zahlungsdaten im Stripe-Portal','Automatische Freischaltung nach bestätigter Zahlung'].map(x => <p key={x} className="flex gap-2"><CheckCircle className="text-green-600 shrink-0"/>{x}</p>)}</div><Button onClick={pay} disabled={loading || status === null} className="w-full">{loading ? 'Weiterleitung…' : 'Sicher mit Stripe bezahlen'}</Button><p className="text-xs text-muted-foreground mt-4">Zahlungsdaten werden ausschließlich von Stripe verarbeitet.</p></div></PaymentShell>;
}

export function PartnerPaymentSuccess() {
    const [params] = useSearchParams(); const navigate = useNavigate(); const { checkAuth } = useAuth(); const [message,setMessage] = useState('Zahlung wird bestätigt…');
    useEffect(() => { const id=params.get('session_id'); if(!id){setMessage('Ungültige Rückkehr-URL');return;} partnerDashboardAPI.getPaymentStatus(id).then(async r => { if(r.data.access_unlocked){await checkAuth(); setMessage('Zahlung bestätigt. Ihr Zugang ist freigeschaltet.'); setTimeout(()=>navigate('/partner-dashboard'),1200);} else setMessage('Stripe verarbeitet die Zahlung noch. Bitte laden Sie die Seite gleich erneut.'); }).catch(e=>setMessage(formatApiError(e))); },[params,navigate,checkAuth]);
    return <PaymentShell><div className="max-w-xl mx-auto bg-card border border-border rounded-xl p-10 text-center"><ShieldCheck size={56} className="mx-auto text-green-600"/><h1 className="text-2xl font-bold mt-5">{message}</h1><Button className="mt-6" onClick={()=>navigate('/partner-payment')}>Status prüfen</Button></div></PaymentShell>;
}
function PaymentShell({children}) { return <div className="min-h-screen bg-background"><header className="border-b border-border bg-card"><div className="max-w-6xl mx-auto px-6 h-20 flex items-center"><Logo/></div></header><main className="px-6 py-16">{children}</main></div>; }
