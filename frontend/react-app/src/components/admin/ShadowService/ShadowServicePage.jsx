import { useEffect, useState } from 'react';
import { useShadowServiceStore } from '../../../store/shadowServiceStore';
import SubagentCard from './SubagentCard';
import SubagentModal from './SubagentModal';
import Toast from '../Common/Toast';

export default function ShadowServicePage() {
  const config = useShadowServiceStore((state) => state.config);
  const isLoading = useShadowServiceStore((state) => state.isLoading);
  const loadConfig = useShadowServiceStore((state) => state.loadConfig);
  const updateGlobalConfig = useShadowServiceStore((state) => state.updateGlobalConfig);
  const openModal = useShadowServiceStore((state) => state.openModal);
  const showModal = useShadowServiceStore((state) => state.showModal);
  const toast = useShadowServiceStore((state) => state.toast);

  const [formData, setFormData] = useState({
    enabled: true,
    global_cooldown_messages: 3,
    max_messages_per_response: 1,
  });

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    if (config) {
      setFormData({
        enabled: config.enabled ?? true,
        global_cooldown_messages: config.global_cooldown_messages ?? 3,
        max_messages_per_response: config.max_messages_per_response ?? 1,
      });
    }
  }, [config]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value, 10) : value,
    }));
  };

  const handleSaveGlobal = async (e) => {
    e.preventDefault();
    await updateGlobalConfig(formData);
  };

  if (isLoading && !config) {
    return <div className="loading">Loading shadow service configuration...</div>;
  }

  return (
    <div className="shadow-service-page">
      <div className="page-header">
        <h2>Shadow Service</h2>
        <p className="page-description">
          Configure shadow subagents that run in parallel with conversations to provide contextual tips and promotions.
        </p>
      </div>

      {/* Global Settings */}
      <section className="config-section">
        <h3>Global Settings</h3>
        <form onSubmit={handleSaveGlobal}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label checkbox-label">
                <input
                  type="checkbox"
                  name="enabled"
                  checked={formData.enabled}
                  onChange={handleChange}
                />
                Enable Shadow Service
              </label>
              <p className="form-help">When disabled, no shadow messages will be generated.</p>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Global Cooldown (messages)</label>
              <input
                type="number"
                name="global_cooldown_messages"
                value={formData.global_cooldown_messages}
                onChange={handleChange}
                min="0"
                max="100"
              />
              <p className="form-help">Minimum messages between any shadow message.</p>
            </div>
            <div className="form-group">
              <label className="form-label">Max Messages Per Response</label>
              <input
                type="number"
                name="max_messages_per_response"
                value={formData.max_messages_per_response}
                onChange={handleChange}
                min="1"
                max="5"
              />
              <p className="form-help">Maximum shadow messages to include in a single response.</p>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Save Global Settings
            </button>
          </div>
        </form>
      </section>

      {/* Subagents List */}
      <section className="config-section">
        <div className="section-header">
          <h3>Shadow Subagents</h3>
          <button
            className="btn btn-primary btn-small"
            onClick={() => showModal('createSubagent')}
          >
            + Add Subagent
          </button>
        </div>

        {config?.subagents?.length === 0 ? (
          <div className="empty-state">
            <p>No shadow subagents configured yet.</p>
            <button
              className="btn btn-primary"
              onClick={() => showModal('createSubagent')}
            >
              Create First Subagent
            </button>
          </div>
        ) : (
          <div className="subagents-grid">
            {config?.subagents?.map((subagent) => (
              <SubagentCard key={subagent.id} subagent={subagent} />
            ))}
          </div>
        )}
      </section>

      {/* Modals */}
      {(openModal === 'editSubagent' || openModal === 'createSubagent') && <SubagentModal />}

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  );
}
