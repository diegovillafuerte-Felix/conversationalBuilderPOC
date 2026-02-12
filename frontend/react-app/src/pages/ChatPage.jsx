import { useState } from 'react';
import ChatContainer from '../components/chat/ChatContainer';
import SessionInfo from '../components/chat/SessionInfo';
import UserSidebar from '../components/chat/UserSidebar';
import DebugPanel from '../components/chat/DebugPanel';
import EventTracePanel from '../components/chat/EventTracePanel';
import '../styles/chat.css';

export default function ChatPage() {
  const [showDebug, setShowDebug] = useState(true);

  return (
    <div className={`chat-page ${showDebug ? 'with-debug' : ''}`}>
      <UserSidebar />
      <div className="chat-layout">
        <div className="chat-main">
          <ChatContainer />
          <SessionInfo />
        </div>
        {showDebug && (
          <>
            <div className="debug-container">
              <DebugPanel />
            </div>
            <div className="trace-container">
              <EventTracePanel />
            </div>
          </>
        )}
      </div>
      <button
        className="toggle-debug-btn"
        onClick={() => setShowDebug(!showDebug)}
        title={showDebug ? 'Hide Debug Panel' : 'Show Debug Panel'}
      >
        {showDebug ? '🔍 Hide Debug' : '🔍 Show Debug'}
      </button>
    </div>
  );
}
