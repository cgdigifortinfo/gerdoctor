import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

// Helper to format API errors
export function formatApiError(error) {
    const detail = error.response?.data?.detail;
    if (detail == null) return "Something went wrong. Please try again.";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
        return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
    if (detail && typeof detail.msg === "string") return detail.msg;
    return String(detail);
}

// Create axios instance with credentials
const api = axios.create({
    baseURL: API,
    withCredentials: true,
});

// Auth APIs
export const authAPI = {
    login: (email, password) => api.post('/auth/login', { email, password }),
    register: (email, password, name) => api.post('/auth/register', { email, password, name }),
    logout: () => api.post('/auth/logout'),
    me: () => api.get('/auth/me'),
    forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
    resetPassword: (token, new_password) => api.post('/auth/reset-password', { token, new_password }),
};

// Profile APIs
export const profileAPI = {
    get: () => api.get('/profile'),
    update: (data) => api.put('/profile', data),
};

// Steps APIs
export const stepsAPI = {
    getAll: () => api.get('/steps'),
    getProgress: () => api.get('/steps/progress'),
    updateProgress: (step_id, status, data) => api.put('/steps/progress', { step_id, status, data }),
};

// Partners APIs
export const partnersAPI = {
    getAll: () => api.get('/partners'),
    getOne: (id) => api.get(`/partners/${id}`),
    submit: (partner_id, data) => api.post('/partners/submit', { partner_id, data }),
};

// Files APIs
export const filesAPI = {
    upload: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/files/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
    getUrl: (fileId) => `${API}/files/${fileId}`,
};

// CMS APIs
export const cmsAPI = {
    get: (section) => api.get(`/cms/${section}`),
    update: (section, content) => api.put(`/cms/${section}`, { section, content }),
};

// Admin APIs
export const adminAPI = {
    // Users
    getUsers: () => api.get('/admin/users'),
    getUser: (id) => api.get(`/admin/users/${id}`),
    searchUsers: (q, role) => api.get(`/admin/users/search?q=${encodeURIComponent(q || '')}&role=${encodeURIComponent(role || '')}`),
    updateUserProgress: (userId, step_id, status, data) => 
        api.put(`/admin/users/${userId}/progress`, { step_id, status, data }),
    updateUserRole: (userId, role) => api.put(`/admin/users/${userId}/role?role=${role}`),
    bulkUpdateRole: (user_ids, role) => api.put('/admin/users/bulk-role', { user_ids, role }),
    exportUsersCsv: () => api.get('/admin/export/users', { responseType: 'blob' }),
    
    // Steps
    getSteps: () => api.get('/admin/steps'),
    createStep: (data) => api.post('/admin/steps', data),
    updateStep: (id, data) => api.put(`/admin/steps/${id}`, data),
    deleteStep: (id) => api.delete(`/admin/steps/${id}`),
    reorderSteps: (step_ids) => api.put('/admin/steps/reorder', { step_ids }),
    
    // Partners
    getPartners: () => api.get('/admin/partners'),
    createPartner: (data) => api.post('/admin/partners', data),
    updatePartner: (id, data) => api.put(`/admin/partners/${id}`, data),
    deletePartner: (id) => api.delete(`/admin/partners/${id}`),
    linkPartnerUser: (partnerId, userId) => api.put(`/admin/partners/${partnerId}/link-user?user_id=${userId}`),
    unlinkPartnerUser: (partnerId) => api.put(`/admin/partners/${partnerId}/unlink-user`),
    
    // Analytics
    getAnalytics: () => api.get('/admin/analytics'),
    
    // Audit Log
    getAuditLog: (limit = 100, skip = 0, action = '', dateFrom = '', dateTo = '') => {
        const params = new URLSearchParams({ limit, skip });
        if (action) params.append('action', action);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        return api.get(`/admin/audit-log?${params.toString()}`);
    },
    
    // CMS
    getCmsContent: (section) => api.get(`/cms/${section}`),
    updateCmsContent: (section, content) => api.put(`/cms/${section}`, { section, content }),
};

// Notification Preferences APIs
export const notificationAPI = {
    getPreferences: () => api.get('/notifications/preferences'),
    updatePreferences: (prefs) => api.put('/notifications/preferences', prefs),
};

// Partner Dashboard APIs
export const partnerDashboardAPI = {
    getSubmissions: () => api.get('/partner/submissions'),
    getProfile: () => api.get('/partner/profile'),
    updateProfile: (data) => api.put('/partner/profile', data),
};

export default api;
