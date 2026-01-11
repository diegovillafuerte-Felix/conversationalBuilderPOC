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
    <div className="user-sidebar">
      <h3>Usuario</h3>
      <select value={userId} onChange={handleUserChange} className="user-select">
        {users.map((user) => (
          <option key={user.user_id} value={user.user_id}>
            {user.name}
          </option>
        ))}
      </select>

      {userContext && (
        <div className="user-context">
          <div className="context-section">
            <strong>{userContext.profile?.name || 'Unknown'}</strong>
            <p>Miembro desde: {userContext.profile?.memberSince || 'N/A'}</p>
          </div>

          {userContext.product_summaries?.wallet && (
            <div className="context-section">
              <div className="context-label">Cartera</div>
              <div className="context-value">
                ${userContext.product_summaries.wallet.currentBalance?.toFixed(2) || '0.00'}
              </div>
            </div>
          )}

          {userContext.product_summaries?.credit?.hasActiveCredit && (
            <div className="context-section">
              <div className="context-label">Crédito</div>
              <div className="context-value">
                ${userContext.product_summaries.credit.currentBalance?.toFixed(2) || '0.00'} / ${userContext.product_summaries.credit.creditLimit?.toFixed(2) || '0.00'}
              </div>
            </div>
          )}

          {userContext.product_summaries?.remittances && (
            <div className="context-section">
              <div className="context-label">Remesas</div>
              <div className="context-value">
                {userContext.product_summaries.remittances.lifetimeCount || 0} enviadas
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
