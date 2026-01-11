import { useAdminStore } from '../../../store/adminStore';
import Badge from '../Common/Badge';

export default function TemplatesTab() {
  const selectedAgent = useAdminStore((state) => state.selectedAgent);
  const showModal = useAdminStore((state) => state.showModal);

  const templates = selectedAgent?.response_templates || [];

  return (
    <div>
      <div className="section-header">
        <h3>Response Templates ({templates.length})</h3>
        <button className="btn btn-primary btn-small" onClick={() => showModal('template')}>
          + Add Template
        </button>
      </div>

      <div className="items-list">
        {templates.length === 0 ? (
          <div className="empty-list">No templates configured</div>
        ) : (
          templates.map((template) => (
            <div key={template.id} className="list-item">
              <div className="list-item-header">
                <div className="list-item-title">{template.name}</div>
                <div className="list-item-actions">
                  <button
                    className="btn btn-secondary btn-small"
                    onClick={() => showModal('template', template)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-danger btn-small"
                    onClick={() => showModal('confirmDelete', { type: 'template', id: template.id, name: template.name })}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div className="list-item-desc">
                {template.template?.substring(0, 100)}
                {template.template?.length > 100 ? '...' : ''}
              </div>
              <div className="list-item-meta">
                <span>
                  Enforcement:{' '}
                  <Badge variant={template.enforcement === 'mandatory' ? 'danger' : ''}>
                    {template.enforcement}
                  </Badge>
                </span>
                <span>Trigger: {JSON.stringify(template.trigger_config)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
