import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null); // null = checking, false = not auth, object = auth
    const [loading, setLoading] = useState(true);

    const checkAuth = useCallback(async () => {
        try {
            const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
            setUser(response.data);
        } catch (err) {
            // Try refreshing the token on 401
            if (err.response?.status === 401) {
                try {
                    await axios.post(`${API}/auth/refresh`, {}, { withCredentials: true });
                    const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
                    setUser(response.data);
                    return;
                } catch {
                    // Refresh also failed
                }
            }
            setUser(false);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    const login = async (email, password) => {
        const response = await axios.post(`${API}/auth/login`, { email, password }, { withCredentials: true });
        setUser(response.data);
        return response.data;
    };

    const register = async (email, password, name) => {
        const response = await axios.post(`${API}/auth/register`, { email, password, name }, { withCredentials: true });
        setUser(response.data);
        return response.data;
    };

    const logout = async () => {
        await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
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
