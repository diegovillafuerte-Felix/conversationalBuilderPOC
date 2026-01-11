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

export const adminApi = {
  // Agents
  getAgents: () => apiRequest('/agents'),
  getAgent: (id) => apiRequest(`/agents/${id}`),
  createAgent: (data) => apiRequest('/agents', { method: 'POST', body: JSON.stringify(data) }),
  updateAgent: (id, data) => apiRequest(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAgent: (id) => apiRequest(`/agents/${id}`, { method: 'DELETE' }),
  cloneAgent: (id) => apiRequest(`/agents/${id}/clone`, { method: 'POST' }),

  // Tools
  createTool: (agentId, data) => apiRequest(`/agents/${agentId}/tools`, { method: 'POST', body: JSON.stringify(data) }),
  updateTool: (id, data) => apiRequest(`/tools/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTool: (id) => apiRequest(`/tools/${id}`, { method: 'DELETE' }),

  // Subflows
  createSubflow: (agentId, data) => apiRequest(`/agents/${agentId}/subflows`, { method: 'POST', body: JSON.stringify(data) }),
  updateSubflow: (id, data) => apiRequest(`/subflows/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSubflow: (id) => apiRequest(`/subflows/${id}`, { method: 'DELETE' }),

  // States
  createState: (subflowId, data) => apiRequest(`/subflows/${subflowId}/states`, { method: 'POST', body: JSON.stringify(data) }),
  updateState: (id, data) => apiRequest(`/states/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteState: (id) => apiRequest(`/states/${id}`, { method: 'DELETE' }),

  // Templates
  createTemplate: (agentId, data) => apiRequest(`/agents/${agentId}/templates`, { method: 'POST', body: JSON.stringify(data) }),
  updateTemplate: (id, data) => apiRequest(`/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTemplate: (id) => apiRequest(`/templates/${id}`, { method: 'DELETE' }),
};
