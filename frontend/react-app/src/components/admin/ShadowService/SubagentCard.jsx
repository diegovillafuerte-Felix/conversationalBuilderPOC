import { useShadowServiceStore } from '../../../store/shadowServiceStore';
import Badge from '../Common/Badge';

export default function SubagentCard({ subagent }) {
  const showModal = useShadowServiceStore((state) => state.showModal);
  const toggleSubagent = useShadowServiceStore((state) => state.toggleSubagent);

  const handleToggle = async (e) => {
    e.stopPropagation();
    await toggleSubagent(subagent.id);
  };

  const handleEdit = () => {
    showModal('editSubagent', subagent);
  };

  const getSourceLabel = () => {
    if (typeof subagent.source_label === 'object') {
      return subagent.source_label.en || subagent.source_label.es || subagent.id;
    }
    return subagent.source_label || subagent.id;
  };

  return (
    <div
      className={`subagent-card ${!subagent.enabled ? 'disabled' : ''}`}
      onClick={handleEdit}
    >
      <div className="subagent-card-header">
        <div className="subagent-card-title">
          <h4>{getSourceLabel()}</h4>
          <Badge variant={subagent.enabled ? 'default' : 'warning'}>
            {subagent.enabled ? 'Active' : 'Disabled'}
          </Badge>
        </div>
        <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={subagent.enabled}
            onChange={handleToggle}
          />
          <span className="toggle-slider"></span>
        </label>
      </div>

      <div className="subagent-card-body">
        <div className="subagent-stat">
          <span className="stat-label">Threshold</span>
          <span className="stat-value">{subagent.relevance_threshold}%</span>
        </div>
        <div className="subagent-stat">
          <span className="stat-label">Priority</span>
          <span className="stat-value">{subagent.priority}</span>
        </div>
        <div className="subagent-stat">
          <span className="stat-label">Cooldown</span>
          <span className="stat-value">{subagent.cooldown_messages} msgs</span>
        </div>
        <div className="subagent-stat">
          <span className="stat-label">Max Length</span>
          <span className="stat-value">{subagent.max_tip_length} chars</span>
        </div>
      </div>

      {subagent.active_campaigns && subagent.active_campaigns.length > 0 && (
        <div className="subagent-card-footer">
          <span className="campaigns-count">
            {subagent.active_campaigns.length} active campaign{subagent.active_campaigns.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {subagent.full_agent_id && (
        <div className="subagent-card-footer">
          <span className="linked-agent">
            Links to: {subagent.full_agent_id}
          </span>
        </div>
      )}
    </div>
  );
}
