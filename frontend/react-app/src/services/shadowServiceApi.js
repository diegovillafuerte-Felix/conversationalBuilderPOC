const API_BASE = '/api/admin';

async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const shadowServiceApi = {
  // Shadow Service Config
  getConfig: () => apiRequest('/shadow-service'),
  updateConfig: (data) => apiRequest('/shadow-service', { method: 'PUT', body: JSON.stringify(data) }),

  // Subagents
  getSubagent: (id) => apiRequest(`/shadow-service/subagents/${id}`),
  updateSubagent: (id, data) => apiRequest(`/shadow-service/subagents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  createSubagent: (data) => apiRequest('/shadow-service/subagents', { method: 'POST', body: JSON.stringify(data) }),
  deleteSubagent: (id) => apiRequest(`/shadow-service/subagents/${id}`, { method: 'DELETE' }),
};
