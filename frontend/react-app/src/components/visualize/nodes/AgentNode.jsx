import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { useVisualizeStore } from '../../../store/visualizeStore';

function AgentNode({ data }) {
  const showDetailPanel = useVisualizeStore((state) => state.showDetailPanel);

  const handleClick = () => {
    showDetailPanel('agent', data.agent);
  };

  return (
    <div
      className={`agent-node ${data.isActive ? '' : 'inactive'}`}
      onClick={handleClick}
    >
      <Handle type="target" position={Position.Top} className="agent-handle" />

      <div className="agent-node-header">
        <span className="agent-node-name">{data.label}</span>
        {!data.isActive && <span className="agent-node-badge inactive">Inactive</span>}
      </div>

      <div className="agent-node-stats">
        <div className="agent-node-stat">
          <span className="stat-icon">T</span>
          <span className="stat-value">{data.toolCount}</span>
          <span className="stat-label">tools</span>
        </div>
        <div className="agent-node-stat">
          <span className="stat-icon">F</span>
          <span className="stat-value">{data.subflowCount}</span>
          <span className="stat-label">flows</span>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="agent-handle" />
    </div>
  );
}

export default memo(AgentNode);
