import { useAdminStore } from '../../../store/adminStore';

function AgentTreeItem({ agent, level = 0, childMap }) {
  const selectedAgentId = useAdminStore((state) => state.selectedAgentId);
  const selectAgent = useAdminStore((state) => state.selectAgent);

  const children = childMap[agent.id] || [];
  const isSelected = agent.id === selectedAgentId;

  return (
    <>
      <div
        className={`agent-tree-item ${isSelected ? 'selected' : ''} ${!agent.is_active ? 'inactive' : ''}`}
        onClick={() => selectAgent(agent.id)}
        style={{ marginLeft: `${level * 16}px` }}
      >
        <div className="agent-name">{agent.name}</div>
        <div className="agent-desc">{agent.description}</div>
      </div>
      {children.map((child) => (
        <AgentTreeItem key={child.id} agent={child} level={level + 1} childMap={childMap} />
      ))}
    </>
  );
}

export default function AgentTree() {
  const agents = useAdminStore((state) => state.agents);
  const showModal = useAdminStore((state) => state.showModal);

  if (agents.length === 0) {
    return <div className="empty-list">No agents configured</div>;
  }

  // Build tree structure
  const rootAgents = agents.filter((a) => !a.parent_agent_id);
  const childMap = {};

  agents.forEach((agent) => {
    if (agent.parent_agent_id) {
      if (!childMap[agent.parent_agent_id]) {
        childMap[agent.parent_agent_id] = [];
      }
      childMap[agent.parent_agent_id].push(agent);
    }
  });

  return (
    <div className="agent-tree">
      {rootAgents.map((agent) => (
        <AgentTreeItem key={agent.id} agent={agent} childMap={childMap} />
      ))}
    </div>
  );
}
