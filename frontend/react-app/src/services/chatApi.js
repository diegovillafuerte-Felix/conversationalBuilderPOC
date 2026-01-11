const API_URL = '/api/chat';

export const chatApi = {
  async sendMessage(userId, message, sessionId) {
    const response = await fetch(`${API_URL}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        message: message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  async endSession(sessionId) {
    const response = await fetch(`${API_URL}/session/${sessionId}/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  async getUsers() {
    const response = await fetch(`${API_URL}/users`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  async getUserContext(userId) {
    const response = await fetch(`${API_URL}/users/${userId}/context`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },
};
