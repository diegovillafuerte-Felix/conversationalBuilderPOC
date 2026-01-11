import { useState } from 'react';
import { useChatStore } from '../../store/chatStore';

export default function DebugPanel() {
  const debugEvents = useChatStore((state) => state.debugEvents);
  const [expandedEvents, setExpandedEvents] = useState({});
  const [activeTab, setActiveTab] = useState('events');

  const toggleEvent = (id) => {
    setExpandedEvents((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const getEventIcon = (type) => {
    switch (type) {
      case 'user_message': return '👤';
      case 'assistant_response': return '🤖';
      case 'tool_call': return '🔧';
      case 'escalation': return '⚠️';
      case 'error': return '❌';
      default: return '📝';
    }
  };

  const getEventTitle = (event) => {
    const truncate = (text, maxLen = 40) => {
      if (!text) return '';
      const clean = text.replace(/\n/g, ' ').trim();
      return clean.length > maxLen ? clean.substring(0, maxLen) + '...' : clean;
    };

    switch (event.type) {
      case 'user_message': return `User: ${truncate(event.content)}`;
      case 'assistant_response': {
        const agentName = event.agentName || 'Assistant';
        return `${agentName}: ${truncate(event.content)}`;
      }
      case 'tool_call': return `Tool: ${event.toolName}`;
      case 'escalation': return 'Escalation';
      case 'error': return 'Error';
      default: return event.type;
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const renderEventDetails = (event) => {
    switch (event.type) {
      case 'user_message':
        return (
          <div className="debug-content">
            <pre>{event.content}</pre>
          </div>
        );

      case 'assistant_response':
        return (
          <div className="debug-content">
            <div className="debug-section">
              <strong>Response:</strong>
              <pre>{event.content}</pre>
            </div>
            {event.debug && (
              <>
                {event.debug.processing_time_ms && (
                  <div className="debug-meta">
                    Processing time: {event.debug.processing_time_ms}ms
                  </div>
                )}
                {event.debug.agent_stack && event.debug.agent_stack.length > 0 && (
                  <div className="debug-section">
                    <strong>Agent Stack:</strong>
                    <pre>{JSON.stringify(event.debug.agent_stack, null, 2)}</pre>
                  </div>
                )}
                {event.debug.flow_info && (
                  <div className="debug-section">
                    <strong>Flow State:</strong>
                    <pre>{JSON.stringify(event.debug.flow_info, null, 2)}</pre>
                  </div>
                )}
                {event.debug.context_sections && (
                  <div className="debug-section">
                    <strong>Token Usage:</strong>
                    <pre>{JSON.stringify(event.debug.context_sections, null, 2)}</pre>
                  </div>
                )}
                {event.debug.llm_call && (
                  <>
                    <div className="debug-section">
                      <strong>Model:</strong> {event.debug.llm_call.model} (temp: {event.debug.llm_call.temperature})
                    </div>
                    {event.debug.llm_call.tools_provided?.length > 0 && (
                      <div className="debug-section">
                        <strong>Tools Available:</strong>
                        <div className="debug-tools">
                          {event.debug.llm_call.tools_provided.map((tool, i) => (
                            <span key={i} className="debug-tool-badge">{tool}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="debug-section">
                      <strong>System Prompt:</strong>
                      <details>
                        <summary>Click to expand ({event.debug.llm_call.system_prompt?.length || 0} chars)</summary>
                        <pre className="debug-prompt">{event.debug.llm_call.system_prompt}</pre>
                      </details>
                    </div>
                    <div className="debug-section">
                      <strong>Messages Sent:</strong>
                      <details>
                        <summary>{event.debug.llm_call.messages?.length || 0} messages</summary>
                        <pre>{JSON.stringify(event.debug.llm_call.messages, null, 2)}</pre>
                      </details>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        );

      case 'tool_call':
        return (
          <div className="debug-content">
            <div className="debug-section">
              <strong>Parameters:</strong>
              <pre>{JSON.stringify(event.parameters, null, 2)}</pre>
            </div>
            {event.result && (
              <div className="debug-section">
                <strong>Result:</strong>
                <pre>{JSON.stringify(event.result, null, 2)}</pre>
              </div>
            )}
            {event.requiresConfirmation && (
              <div className="debug-meta warning">Requires user confirmation</div>
            )}
          </div>
        );

      case 'error':
        return (
          <div className="debug-content error">
            <pre>{event.error}</pre>
          </div>
        );

      default:
        return (
          <div className="debug-content">
            <pre>{JSON.stringify(event, null, 2)}</pre>
          </div>
        );
    }
  };

  // Get the last LLM call for the prompt tab
  const lastLLMCall = [...debugEvents]
    .reverse()
    .find((e) => e.type === 'assistant_response' && e.debug?.llm_call);

  return (
    <div className="debug-panel">
      <div className="debug-header">
        <h3>Debug View</h3>
        <div className="debug-tabs">
          <button
            className={`debug-tab ${activeTab === 'events' ? 'active' : ''}`}
            onClick={() => setActiveTab('events')}
          >
            Events ({debugEvents.length})
          </button>
          <button
            className={`debug-tab ${activeTab === 'prompt' ? 'active' : ''}`}
            onClick={() => setActiveTab('prompt')}
          >
            Last Prompt
          </button>
        </div>
      </div>

      <div className="debug-body">
        {activeTab === 'events' && (
          <div className="debug-events">
            {debugEvents.length === 0 ? (
              <div className="debug-empty">
                No events yet. Start a conversation to see debug information.
              </div>
            ) : (
              debugEvents.map((event) => (
                <div key={event.id} className={`debug-event ${event.type}`}>
                  <div
                    className="debug-event-header"
                    onClick={() => toggleEvent(event.id)}
                  >
                    <span className="debug-icon">{getEventIcon(event.type)}</span>
                    <span className="debug-title">{getEventTitle(event)}</span>
                    <span className="debug-time">{formatTime(event.timestamp)}</span>
                    <span className="debug-expand">
                      {expandedEvents[event.id] ? '▼' : '▶'}
                    </span>
                  </div>
                  {expandedEvents[event.id] && renderEventDetails(event)}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'prompt' && (
          <div className="debug-prompt-view">
            {lastLLMCall ? (
              <>
                <div className="debug-section">
                  <strong>Model:</strong> {lastLLMCall.debug.llm_call.model}
                  <br />
                  <strong>Temperature:</strong> {lastLLMCall.debug.llm_call.temperature}
                  <br />
                  <strong>Processing Time:</strong> {lastLLMCall.debug.processing_time_ms}ms
                </div>
                <div className="debug-section">
                  <strong>System Prompt:</strong>
                  <pre className="debug-prompt-full">
                    {lastLLMCall.debug.llm_call.system_prompt}
                  </pre>
                </div>
                <div className="debug-section">
                  <strong>Messages ({lastLLMCall.debug.llm_call.messages?.length || 0}):</strong>
                  <pre className="debug-messages-full">
                    {JSON.stringify(lastLLMCall.debug.llm_call.messages, null, 2)}
                  </pre>
                </div>
                {lastLLMCall.debug.llm_call.tools_provided?.length > 0 && (
                  <div className="debug-section">
                    <strong>Tools ({lastLLMCall.debug.llm_call.tools_provided.length}):</strong>
                    <div className="debug-tools">
                      {lastLLMCall.debug.llm_call.tools_provided.map((tool, i) => (
                        <span key={i} className="debug-tool-badge">{tool}</span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="debug-empty">
                No LLM calls yet. Send a message to see the prompt.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
