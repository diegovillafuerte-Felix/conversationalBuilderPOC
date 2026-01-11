import { useChatStore } from '../../store/chatStore';

export default function SessionInfo() {
  const sessionId = useChatStore((state) => state.sessionId);
  const resetSession = useChatStore((state) => state.resetSession);

  const displaySessionId = sessionId
    ? `Sesión: ${sessionId.substring(0, 8)}...`
    : 'Nueva sesión';

  return (
    <div className="session-info">
      <span>{displaySessionId}</span>
      <button className="reset-btn" onClick={resetSession}>
        Nueva conversación
      </button>
    </div>
  );
}
