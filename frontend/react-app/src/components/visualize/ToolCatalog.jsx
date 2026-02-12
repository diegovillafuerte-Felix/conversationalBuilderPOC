import { useState, useMemo } from 'react';
import { useVisualizeStore } from '../../store/visualizeStore';

export default function ToolCatalog() {
  const agents = useVisualizeStore((state) => state.agents);
  const [searchQuery, setSearchQuery] = useState('');
  const [agentFilter, setAgentFilter] = useState('');
  const [sideEffectFilter, setSideEffectFilter] = useState('');
  const [expandedTools, setExpandedTools] = useState(new Set());

  // Collect all tools with their agent info
  const allTools = useMemo(() => {
    const tools = [];
    agents.forEach((agent) => {
      if (agent.tools) {
        agent.tools.forEach((tool) => {
          tools.push({
            ...tool,
            agentId: agent.id,
            agentName: agent.name,
          });
        });
      }
    });
    return tools;
  }, [agents]);

  // Get unique side effects for filter
  const sideEffects = useMemo(() => {
    const effects = new Set();
    allTools.forEach((tool) => {
      if (tool.side_effects) {
        effects.add(tool.side_effects);
      }
    });
    return Array.from(effects).sort();
  }, [allTools]);

  // Filter tools
  const filteredTools = useMemo(() => {
    return allTools.filter((tool) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesName = tool.name.toLowerCase().includes(query);
        const matchesDesc = tool.description?.toLowerCase().includes(query);
        if (!matchesName && !matchesDesc) return false;
      }

      // Agent filter
      if (agentFilter && tool.agentId !== agentFilter) return false;

      // Side effect filter
      if (sideEffectFilter && tool.side_effects !== sideEffectFilter) return false;

      return true;
    });
  }, [allTools, searchQuery, agentFilter, sideEffectFilter]);

  // Group tools by agent
  const toolsByAgent = useMemo(() => {
    const grouped = {};
    filteredTools.forEach((tool) => {
      if (!grouped[tool.agentId]) {
        grouped[tool.agentId] = {
          agentName: tool.agentName,
          tools: [],
        };
      }
      grouped[tool.agentId].tools.push(tool);
    });
    return grouped;
  }, [filteredTools]);

  const toggleExpand = (toolKey) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolKey)) {
      newExpanded.delete(toolKey);
    } else {
      newExpanded.add(toolKey);
    }
    setExpandedTools(newExpanded);
  };

  const getRoutingType = (tool) => {
    if (tool.routing?.type === 'enter_agent') return 'navigation';
    if (tool.routing?.type === 'start_flow' || tool.starts_flow) return 'flow';
    if (tool.routing?.cross_agent) return 'cross-agent';
    return 'service';
  };

  return (
    <div className="tool-catalog">
      <div className="catalog-filters">
        <div className="filter-group">
          <input
            type="text"
            placeholder="Search tools..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-group">
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
          >
            <option value="">All Agents</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <select
            value={sideEffectFilter}
            onChange={(e) => setSideEffectFilter(e.target.value)}
          >
            <option value="">All Side Effects</option>
            {sideEffects.map((effect) => (
              <option key={effect} value={effect}>
                {effect}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-summary">
          {filteredTools.length} of {allTools.length} tools
        </div>
      </div>

      <div className="catalog-content">
        {Object.entries(toolsByAgent).map(([agentId, { agentName, tools }]) => (
          <div key={agentId} className="agent-tools-section">
            <h3 className="agent-tools-header">
              {agentName}
              <span className="tools-count">{tools.length} tools</span>
            </h3>

            <div className="tools-grid">
              {tools.map((tool) => {
                const toolKey = `${agentId}-${tool.name}`;
                const isExpanded = expandedTools.has(toolKey);
                const routingType = getRoutingType(tool);

                return (
                  <div
                    key={toolKey}
                    className={`tool-card ${isExpanded ? 'expanded' : ''}`}
                    onClick={() => toggleExpand(toolKey)}
                  >
                    <div className="tool-card-header">
                      <span className="tool-name">{tool.name}</span>
                      <div className="tool-badges">
                        {tool.side_effects && tool.side_effects !== 'none' && (
                          <span className={`tool-badge side-effect ${tool.side_effects}`}>
                            {tool.side_effects}
                          </span>
                        )}
                        <span className={`tool-badge routing-type ${routingType}`}>
                          {routingType}
                        </span>
                        {tool.requires_confirmation && (
                          <span className="tool-badge confirmation">confirm</span>
                        )}
                      </div>
                    </div>

                    <p className="tool-description">
                      {tool.description || 'No description'}
                    </p>

                    {isExpanded && (
                      <div className="tool-details">
                        {tool.parameters && tool.parameters.length > 0 && (
                          <div className="tool-params">
                            <h4>Parameters</h4>
                            <div className="params-list">
                              {tool.parameters.map((param) => (
                                <div key={param.name} className="param-item">
                                  <code className="param-name">
                                    {param.name}
                                    {param.required && <span className="required">*</span>}
                                  </code>
                                  <span className="param-type">{param.type}</span>
                                  {param.description && (
                                    <span className="param-desc">{param.description}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {tool.routing && (
                          <div className="tool-routing">
                            <h4>Routing</h4>
                            <div className="routing-info">
                              <span className="routing-label">Type:</span>
                              <span className="routing-value">{tool.routing.type}</span>
                              {tool.routing.target && (
                                <>
                                  <span className="routing-label">Target:</span>
                                  <span className="routing-value">{tool.routing.target}</span>
                                </>
                              )}
                              {tool.routing.cross_agent && (
                                <>
                                  <span className="routing-label">Cross-Agent:</span>
                                  <span className="routing-value">{tool.routing.cross_agent}</span>
                                </>
                              )}
                            </div>
                          </div>
                        )}

                        {tool.starts_flow && (
                          <div className="tool-routing">
                            <h4>Starts Flow</h4>
                            <code>{tool.starts_flow}</code>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        {filteredTools.length === 0 && (
          <div className="empty-catalog">
            <p>No tools match the current filters</p>
          </div>
        )}
      </div>
    </div>
  );
}
