import { useState } from 'react';
import { useAdminStore } from '../../../store/adminStore';
import Modal from '../Common/Modal';

export default function AgentModal() {
  const agents = useAdminStore((state) => state.agents);
  const createAgent = useAdminStore((state) => state.createAgent);
  const closeModal = useAdminStore((state) => state.closeModal);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    parent_agent_id: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await createAgent({
      name: formData.name.trim(),
      description: formData.description.trim(),
      parent_agent_id: formData.parent_agent_id || null,
      model_config_json: {},
      navigation_tools: {},
    });
  };

  return (
    <Modal title="Create Agent" onClose={closeModal}>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Name</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={2}
          />
        </div>

        <div className="form-group">
          <label>Parent Agent</label>
          <select name="parent_agent_id" value={formData.parent_agent_id} onChange={handleChange}>
            <option value="">None (Root Agent)</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={closeModal}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary">
            Create Agent
          </button>
        </div>
      </form>
    </Modal>
  );
}
