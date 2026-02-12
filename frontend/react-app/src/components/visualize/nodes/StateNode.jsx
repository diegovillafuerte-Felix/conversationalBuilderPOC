import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { useVisualizeStore } from '../../../store/visualizeStore';

function StateNode({ data }) {
  const showDetailPanel = useVisualizeStore((state) => state.showDetailPanel);

  const handleClick = () => {
    showDetailPanel('state', data.state);
  };

  return (
    <div
      className={`state-node ${data.isInitial ? 'initial' : ''} ${data.isFinal ? 'final' : ''}`}
      onClick={handleClick}
    >
      <Handle type="target" position={Position.Top} className="state-handle" />

      <div className="state-node-header">
        <span className="state-node-name">{data.label}</span>
        {data.isInitial && <span className="state-node-badge initial">Start</span>}
        {data.isFinal && <span className="state-node-badge final">End</span>}
      </div>

      <div className="state-node-info">
        {data.hasOnEnter && (
          <span className="state-node-indicator" title="Has on_enter action">
            Auto
          </span>
        )}
        {data.stateToolsCount > 0 && (
          <span className="state-node-tools">
            {data.stateToolsCount} tool{data.stateToolsCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="state-handle" />
    </div>
  );
}

export default memo(StateNode);
