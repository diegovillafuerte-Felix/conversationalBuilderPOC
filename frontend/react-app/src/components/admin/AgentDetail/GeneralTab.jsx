import { useState, useEffect } from 'react';
import { useAdminStore } from '../../../store/adminStore';

export default function GeneralTab() {
  const selectedAgent = useAdminStore((state) => state.selectedAgent);
  const agents = useAdminStore((state) => state.agents);
  const updateAgent = useAdminStore((state) => state.updateAgent);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    parent_agent_id: '',
    system_prompt_addition: '',
    model_config_json: '{}',
    navigation_tools: '{}',
    is_active: true,
  });

  useEffect(() => {
    if (selectedAgent) {
      setFormData({
        name: selectedAgent.name || '',
        description: selectedAgent.description || '',
        parent_agent_id: selectedAgent.parent_agent_id || '',
        system_prompt_addition: selectedAgent.system_prompt_addition || '',
        model_config_json: JSON.stringify(selectedAgent.model_config_json || {}, null, 2),
        navigation_tools: JSON.stringify(selectedAgent.navigation_tools || {}, null, 2),
        is_active: selectedAgent.is_active ?? true,
      });
    }
  }, [selectedAgent]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    let modelConfig, navTools;
    try {
      modelConfig = JSON.parse(formData.model_config_json || '{}');
    } catch {
      alert('Invalid JSON in Model Configuration');
      return;
    }

    try {
      navTools = JSON.parse(formData.navigation_tools || '{}');
    } catch {
      alert('Invalid JSON in Navigation Tools');
      return;
    }

    await updateAgent(selectedAgent.id, {
      name: formData.name.trim(),
      description: formData.description.trim(),
      parent_agent_id: formData.parent_agent_id || null,
      system_prompt_addition: formData.system_prompt_addition.trim() || null,
      model_config_json: modelConfig,
      navigation_tools: navTools,
      is_active: formData.is_active,
    });
  };

  const availableParents = agents.filter((a) => a.id !== selectedAgent?.id);

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-row">
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
          <label>Parent Agent</label>
          <select
            name="parent_agent_id"
            value={formData.parent_agent_id}
            onChange={handleChange}
          >
            <option value="">None (Root Agent)</option>
            {availableParents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>
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
        <label>System Prompt Addition</label>
        <textarea
          name="system_prompt_addition"
          value={formData.system_prompt_addition}
          onChange={handleChange}
          rows={4}
          placeholder="Additional instructions for this agent..."
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Model Configuration (JSON)</label>
          <textarea
            name="model_config_json"
            value={formData.model_config_json}
            onChange={handleChange}
            rows={4}
          />
        </div>
        <div className="form-group">
          <label>Navigation Tools (JSON)</label>
          <textarea
            name="navigation_tools"
            value={formData.navigation_tools}
            onChange={handleChange}
            rows={4}
          />
        </div>
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            name="is_active"
            checked={formData.is_active}
            onChange={handleChange}
          />
          Active
        </label>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary">
          Save Changes
        </button>
      </div>
    </form>
  );
}
