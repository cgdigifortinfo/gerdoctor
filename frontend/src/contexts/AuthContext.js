import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { setAuthToken } from '../lib/api';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [impersonating, setImpersonating] = useState(false);
    const tokenRef = useRef(null);
    const adminTokenRef = useRef(null);
    const adminUserRef = useRef(null);

    const checkAuth = useCallback(async () => {
        try {
            const headers = tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {};
            const response = await axios.get(`${API}/auth/me`, { withCredentials: true, headers });
            setUser(response.data);
        } catch (err) {
            if (err.response?.status === 401) {
                try {
                    await axios.post(`${API}/auth/refresh`, {}, { withCredentials: true });
                    const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
                    setUser(response.data);
                    return;
                } catch {}
            }
            setUser(false);
            tokenRef.current = null;
            setAuthToken(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // Restore impersonation state from sessionStorage
        const savedAdmin = sessionStorage.getItem('admin_impersonate');
        if (savedAdmin) {
            try {
                const parsed = JSON.parse(savedAdmin);
                adminTokenRef.current = parsed.token;
                adminUserRef.current = parsed.user;
                // Restore impersonated token
                const savedImpToken = sessionStorage.getItem('impersonate_token');
                if (savedImpToken) {
                    tokenRef.current = savedImpToken;
                    setAuthToken(savedImpToken);
                }
                setImpersonating(true);
            } catch {}
        }
        checkAuth();
    }, [checkAuth]);

    const login = async (email, password) => {
        const response = await axios.post(`${API}/auth/login`, { email, password }, { withCredentials: true });
        if (response.data.access_token) {
            tokenRef.current = response.data.access_token;
            setAuthToken(response.data.access_token);
        }
        setUser(response.data);
        return response.data;
    };

    const register = async (email, password, name) => {
        const response = await axios.post(`${API}/auth/register`, { email, password, name }, { withCredentials: true });
        if (response.data.access_token) {
            tokenRef.current = response.data.access_token;
            setAuthToken(response.data.access_token);
        }
        setUser(response.data);
        return response.data;
    };

    const logout = async () => {
        try {
            await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
        } catch {}
        tokenRef.current = null;
        adminTokenRef.current = null;
        adminUserRef.current = null;
        setAuthToken(null);
        sessionStorage.removeItem('admin_impersonate');
        sessionStorage.removeItem('impersonate_token');
        setImpersonating(false);
        setUser(false);
    };

    const impersonate = async (targetToken, targetUser) => {
        // Save current admin token
        adminTokenRef.current = tokenRef.current;
        adminUserRef.current = user;
        sessionStorage.setItem('admin_impersonate', JSON.stringify({ token: tokenRef.current, user }));
        sessionStorage.setItem('impersonate_token', targetToken);
        // Switch to target user
        tokenRef.current = targetToken;
        setAuthToken(targetToken);
        setUser(targetUser);
        setImpersonating(true);
    };

    const stopImpersonation = () => {
        // Restore admin token
        tokenRef.current = adminTokenRef.current;
        setAuthToken(adminTokenRef.current);
        setUser(adminUserRef.current);
        adminTokenRef.current = null;
        adminUserRef.current = null;
        sessionStorage.removeItem('admin_impersonate');
        sessionStorage.removeItem('impersonate_token');
        setImpersonating(false);
    };

    const refreshToken = async () => {
        try {
            await axios.post(`${API}/auth/refresh`, {}, { withCredentials: true });
            await checkAuth();
        } catch {
            setUser(false);
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, refreshToken, checkAuth, impersonate, stopImpersonation, impersonating }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
}
