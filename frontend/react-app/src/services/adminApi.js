const API_BASE = '/api/admin';
const CHAT_API_BASE = '/api/chat';

// Dev token for local development - in production, this should come from auth
const DEV_TOKEN = 'dev-token';

async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const { method = 'GET', body } = options;
  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${DEV_TOKEN}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const adminApi = {
  getAgents: () => apiRequest('/agents'),
  getAgent: (id) => apiRequest(`/agents/${id}`),
  reloadConfig: () => apiRequest('/reload-config', { method: 'POST' }),
};

async function chatApiRequest(endpoint) {
  const response = await fetch(`${CHAT_API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const conversationApi = {
  listConversations: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.set(key, String(value));
      }
    });
    const suffix = query.toString() ? `?${query}` : '';
    return chatApiRequest(`/conversations${suffix}`);
  },
  getConversation: (id) => chatApiRequest(`/conversations/${id}`),
  getConversationEvents: (id) => chatApiRequest(`/conversations/${id}/events`),
};
