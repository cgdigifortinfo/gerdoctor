import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authAPI, formatApiError } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeft, Eye, EyeSlash } from '@phosphor-icons/react';
import { toast } from 'sonner';

export function Login() {
    const navigate = useNavigate();
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
        <div className="min-h-screen bg-[#FAFAFA] flex">
            {/* Left Side - Image */}
            <div className="hidden lg:block lg:w-1/2 relative">
                <img 
                    src="https://images.unsplash.com/photo-1747727350761-a607eae63dc0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzN8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMG1pbmltYWwlMjBhcmNoaXRlY3R1cmV8ZW58MHx8fHwxNzc2MTUyMzY3fDA&ixlib=rb-4.1.0&q=85"
                    alt="Abstract architecture"
                    className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-white/20"></div>
            </div>

            {/* Right Side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
                <div className="w-full max-w-md">
                    <Link to="/" className="inline-flex items-center text-sm text-[#52525B] hover:text-[#0A0A0A] mb-8">
                        <ArrowLeft size={16} className="mr-2" />
                        Back to Home
                    </Link>

                    <h1 className="text-2xl sm:text-3xl tracking-tight font-bold text-[#0A0A0A] mb-2">
                        Welcome back
                    </h1>
                    <p className="text-[#52525B] mb-8">
                        Sign in to continue your journey
                    </p>

                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm" data-testid="login-error">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <Label htmlFor="email" className="text-[#0A0A0A]">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@example.com"
                                className="mt-2 border-[#E4E4E7] focus:ring-[#114f55] rounded-sm"
                                required
                                data-testid="login-email-input"
                            />
                        </div>

                        <div>
                            <div className="flex justify-between items-center">
                                <Label htmlFor="password" className="text-[#0A0A0A]">Password</Label>
                                <Link to="/forgot-password" className="text-sm text-[#114f55] hover:underline">
                                    Forgot password?
                                </Link>
                            </div>
                            <div className="relative mt-2">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Enter your password"
                                    className="border-[#E4E4E7] focus:ring-[#114f55] rounded-sm pr-10"
                                    required
                                    data-testid="login-password-input"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#52525B]"
                                >
                                    {showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}
                                </button>
                            </div>
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-[#114f55] hover:bg-[#0d3d42] text-white py-3 rounded-sm"
                            disabled={loading}
                            data-testid="login-submit-btn"
                        >
                            {loading ? 'Signing in...' : 'Sign In'}
                        </Button>
                    </form>

                    <p className="mt-6 text-center text-[#52525B]">
                        Don't have an account?{' '}
                        <Link to="/register" className="text-[#114f55] hover:underline font-medium">
                            Create one
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}

export function Register() {
    const navigate = useNavigate();
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
            await register(email, password, name);
            toast.success('Account created successfully!');
            navigate('/dashboard');
        } catch (err) {
            setError(formatApiError(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#FAFAFA] flex">
            {/* Left Side - Image */}
            <div className="hidden lg:block lg:w-1/2 relative">
                <img 
                    src="https://images.unsplash.com/photo-1747727350761-a607eae63dc0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzN8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMG1pbmltYWwlMjBhcmNoaXRlY3R1cmV8ZW58MHx8fHwxNzc2MTUyMzY3fDA&ixlib=rb-4.1.0&q=85"
                    alt="Abstract architecture"
                    className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-white/20"></div>
            </div>

            {/* Right Side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
                <div className="w-full max-w-md">
                    <Link to="/" className="inline-flex items-center text-sm text-[#52525B] hover:text-[#0A0A0A] mb-8">
                        <ArrowLeft size={16} className="mr-2" />
                        Back to Home
                    </Link>

                    <h1 className="text-2xl sm:text-3xl tracking-tight font-bold text-[#0A0A0A] mb-2">
                        Create your account
                    </h1>
                    <p className="text-[#52525B] mb-8">
                        Start your journey with us today
                    </p>

                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm" data-testid="register-error">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <Label htmlFor="name" className="text-[#0A0A0A]">Full Name</Label>
                            <Input
                                id="name"
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="John Doe"
                                className="mt-2 border-[#E4E4E7] focus:ring-[#114f55] rounded-sm"
                                required
                                data-testid="register-name-input"
                            />
                        </div>

                        <div>
                            <Label htmlFor="email" className="text-[#0A0A0A]">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@example.com"
                                className="mt-2 border-[#E4E4E7] focus:ring-[#114f55] rounded-sm"
                                required
                                data-testid="register-email-input"
                            />
                        </div>

                        <div>
                            <Label htmlFor="password" className="text-[#0A0A0A]">Password</Label>
                            <div className="relative mt-2">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="At least 6 characters"
                                    className="border-[#E4E4E7] focus:ring-[#114f55] rounded-sm pr-10"
                                    required
                                    data-testid="register-password-input"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#52525B]"
                                >
                                    {showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}
                                </button>
                            </div>
                        </div>

                        <div>
                            <Label htmlFor="confirmPassword" className="text-[#0A0A0A]">Confirm Password</Label>
                            <Input
                                id="confirmPassword"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Confirm your password"
                                className="mt-2 border-[#E4E4E7] focus:ring-[#114f55] rounded-sm"
                                required
                                data-testid="register-confirm-password-input"
                            />
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-[#114f55] hover:bg-[#0d3d42] text-white py-3 rounded-sm"
                            disabled={loading}
                            data-testid="register-submit-btn"
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                        </Button>
                    </form>

                    <p className="mt-6 text-center text-[#52525B]">
                        Already have an account?{' '}
                        <Link to="/login" className="text-[#114f55] hover:underline font-medium">
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
            <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-8">
                <div className="w-full max-w-md text-center">
                    <h1 className="text-2xl font-bold text-[#0A0A0A] mb-4">Check your email</h1>
                    <p className="text-[#52525B] mb-8">
                        If an account exists for {email}, you'll receive a password reset link.
                    </p>
                    <Link to="/login">
                        <Button className="bg-[#114f55] hover:bg-[#0d3d42] text-white">
                            Return to Login
                        </Button>
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-8">
            <div className="w-full max-w-md">
                <Link to="/login" className="inline-flex items-center text-sm text-[#52525B] hover:text-[#0A0A0A] mb-8">
                    <ArrowLeft size={16} className="mr-2" />
                    Back to Login
                </Link>

                <h1 className="text-2xl font-bold text-[#0A0A0A] mb-2">Reset your password</h1>
                <p className="text-[#52525B] mb-8">
                    Enter your email and we'll send you a reset link.
                </p>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <Label htmlFor="email" className="text-[#0A0A0A]">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@example.com"
                            className="mt-2 border-[#E4E4E7] rounded-sm"
                            required
                            data-testid="forgot-email-input"
                        />
                    </div>

                    <Button
                        type="submit"
                        className="w-full bg-[#114f55] hover:bg-[#0d3d42] text-white py-3 rounded-sm"
                        disabled={loading}
                        data-testid="forgot-submit-btn"
                    >
                        {loading ? 'Sending...' : 'Send Reset Link'}
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
            toast.success('Password reset successful!');
            navigate('/login');
        } catch (err) {
            setError(formatApiError(err));
        } finally {
            setLoading(false);
        }
    };

    if (!token) {
        return (
            <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-8">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-[#0A0A0A] mb-4">Invalid Reset Link</h1>
                    <Link to="/forgot-password">
                        <Button className="bg-[#114f55] hover:bg-[#0d3d42] text-white">
                            Request New Link
                        </Button>
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-8">
            <div className="w-full max-w-md">
                <h1 className="text-2xl font-bold text-[#0A0A0A] mb-2">Set new password</h1>
                <p className="text-[#52525B] mb-8">
                    Enter your new password below.
                </p>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-sm mb-6 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <Label htmlFor="password" className="text-[#0A0A0A]">New Password</Label>
                        <Input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="At least 6 characters"
                            className="mt-2 border-[#E4E4E7] rounded-sm"
                            required
                            data-testid="reset-password-input"
                        />
                    </div>

                    <div>
                        <Label htmlFor="confirmPassword" className="text-[#0A0A0A]">Confirm Password</Label>
                        <Input
                            id="confirmPassword"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="Confirm your password"
                            className="mt-2 border-[#E4E4E7] rounded-sm"
                            required
                            data-testid="reset-confirm-password-input"
                        />
                    </div>

                    <Button
                        type="submit"
                        className="w-full bg-[#114f55] hover:bg-[#0d3d42] text-white py-3 rounded-sm"
                        disabled={loading}
                        data-testid="reset-submit-btn"
                    >
                        {loading ? 'Resetting...' : 'Reset Password'}
                    </Button>
                </form>
            </div>
        </div>
    );
}
