import { useState, useEffect } from 'react';
import { useShadowServiceStore } from '../../../store/shadowServiceStore';
import Modal from '../Common/Modal';
import CampaignEditor from './CampaignEditor';

export default function SubagentModal() {
  const closeModal = useShadowServiceStore((state) => state.closeModal);
  const openModal = useShadowServiceStore((state) => state.openModal);
  const modalData = useShadowServiceStore((state) => state.modalData);
  const updateSubagent = useShadowServiceStore((state) => state.updateSubagent);
  const createSubagent = useShadowServiceStore((state) => state.createSubagent);
  const deleteSubagent = useShadowServiceStore((state) => state.deleteSubagent);
  const showModal = useShadowServiceStore((state) => state.showModal);

  const isEdit = openModal === 'editSubagent' && modalData;

  const [formData, setFormData] = useState({
    id: '',
    enabled: true,
    relevance_threshold: 80,
    model: 'claude-3-haiku-20240307',
    temperature: 0.3,
    priority: 1,
    full_agent_id: '',
    tone_en: '',
    tone_es: '',
    system_prompt_addition_en: '',
    system_prompt_addition_es: '',
    max_tip_length: 280,
    cooldown_messages: 5,
    source_label_en: '',
    source_label_es: '',
    activation_intents: '',
    active_campaigns: [],
  });

  useEffect(() => {
    if (isEdit && modalData) {
      setFormData({
        id: modalData.id || '',
        enabled: modalData.enabled ?? true,
        relevance_threshold: modalData.relevance_threshold ?? 80,
        model: modalData.model || 'claude-3-haiku-20240307',
        temperature: modalData.temperature ?? 0.3,
        priority: modalData.priority ?? 1,
        full_agent_id: modalData.full_agent_id || '',
        tone_en: modalData.tone?.en || '',
        tone_es: modalData.tone?.es || '',
        system_prompt_addition_en: modalData.system_prompt_addition?.en || '',
        system_prompt_addition_es: modalData.system_prompt_addition?.es || '',
        max_tip_length: modalData.max_tip_length ?? 280,
        cooldown_messages: modalData.cooldown_messages ?? 5,
        source_label_en: modalData.source_label?.en || '',
        source_label_es: modalData.source_label?.es || '',
        activation_intents: (modalData.activation_intents || []).join(', '),
        active_campaigns: modalData.active_campaigns || [],
      });
    }
  }, [isEdit, modalData]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox'
        ? checked
        : type === 'number'
          ? parseFloat(value)
          : value,
    }));
  };

  const handleCampaignsChange = (campaigns) => {
    setFormData((prev) => ({ ...prev, active_campaigns: campaigns }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Build the subagent config object
    const subagentConfig = {
      id: formData.id,
      enabled: formData.enabled,
      relevance_threshold: formData.relevance_threshold,
      model: formData.model,
      temperature: formData.temperature,
      priority: formData.priority,
      full_agent_id: formData.full_agent_id || null,
      tone: {
        en: formData.tone_en,
        es: formData.tone_es,
      },
      system_prompt_addition: {
        en: formData.system_prompt_addition_en,
        es: formData.system_prompt_addition_es,
      },
      max_tip_length: formData.max_tip_length,
      cooldown_messages: formData.cooldown_messages,
      source_label: {
        en: formData.source_label_en,
        es: formData.source_label_es,
      },
      activation_intents: formData.activation_intents
        ? formData.activation_intents.split(',').map(s => s.trim()).filter(Boolean)
        : [],
    };

    // Only include campaigns for campaigns-type subagent
    if (formData.active_campaigns.length > 0 || formData.id === 'campaigns') {
      subagentConfig.active_campaigns = formData.active_campaigns;
    }

    if (isEdit) {
      await updateSubagent(formData.id, subagentConfig);
    } else {
      await createSubagent(subagentConfig);
    }
  };

  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete "${formData.id}"?`)) {
      deleteSubagent(formData.id);
    }
  };

  return (
    <Modal
      title={isEdit ? `Edit Subagent: ${formData.id}` : 'Create Subagent'}
      onClose={closeModal}
      size="large"
    >
      <form onSubmit={handleSubmit}>
        {/* Basic Info */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">ID</label>
            <input
              type="text"
              name="id"
              value={formData.id}
              onChange={handleChange}
              disabled={isEdit}
              placeholder="e.g., financial_advisor"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label checkbox-label">
              <input
                type="checkbox"
                name="enabled"
                checked={formData.enabled}
                onChange={handleChange}
              />
              Enabled
            </label>
          </div>
        </div>

        {/* Source Labels */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Source Label (EN)</label>
            <input
              type="text"
              name="source_label_en"
              value={formData.source_label_en}
              onChange={handleChange}
              placeholder="e.g., Felix Financial Advisor"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Source Label (ES)</label>
            <input
              type="text"
              name="source_label_es"
              value={formData.source_label_es}
              onChange={handleChange}
              placeholder="e.g., Asesor Financiero Felix"
            />
          </div>
        </div>

        {/* Threshold and Priority */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Relevance Threshold (%)</label>
            <input
              type="number"
              name="relevance_threshold"
              value={formData.relevance_threshold}
              onChange={handleChange}
              min="0"
              max="100"
            />
            <p className="form-help">Minimum relevance score to trigger (0-100)</p>
          </div>
          <div className="form-group">
            <label className="form-label">Priority</label>
            <input
              type="number"
              name="priority"
              value={formData.priority}
              onChange={handleChange}
              min="1"
              max="10"
            />
            <p className="form-help">Higher priority wins ties (1-10)</p>
          </div>
        </div>

        {/* Model Settings */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Model</label>
            <select name="model" value={formData.model} onChange={handleChange}>
              <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
              <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="gpt-4o">GPT-4o</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Temperature</label>
            <input
              type="number"
              name="temperature"
              value={formData.temperature}
              onChange={handleChange}
              min="0"
              max="1"
              step="0.1"
            />
          </div>
        </div>

        {/* Cooldown and Length */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Cooldown (messages)</label>
            <input
              type="number"
              name="cooldown_messages"
              value={formData.cooldown_messages}
              onChange={handleChange}
              min="0"
              max="50"
            />
            <p className="form-help">Min messages between this subagent's tips</p>
          </div>
          <div className="form-group">
            <label className="form-label">Max Tip Length (chars)</label>
            <input
              type="number"
              name="max_tip_length"
              value={formData.max_tip_length}
              onChange={handleChange}
              min="50"
              max="1000"
            />
          </div>
        </div>

        {/* Linked Agent */}
        <div className="form-group">
          <label className="form-label">Linked Agent ID (for takeover)</label>
          <input
            type="text"
            name="full_agent_id"
            value={formData.full_agent_id}
            onChange={handleChange}
            placeholder="e.g., financial_advisor (leave empty if no takeover)"
          />
          <p className="form-help">Agent to activate when user engages. Leave empty if this subagent only provides tips.</p>
        </div>

        {/* Tone */}
        <div className="form-group">
          <label className="form-label">Tone (EN)</label>
          <textarea
            name="tone_en"
            value={formData.tone_en}
            onChange={handleChange}
            rows="2"
            placeholder="e.g., friendly and helpful, like a knowledgeable friend"
          />
        </div>
        <div className="form-group">
          <label className="form-label">Tone (ES)</label>
          <textarea
            name="tone_es"
            value={formData.tone_es}
            onChange={handleChange}
            rows="2"
            placeholder="e.g., amigable y servicial, como un amigo con conocimiento"
          />
        </div>

        {/* System Prompt Addition */}
        <div className="form-group">
          <label className="form-label">System Prompt Addition (EN)</label>
          <textarea
            name="system_prompt_addition_en"
            value={formData.system_prompt_addition_en}
            onChange={handleChange}
            rows="3"
            placeholder="Additional instructions for this subagent..."
          />
        </div>
        <div className="form-group">
          <label className="form-label">System Prompt Addition (ES)</label>
          <textarea
            name="system_prompt_addition_es"
            value={formData.system_prompt_addition_es}
            onChange={handleChange}
            rows="3"
            placeholder="Instrucciones adicionales para este subagente..."
          />
        </div>

        {/* Activation Intents */}
        <div className="form-group">
          <label className="form-label">Activation Intents</label>
          <input
            type="text"
            name="activation_intents"
            value={formData.activation_intents}
            onChange={handleChange}
            placeholder="budgeting_help, savings_advice, fee_optimization"
          />
          <p className="form-help">Comma-separated list of intents that trigger takeover</p>
        </div>

        {/* Campaigns (only shown if it looks like a campaigns subagent) */}
        {(formData.id === 'campaigns' || formData.active_campaigns.length > 0) && (
          <div className="form-group">
            <label className="form-label">Active Campaigns</label>
            <CampaignEditor
              campaigns={formData.active_campaigns}
              onChange={handleCampaignsChange}
            />
          </div>
        )}

        {/* Actions */}
        <div className="form-actions">
          {isEdit && (
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleDelete}
            >
              Delete
            </button>
          )}
          <div className="form-actions-right">
            <button type="button" className="btn btn-secondary" onClick={closeModal}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              {isEdit ? 'Save Changes' : 'Create Subagent'}
            </button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
