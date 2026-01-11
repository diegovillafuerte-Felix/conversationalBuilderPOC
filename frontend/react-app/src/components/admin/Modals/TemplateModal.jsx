import { useState, useEffect } from 'react';
import { useAdminStore } from '../../../store/adminStore';
import Modal from '../Common/Modal';

export default function TemplateModal() {
  const modalData = useAdminStore((state) => state.modalData);
  const selectedAgentId = useAdminStore((state) => state.selectedAgentId);
  const createTemplate = useAdminStore((state) => state.createTemplate);
  const updateTemplate = useAdminStore((state) => state.updateTemplate);
  const closeModal = useAdminStore((state) => state.closeModal);

  const isEdit = !!modalData?.id;

  const [formData, setFormData] = useState({
    name: '',
    enforcement: 'suggested',
    trigger_config: '',
    template: '',
    required_fields: '',
  });

  useEffect(() => {
    if (modalData) {
      setFormData({
        name: modalData.name || '',
        enforcement: modalData.enforcement || 'suggested',
        trigger_config: modalData.trigger_config ? JSON.stringify(modalData.trigger_config, null, 2) : '',
        template: modalData.template || '',
        required_fields: (modalData.required_fields || []).join(', '),
      });
    }
  }, [modalData]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
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

    const triggerConfig = parseJson(formData.trigger_config);
    if (!triggerConfig) {
      alert('Invalid JSON in Trigger Configuration');
      return;
    }

    const requiredFields = formData.required_fields.trim()
      ? formData.required_fields.split(',').map((f) => f.trim()).filter((f) => f)
      : null;

    const data = {
      name: formData.name.trim(),
      enforcement: formData.enforcement,
      trigger_config: triggerConfig,
      template: formData.template.trim(),
      required_fields: requiredFields,
    };

    if (isEdit) {
      await updateTemplate(modalData.id, data);
    } else {
      await createTemplate(selectedAgentId, data);
    }
  };

  return (
    <Modal title={isEdit ? 'Edit Template' : 'Add Template'} onClose={closeModal} size="large">
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
            <label>Enforcement</label>
            <select name="enforcement" value={formData.enforcement} onChange={handleChange}>
              <option value="suggested">Suggested</option>
              <option value="mandatory">Mandatory</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Trigger Configuration (JSON)</label>
          <textarea
            name="trigger_config"
            value={formData.trigger_config}
            onChange={handleChange}
            rows={3}
            placeholder='{"tool": "transfer_success"}'
            required
          />
        </div>

        <div className="form-group">
          <label>Template</label>
          <textarea
            name="template"
            value={formData.template}
            onChange={handleChange}
            rows={6}
            placeholder="Tu transferencia de ${amount} a ${recipient} ha sido procesada. Número de confirmación: ${confirmation_number}"
          />
        </div>

        <div className="form-group">
          <label>Required Fields (comma-separated)</label>
          <input
            type="text"
            name="required_fields"
            value={formData.required_fields}
            onChange={handleChange}
            placeholder="amount, recipient, confirmation_number"
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={closeModal}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary">
            {isEdit ? 'Save Changes' : 'Add Template'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
