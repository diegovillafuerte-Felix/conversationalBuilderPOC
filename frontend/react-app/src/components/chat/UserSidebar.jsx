import { useState, useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';
import { chatApi } from '../../services/chatApi';

export default function UserSidebar() {
  const userId = useChatStore((state) => state.userId);
  const setUserId = useChatStore((state) => state.setUserId);
  const resetSession = useChatStore((state) => state.resetSession);

  const [users, setUsers] = useState([]);
  const [userContext, setUserContext] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUsers();
  }, []);

  useEffect(() => {
    if (userId) {
      loadUserContext(userId);
    }
  }, [userId]);

  const loadUsers = async () => {
    try {
      const data = await chatApi.getUsers();
      setUsers(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load users:', error);
      setLoading(false);
    }
  };

  const loadUserContext = async (id) => {
    try {
      const data = await chatApi.getUserContext(id);
      setUserContext(data);
    } catch (error) {
      console.error('Failed to load user context:', error);
      setUserContext(null);
    }
  };

  const handleUserChange = async (e) => {
    const newUserId = e.target.value;
    await resetSession();
    setUserId(newUserId);
  };

  if (loading) {
    return <div className="user-sidebar">Loading...</div>;
  }

  return (
    <div className="user-topbar">
      <div className="user-select-section">
        <label>Usuario:</label>
        <select value={userId} onChange={handleUserChange} className="user-select">
          {users.map((user) => (
            <option key={user.user_id} value={user.user_id}>
              {user.name}
            </option>
          ))}
        </select>
      </div>

      {userContext && (
        <div className="user-context-horizontal">
          <div className="context-item">
            <span className="context-label">Nombre:</span>
            <span className="context-value">{userContext.profile?.name || 'Unknown'}</span>
          </div>

          {userContext.profile?.language && (
            <div className="context-item">
              <span className="context-label">Idioma:</span>
              <span className="context-value">
                {userContext.profile.language === 'es' ? 'Español' : 'English'}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
