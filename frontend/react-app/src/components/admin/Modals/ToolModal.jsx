import { useState, useEffect } from 'react';
import { useAdminStore } from '../../../store/adminStore';
import Modal from '../Common/Modal';

export default function ToolModal() {
  const modalData = useAdminStore((state) => state.modalData);
  const selectedAgentId = useAdminStore((state) => state.selectedAgentId);
  const createTool = useAdminStore((state) => state.createTool);
  const updateTool = useAdminStore((state) => state.updateTool);
  const closeModal = useAdminStore((state) => state.closeModal);

  const isEdit = !!modalData?.id;

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    side_effects: 'read',
    parameters: '',
    api_config: '',
    requires_confirmation: false,
    confirmation_template: '',
    flow_transition: '',
  });

  useEffect(() => {
    if (modalData) {
      setFormData({
        name: modalData.name || '',
        description: modalData.description || '',
        side_effects: modalData.side_effects || 'read',
        parameters: modalData.parameters ? JSON.stringify(modalData.parameters, null, 2) : '',
        api_config: modalData.api_config ? JSON.stringify(modalData.api_config, null, 2) : '',
        requires_confirmation: modalData.requires_confirmation || false,
        confirmation_template: modalData.confirmation_template || '',
        flow_transition: modalData.flow_transition ? JSON.stringify(modalData.flow_transition, null, 2) : '',
      });
    }
  }, [modalData]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const parseJson = (value) => {
    if (!value || !value.trim()) return null;
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const parameters = parseJson(formData.parameters);
    const apiConfig = parseJson(formData.api_config);
    const flowTransition = parseJson(formData.flow_transition);

    if (formData.parameters && parameters === null) {
      alert('Invalid JSON in Parameters field');
      return;
    }
    if (formData.api_config && apiConfig === null) {
      alert('Invalid JSON in API Configuration field');
      return;
    }
    if (formData.flow_transition && flowTransition === null) {
      alert('Invalid JSON in Flow Transition field');
      return;
    }

    const data = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      side_effects: formData.side_effects,
      parameters,
      api_config: apiConfig,
      requires_confirmation: formData.requires_confirmation,
      confirmation_template: formData.confirmation_template.trim() || null,
      flow_transition: flowTransition,
    };

    if (isEdit) {
      await updateTool(modalData.id, data);
    } else {
      await createTool(selectedAgentId, data);
    }
  };

  return (
    <Modal title={isEdit ? 'Edit Tool' : 'Add Tool'} onClose={closeModal} size="large">
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
            <label>Side Effects</label>
            <select name="side_effects" value={formData.side_effects} onChange={handleChange}>
              <option value="read">Read</option>
              <option value="write">Write</option>
              <option value="financial">Financial</option>
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
          <label>Parameters (JSON)</label>
          <textarea
            name="parameters"
            value={formData.parameters}
            onChange={handleChange}
            rows={4}
            placeholder='{"amount": {"type": "number", "required": true}}'
          />
        </div>

        <div className="form-group">
          <label>API Configuration (JSON)</label>
          <textarea
            name="api_config"
            value={formData.api_config}
            onChange={handleChange}
            rows={4}
            placeholder='{"endpoint": "/api/...", "method": "POST"}'
          />
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              name="requires_confirmation"
              checked={formData.requires_confirmation}
              onChange={handleChange}
            />
            Requires Confirmation
          </label>
        </div>

        {formData.requires_confirmation && (
          <div className="form-group">
            <label>Confirmation Template</label>
            <textarea
              name="confirmation_template"
              value={formData.confirmation_template}
              onChange={handleChange}
              rows={3}
              placeholder="¿Confirmas el envío de ${amount} a ${recipient}?"
            />
          </div>
        )}

        <div className="form-group">
          <label>Flow Transition (JSON)</label>
          <textarea
            name="flow_transition"
            value={formData.flow_transition}
            onChange={handleChange}
            rows={3}
            placeholder='{"target_flow": "...", "target_state": "..."}'
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={closeModal}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary">
            {isEdit ? 'Save Changes' : 'Add Tool'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
