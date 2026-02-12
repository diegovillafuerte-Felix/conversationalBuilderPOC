import { useEffect, useState } from 'react';
import { useVisualizeStore } from '../../store/visualizeStore';

function formatTimestamp(value) {
  if (!value) return 'N/A';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function ConversationReview() {
  const conversations = useVisualizeStore((state) => state.conversations);
  const selectedConversation = useVisualizeStore((state) => state.selectedConversation);
  const conversationEvents = useVisualizeStore((state) => state.conversationEvents);
  const isConversationLoading = useVisualizeStore((state) => state.isConversationLoading);
  const loadConversations = useVisualizeStore((state) => state.loadConversations);
  const openConversation = useVisualizeStore((state) => state.openConversation);
  const clearConversationSelection = useVisualizeStore((state) => state.clearConversationSelection);

  const [search, setSearch] = useState('');

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleSearch = () => {
    loadConversations({ q: search.trim() || undefined });
    clearConversationSelection();
  };

  return (
    <div className="conversation-review">
      <div className="conversation-list-panel">
        <div className="conversation-toolbar">
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search conversation text..."
          />
          <button className="btn btn-primary" onClick={handleSearch}>Search</button>
          <button className="btn" onClick={() => loadConversations()}>Reset</button>
        </div>

        <div className="conversation-list">
          {conversations.map((conversation) => (
            <button
              type="button"
              key={conversation.session_id}
              className={`conversation-row ${
                selectedConversation?.session_id === conversation.session_id ? 'selected' : ''
              }`}
              onClick={() => openConversation(conversation.session_id)}
            >
              <div className="conversation-row-header">
                <span>{conversation.user_id}</span>
                <span>{conversation.status}</span>
              </div>
              <div className="conversation-row-meta">
                <span>{conversation.message_count} messages</span>
                <span>{formatTimestamp(conversation.last_interaction_at)}</span>
              </div>
              <div className="conversation-row-preview">
                {conversation.last_message_preview || 'No messages yet'}
              </div>
            </button>
          ))}
          {conversations.length === 0 && !isConversationLoading && (
            <div className="empty-state">No conversations found.</div>
          )}
        </div>
      </div>

      <div className="conversation-detail-panel">
        {isConversationLoading && <div className="loading">Loading conversation...</div>}
        {!isConversationLoading && !selectedConversation && (
          <div className="empty-state">Select a conversation to view details.</div>
        )}

        {!isConversationLoading && selectedConversation && (
          <div className="conversation-detail">
            <div className="conversation-summary">
              <h3>{selectedConversation.user_id}</h3>
              <p>Session: {selectedConversation.session_id}</p>
              <p>Status: {selectedConversation.status}</p>
              <p>Messages: {selectedConversation.message_count}</p>
              <p>Agent: {selectedConversation.current_agent_id || 'N/A'}</p>
              <p>Flow: {selectedConversation.current_flow || 'N/A'}</p>
            </div>

            <div className="conversation-columns">
              <section>
                <h4>Messages</h4>
                <div className="scroll-panel">
                  {(selectedConversation.messages || []).map((message) => (
                    <div key={message.id} className={`message-item ${message.role}`}>
                      <div className="message-header">
                        <span>{message.role}</span>
                        <span>{formatTimestamp(message.created_at)}</span>
                      </div>
                      <div className="message-content">{message.content}</div>
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <h4>Event Trace</h4>
                <div className="scroll-panel">
                  {conversationEvents.map((event) => (
                    <div key={`${event.turn_id}-${event.id}`} className="event-item">
                      <div className="event-header">
                        <span>{event.category}</span>
                        <span>{event.event_type}</span>
                      </div>
                      <div className="event-message">{event.message}</div>
                      <div className="event-meta">{formatTimestamp(event.timestamp)}</div>
                    </div>
                  ))}
                  {conversationEvents.length === 0 && (
                    <div className="empty-state">No event trace recorded.</div>
                  )}
                </div>
              </section>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
