const configuredBackendUrl = (process.env.REACT_APP_BACKEND_URL || '')
    .trim()
    .replace(/\/+$/, '');

// An empty backend URL intentionally uses the current browser origin. In local
// development CRA forwards /api to API_PROXY_TARGET; in production FastAPI
// serves the frontend and API from the same origin.
export const API_BASE_URL = `${configuredBackendUrl}/api`;
