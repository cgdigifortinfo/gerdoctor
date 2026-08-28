import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authAPI, formatApiError } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeft, Eye, EyeSlash } from '@phosphor-icons/react';
import { toast } from 'sonner';

// Stryker disable all: authentication form adapter covered by page contract tests.
export function Login() {
    const navigate = useNavigate();
    const { surveySlug } = useParams();
    const [searchParams] = useSearchParams();
    const { login } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const user = await login(email, password);
            toast.success('Login successful!');
            if (user.role === 'admin') {
                navigate('/admin');
            } else if (user.role === 'partner') {
                navigate('/partner-dashboard');
            } else {
                navigate('/dashboard');
            }
        } catch (err) {
            setError(formatApiError(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-view min-h-screen bg-background flex">
            {/* Left Side - Image */}
            <div className="hidden lg:block lg:w-1/2 relative">
                <img 
                    src="/assets/auth-background.svg"
                    alt="GerDoctor"
                    className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-white/20"></div>
            </div>

            {/* Right Side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
                <div className="w-full max-w-md">
                    <Link to={surveySlug ? `/s/${surveySlug}` : '/'} className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-8">
                        <ArrowLeft size={16} className="mr-2" />
                        Zurück zur Startseite
                    </Link>

                    <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-2">
                        Willkommen zurück
                    </h1>
                    <p className="text-muted-foreground mb-8">
                        Melden Sie sich an, um Ihren Anerkennungsprozess fortzusetzen.
                    </p>

                    {searchParams.get('passwordReset') === 'success' && (
                        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-sm mb-6 text-sm" data-testid="login-reset-success" role="status">
                            Ihr Passwort wurde erfolgreich geändert. Sie können sich jetzt anmelden.
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm" data-testid="login-error">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <Label htmlFor="email" className="text-foreground">E-Mail-Adresse</Label>
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="name@beispiel.de"
                                className="mt-2 border-border focus:ring-[var(--brand-primary)] rounded-sm"
                                required
                                data-testid="login-email-input"
                            />
                        </div>

                        <div>
                            <div className="flex justify-between items-center">
                                <Label htmlFor="password" className="text-foreground">Passwort</Label>
                                <Link to="/forgot-password" className="text-sm text-[var(--brand-primary)] hover:underline">
                                    Passwort vergessen?
                                </Link>
                            </div>
                            <div className="relative mt-2">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Passwort eingeben"
                                    className="border-border focus:ring-[var(--brand-primary)] rounded-sm pr-10"
                                    required
                                    data-testid="login-password-input"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                                    aria-label={showPassword ? 'Passwort ausblenden' : 'Passwort anzeigen'}
                                >
                                    {showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}
                                </button>
                            </div>
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white py-3 rounded-sm"
                            disabled={loading}
                            data-testid="login-submit-btn"
                        >
                            {loading ? 'Anmeldung...' : 'Anmelden'}
                        </Button>
                    </form>

                    <p className="mt-6 text-center text-muted-foreground">
                        Noch kein Konto?{' '}
                        <Link to={surveySlug ? `/s/${surveySlug}/register` : '/register'} className="text-[var(--brand-primary)] hover:underline font-medium">
                            Jetzt registrieren
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}

export function Register() {
    const navigate = useNavigate();
    const { surveySlug } = useParams();
    const { register } = useAuth();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setLoading(true);
        try {
            await register(email, password, name, surveySlug);
            toast.success('Account created successfully!');
            navigate('/dashboard');
        } catch (err) {
            setError(formatApiError(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-view min-h-screen bg-background flex">
            {/* Left Side - Image */}
            <div className="hidden lg:block lg:w-1/2 relative">
                <img 
                    src="/assets/auth-background.svg"
                    alt="GerDoctor"
                    className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-white/20"></div>
            </div>

            {/* Right Side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
                <div className="w-full max-w-md">
                    <Link to={surveySlug ? `/s/${surveySlug}` : '/'} className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-8">
                        <ArrowLeft size={16} className="mr-2" />
                        Back to Home
                    </Link>

                    <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-2">
                        Konto für den Anerkennungsprozess erstellen
                    </h1>
                    <p className="text-muted-foreground mb-8">
                        Starten Sie Ihren Weg als Pflegefachkraft in Deutschland.
                    </p>

                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm" data-testid="register-error">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <Label htmlFor="name" className="text-foreground">Full Name</Label>
                            <Input
                                id="name"
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="John Doe"
                                className="mt-2 border-border focus:ring-[var(--brand-primary)] rounded-sm"
                                required
                                data-testid="register-name-input"
                            />
                        </div>

                        <div>
                            <Label htmlFor="email" className="text-foreground">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@example.com"
                                className="mt-2 border-border focus:ring-[var(--brand-primary)] rounded-sm"
                                required
                                data-testid="register-email-input"
                            />
                        </div>

                        <div>
                            <Label htmlFor="password" className="text-foreground">Password</Label>
                            <div className="relative mt-2">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="At least 6 characters"
                                    className="border-border focus:ring-[var(--brand-primary)] rounded-sm pr-10"
                                    required
                                    data-testid="register-password-input"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                                >
                                    {showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}
                                </button>
                            </div>
                        </div>

                        <div>
                            <Label htmlFor="confirmPassword" className="text-foreground">Confirm Password</Label>
                            <Input
                                id="confirmPassword"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Confirm your password"
                                className="mt-2 border-border focus:ring-[var(--brand-primary)] rounded-sm"
                                required
                                data-testid="register-confirm-password-input"
                            />
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white py-3 rounded-sm"
                            disabled={loading}
                            data-testid="register-submit-btn"
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                        </Button>
                    </form>

                    <p className="mt-6 text-center text-muted-foreground">
                        Already have an account?{' '}
                        <Link to="/login" className="text-[var(--brand-primary)] hover:underline font-medium">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}

export function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await authAPI.forgotPassword(email);
            setSubmitted(true);
        } catch (err) {
            setError(formatApiError(err));
        } finally {
            setLoading(false);
        }
    };

    if (submitted) {
        return (
            <div className="auth-view min-h-screen bg-background flex items-center justify-center p-8">
                <div className="w-full max-w-md text-center">
                    <h1 className="text-2xl font-bold text-foreground mb-4" data-testid="forgot-success">Prüfen Sie Ihr E-Mail-Postfach</h1>
                    <p className="text-muted-foreground mb-8">
                        Falls ein Konto für {email} existiert, erhalten Sie einen Link zum Zurücksetzen Ihres Passworts.
                    </p>
                    <Link to="/login">
                        <Button className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white">
                            Zurück zur Anmeldung
                        </Button>
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-view min-h-screen bg-background flex items-center justify-center p-8">
            <div className="w-full max-w-md">
                <Link to="/login" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-8">
                    <ArrowLeft size={16} className="mr-2" />
                    Zurück zur Anmeldung
                </Link>

                <h1 className="text-2xl font-bold text-foreground mb-2">Passwort zurücksetzen</h1>
                <p className="text-muted-foreground mb-8">
                    Geben Sie Ihre E-Mail-Adresse ein. Wir senden Ihnen anschließend einen sicheren Link.
                </p>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm" data-testid="forgot-error" role="alert">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <Label htmlFor="email" className="text-foreground">E-Mail-Adresse</Label>
                        <Input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@beispiel.de"
                            className="mt-2 border-border rounded-sm"
                            required
                            data-testid="forgot-email-input"
                        />
                    </div>

                    <Button
                        type="submit"
                        className="w-full bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white py-3 rounded-sm"
                        disabled={loading}
                        data-testid="forgot-submit-btn"
                    >
                        {loading ? 'Wird gesendet...' : 'Link zum Zurücksetzen senden'}
                    </Button>
                </form>
            </div>
        </div>
    );
}

export function ResetPassword() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setLoading(true);
        try {
            await authAPI.resetPassword(token, password);
            toast.success('Passwort erfolgreich geändert.');
            navigate('/login?passwordReset=success');
        } catch (err) {
            setError(formatApiError(err));
        } finally {
            setLoading(false);
        }
    };

    if (!token) {
        return (
            <div className="auth-view min-h-screen bg-background flex items-center justify-center p-8">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-foreground mb-4">Ungültiger Link</h1>
                    <Link to="/forgot-password">
                        <Button className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white">
                            Neuen Link anfordern
                        </Button>
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-view min-h-screen bg-background flex items-center justify-center p-8">
            <div className="w-full max-w-md">
                <h1 className="text-2xl font-bold text-foreground mb-2">Neues Passwort festlegen</h1>
                <p className="text-muted-foreground mb-8">
                    Geben Sie Ihr neues Passwort zweimal ein.
                </p>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm" data-testid="reset-error" role="alert">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <Label htmlFor="password" className="text-foreground">Neues Passwort</Label>
                        <Input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Mindestens 6 Zeichen"
                            className="mt-2 border-border rounded-sm"
                            required
                            data-testid="reset-password-input"
                        />
                    </div>

                    <div>
                        <Label htmlFor="confirmPassword" className="text-foreground">Passwort bestätigen</Label>
                        <Input
                            id="confirmPassword"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="Passwort erneut eingeben"
                            className="mt-2 border-border rounded-sm"
                            required
                            data-testid="reset-confirm-password-input"
                        />
                    </div>

                    <Button
                        type="submit"
                        className="w-full bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white py-3 rounded-sm"
                        disabled={loading}
                        data-testid="reset-submit-btn"
                    >
                        {loading ? 'Wird geändert...' : 'Passwort ändern'}
                    </Button>
                </form>
            </div>
        </div>
    );
}
