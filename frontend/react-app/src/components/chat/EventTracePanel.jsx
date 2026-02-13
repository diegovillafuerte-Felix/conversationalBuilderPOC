import { useState, useMemo } from 'react';
import { useChatStore } from '../../store/chatStore';

const CATEGORY_COLORS = {
  session: '#6c5ce7',
  agent: '#00b894',
  flow: '#0984e3',
  routing: '#fdcb6e',
  enrichment: '#e17055',
  llm: '#00cec9',
  tool: '#74b9ff',
  service: '#a29bfe',
  error: '#d63031',
};

const CATEGORY_ICONS = {
  session: '🔗',
  agent: '🤖',
  flow: '📊',
  routing: '🔀',
  enrichment: '📥',
  llm: '🧠',
  tool: '🔧',
  service: '🌐',
  error: '❌',
};

export default function EventTracePanel() {
  const eventTrace = useChatStore((state) => state.eventTrace);
  const [filters, setFilters] = useState({
    categories: Object.keys(CATEGORY_COLORS),
    levels: ['info', 'debug', 'warning', 'error'],
    searchText: '',
  });
  const [expandedEvents, setExpandedEvents] = useState(new Set());
  const [expandedTurns, setExpandedTurns] = useState(new Set());
  const [copied, setCopied] = useState(false);

  // Group events by turn_id
  const groupedEvents = useMemo(() => {
    const groups = [];
    let currentTurnId = null;
    let currentGroup = null;

    eventTrace.forEach(event => {
      // Apply filters
      if (!filters.categories.includes(event.category)) return;
      if (!filters.levels.includes(event.level)) return;
      if (filters.searchText && !event.message.toLowerCase().includes(filters.searchText.toLowerCase())) return;

      if (event.turn_id !== currentTurnId) {
        if (currentGroup) {
          groups.push(currentGroup);
        }
        currentTurnId = event.turn_id;
        currentGroup = {
          turn_id: event.turn_id,
          user_message: event.user_message || null,
          assistant_response: event.assistant_response || null,
          events: [],
          timestamp: event.timestamp,
        };
      }
      if (currentGroup) {
        currentGroup.events.push(event);
        // Capture assistant_response if present on any event
        if (event.assistant_response) {
          currentGroup.assistant_response = event.assistant_response;
        }
      }
    });

    if (currentGroup && currentGroup.events.length > 0) {
      groups.push(currentGroup);
    }

    return groups;
  }, [eventTrace, filters]);

  const totalFilteredEvents = useMemo(() => {
    return groupedEvents.reduce((sum, g) => sum + g.events.length, 0);
  }, [groupedEvents]);

  const toggleExpand = (eventId) => {
    setExpandedEvents(prev => {
      const next = new Set(prev);
      if (next.has(eventId)) next.delete(eventId);
      else next.add(eventId);
      return next;
    });
  };

  const toggleTurn = (turnId) => {
    setExpandedTurns(prev => {
      const next = new Set(prev);
      if (next.has(turnId)) next.delete(turnId);
      else next.add(turnId);
      return next;
    });
  };

  const toggleCategory = (cat) => {
    setFilters(f => ({
      ...f,
      categories: f.categories.includes(cat)
        ? f.categories.filter(c => c !== cat)
        : [...f.categories, cat]
    }));
  };

  const copyToClipboard = () => {
    const lines = [];
    let eventNumber = 1;
    groupedEvents.forEach(group => {
      if (group.user_message) {
        lines.push(`\n=== USER: "${group.user_message}" ===`);
      } else {
        lines.push(`\n=== Turn ${group.turn_id} ===`);
      }
      group.events.forEach(e => {
        const duration = e.duration_ms ? ` (${e.duration_ms}ms)` : '';
        const dataStr = e.data && Object.keys(e.data).length > 0
          ? `\n    Data: ${JSON.stringify(e.data)}`
          : '';
        lines.push(`#${eventNumber} [${e.category.toUpperCase()}] ${e.event_type}: ${e.message}${duration}${dataStr}`);
        eventNumber++;
      });
    });
    navigator.clipboard.writeText(lines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  // Auto-expand the latest turn
  const latestTurnId = groupedEvents.length > 0 ? groupedEvents[groupedEvents.length - 1].turn_id : null;

  return (
    <div className="event-trace-panel">
      <div className="trace-header">
        <h3>Event Trace</h3>
        <div className="trace-header-actions">
          <button
            className={`copy-btn ${copied ? 'copied' : ''}`}
            onClick={copyToClipboard}
            title="Copy logs to clipboard"
          >
            {copied ? '✓ Copied!' : '📋 Copy'}
          </button>
          <span className="event-count">{totalFilteredEvents} events</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="trace-filters">
        <input
          type="text"
          placeholder="Search events..."
          value={filters.searchText}
          onChange={e => setFilters(f => ({...f, searchText: e.target.value}))}
        />
        <div className="category-toggles">
          {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
            <button
              key={cat}
              className={`category-toggle ${filters.categories.includes(cat) ? 'active' : ''}`}
              style={{ borderColor: color }}
              onClick={() => toggleCategory(cat)}
              title={cat}
            >
              {CATEGORY_ICONS[cat]}
            </button>
          ))}
        </div>
      </div>

      {/* Event List - Grouped by Turn */}
      <div className="trace-events">
        {groupedEvents.length === 0 ? (
          <div className="no-events">
            {eventTrace.length === 0
              ? 'No events yet. Send a message to see traces.'
              : 'No events match the current filters.'}
          </div>
        ) : (
          groupedEvents.map((group, groupIndex) => {
            const isExpanded = expandedTurns.has(group.turn_id) || group.turn_id === latestTurnId;
            return (
              <div key={group.turn_id} className="turn-group">
                <div
                  className="turn-header"
                  onClick={() => toggleTurn(group.turn_id)}
                >
                  <span className="turn-arrow">{isExpanded ? '▼' : '▶'}</span>
                  <span className="turn-icon">💬</span>
                  <span className="turn-message">
                    {group.user_message
                      ? `"${group.user_message.length > 50 ? group.user_message.substring(0, 50) + '...' : group.user_message}"`
                      : `Turn ${groupIndex + 1}`}
                  </span>
                  <span className="turn-count">{group.events.length} events</span>
                  <span className="turn-time">{formatTime(group.timestamp)}</span>
                </div>

                {isExpanded && (
                  <div className="turn-events">
                    {group.events.map((event, eventIndex) => {
                      // Calculate global event number (sum of all events in previous groups + current index + 1)
                      const eventNumber = groupedEvents
                        .slice(0, groupIndex)
                        .reduce((sum, g) => sum + g.events.length, 0) + eventIndex + 1;
                      return (
                        <div
                          key={event.id}
                          className={`trace-event level-${event.level}`}
                          style={{ borderLeftColor: CATEGORY_COLORS[event.category] || '#888' }}
                        >
                          <div className="event-header" onClick={() => toggleExpand(event.id)}>
                            <span className="event-number">#{eventNumber}</span>
                            <span className="event-icon">{CATEGORY_ICONS[event.category] || '📌'}</span>
                            <span className="event-type">{event.event_type}</span>
                            <span className="event-message">{event.message}</span>
                            {event.duration_ms && (
                              <span className="event-duration">{event.duration_ms}ms</span>
                            )}
                            <span className="event-time">
                              {formatTime(event.timestamp)}
                            </span>
                            <span className="expand-arrow">
                              {expandedEvents.has(event.id) ? '▼' : '▶'}
                            </span>
                          </div>

                          {expandedEvents.has(event.id) && event.data && Object.keys(event.data).length > 0 && (
                            <div className="event-data">
                              <pre>{JSON.stringify(event.data, null, 2)}</pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Assistant Response Footer */}
                {group.assistant_response && (
                  <div className="turn-response">
                    <span className="response-icon">🤖</span>
                    <span className="response-label">Response:</span>
                    <span className="response-text">{group.assistant_response}</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
