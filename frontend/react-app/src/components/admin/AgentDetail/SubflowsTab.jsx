import { useAdminStore } from '../../../store/adminStore';
import Badge from '../Common/Badge';

function StateItem({ state, subflowId }) {
  const showModal = useAdminStore((state) => state.showModal);

  return (
    <div className={`state-item ${state.is_final ? 'final' : ''}`}>
      <div className="state-info">
        <strong>{state.name}</strong>
        <span className="state-id">({state.state_id})</span>
        {state.is_final && <Badge>Final</Badge>}
      </div>
      <div className="list-item-actions">
        <button
          className="btn btn-secondary btn-small"
          onClick={() => showModal('state', { state, subflowId })}
        >
          Edit
        </button>
        <button
          className="btn btn-danger btn-small"
          onClick={() => showModal('confirmDelete', { type: 'state', id: state.id, name: state.name })}
        >
          Delete
        </button>
      </div>
    </div>
  );
}

function SubflowStates({ subflow }) {
  const showModal = useAdminStore((state) => state.showModal);
  const states = subflow.states || [];

  return (
    <div className="subflow-states">
      <div className="subflow-states-header">
        <h4>States</h4>
        <button
          className="btn btn-secondary btn-small"
          onClick={() => showModal('state', { subflowId: subflow.id })}
        >
          + Add State
        </button>
      </div>
      {states.length === 0 ? (
        <div className="empty-list" style={{ padding: '16px' }}>No states defined</div>
      ) : (
        states.map((state) => (
          <StateItem key={state.id} state={state} subflowId={subflow.id} />
        ))
      )}
    </div>
  );
}

export default function SubflowsTab() {
  const selectedAgent = useAdminStore((state) => state.selectedAgent);
  const showModal = useAdminStore((state) => state.showModal);

  const subflows = selectedAgent?.subflows || [];

  return (
    <div>
      <div className="section-header">
        <h3>Subflows ({subflows.length})</h3>
        <button className="btn btn-primary btn-small" onClick={() => showModal('subflow')}>
          + Add Subflow
        </button>
      </div>

      <div className="items-list">
        {subflows.length === 0 ? (
          <div className="empty-list">No subflows configured</div>
        ) : (
          subflows.map((subflow) => (
            <div key={subflow.id} className="list-item">
              <div className="list-item-header">
                <div className="list-item-title">{subflow.name}</div>
                <div className="list-item-actions">
                  <button
                    className="btn btn-secondary btn-small"
                    onClick={() => showModal('subflow', subflow)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-danger btn-small"
                    onClick={() => showModal('confirmDelete', { type: 'subflow', id: subflow.id, name: subflow.name })}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div className="list-item-desc">{subflow.trigger_description}</div>
              <div className="list-item-meta">
                <span>Initial State: <code>{subflow.initial_state}</code></span>
                <span>{subflow.states?.length || 0} state(s)</span>
              </div>
              <SubflowStates subflow={subflow} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
