import { useState, useEffect } from 'react';
import { useAdminStore } from '../../../store/adminStore';
import Modal from '../Common/Modal';

export default function SubflowModal() {
  const modalData = useAdminStore((state) => state.modalData);
  const selectedAgentId = useAdminStore((state) => state.selectedAgentId);
  const createSubflow = useAdminStore((state) => state.createSubflow);
  const updateSubflow = useAdminStore((state) => state.updateSubflow);
  const closeModal = useAdminStore((state) => state.closeModal);

  const isEdit = !!modalData?.id;

  const [formData, setFormData] = useState({
    name: '',
    trigger_description: '',
    initial_state: '',
    data_schema: '',
  });

  useEffect(() => {
    if (modalData) {
      setFormData({
        name: modalData.name || '',
        trigger_description: modalData.trigger_description || '',
        initial_state: modalData.initial_state || '',
        data_schema: modalData.data_schema ? JSON.stringify(modalData.data_schema, null, 2) : '',
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

    const dataSchema = parseJson(formData.data_schema);
    if (formData.data_schema && dataSchema === null) {
      alert('Invalid JSON in Data Schema');
      return;
    }

    const data = {
      name: formData.name.trim(),
      trigger_description: formData.trigger_description.trim(),
      initial_state: formData.initial_state.trim(),
      data_schema: dataSchema,
    };

    if (isEdit) {
      await updateSubflow(modalData.id, data);
    } else {
      await createSubflow(selectedAgentId, data);
    }
  };

  return (
    <Modal title={isEdit ? 'Edit Subflow' : 'Add Subflow'} onClose={closeModal}>
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
          <label>Trigger Description</label>
          <textarea
            name="trigger_description"
            value={formData.trigger_description}
            onChange={handleChange}
            rows={2}
            placeholder="When the user wants to..."
          />
        </div>

        <div className="form-group">
          <label>Initial State</label>
          <input
            type="text"
            name="initial_state"
            value={formData.initial_state}
            onChange={handleChange}
            required
            placeholder="start"
          />
        </div>

        <div className="form-group">
          <label>Data Schema (JSON)</label>
          <textarea
            name="data_schema"
            value={formData.data_schema}
            onChange={handleChange}
            rows={4}
            placeholder='{"amount": {"type": "number"}, "recipient": {"type": "string"}}'
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={closeModal}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary">
            {isEdit ? 'Save Changes' : 'Add Subflow'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
