import { useAdminStore } from '../../../store/adminStore';
import Badge from '../Common/Badge';

export default function ToolsTab() {
  const selectedAgent = useAdminStore((state) => state.selectedAgent);
  const showModal = useAdminStore((state) => state.showModal);

  const tools = selectedAgent?.tools || [];

  return (
    <div>
      <div className="section-header">
        <h3>Tools ({tools.length})</h3>
        <button className="btn btn-primary btn-small" onClick={() => showModal('tool')}>
          + Add Tool
        </button>
      </div>

      <div className="items-list">
        {tools.length === 0 ? (
          <div className="empty-list">No tools configured</div>
        ) : (
          tools.map((tool) => (
            <div key={tool.id} className="list-item">
              <div className="list-item-header">
                <div className="list-item-title">{tool.name}</div>
                <div className="list-item-actions">
                  <button
                    className="btn btn-secondary btn-small"
                    onClick={() => showModal('tool', tool)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-danger btn-small"
                    onClick={() => showModal('confirmDelete', { type: 'tool', id: tool.id, name: tool.name })}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div className="list-item-desc">{tool.description}</div>
              <div className="list-item-meta">
                <span>
                  Side Effects:{' '}
                  <Badge variant={tool.side_effects === 'financial' ? 'danger' : tool.side_effects === 'write' ? 'warning' : ''}>
                    {tool.side_effects}
                  </Badge>
                </span>
                {tool.requires_confirmation && <Badge variant="warning">Requires Confirmation</Badge>}
                {tool.flow_transition && <Badge>Has Flow Transition</Badge>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
