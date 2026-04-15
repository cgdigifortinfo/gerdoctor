import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null); // null = checking, false = not auth, object = auth
    const [loading, setLoading] = useState(true);
    const tokenRef = useRef(null);

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
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    const login = async (email, password) => {
        const response = await axios.post(`${API}/auth/login`, { email, password }, { withCredentials: true });
        if (response.data.access_token) tokenRef.current = response.data.access_token;
        setUser(response.data);
        return response.data;
    };

    const register = async (email, password, name) => {
        const response = await axios.post(`${API}/auth/register`, { email, password, name }, { withCredentials: true });
        if (response.data.access_token) tokenRef.current = response.data.access_token;
        setUser(response.data);
        return response.data;
    };

    const logout = async () => {
        try {
            await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
        } catch {}
        tokenRef.current = null;
        setUser(false);
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
        <AuthContext.Provider value={{ user, loading, login, register, logout, refreshToken, checkAuth }}>
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
