import { useState, useEffect } from 'react';
import { useAdminStore } from '../../../store/adminStore';
import Modal from '../Common/Modal';

export default function StateModal() {
  const modalData = useAdminStore((state) => state.modalData);
  const createState = useAdminStore((state) => state.createState);
  const updateState = useAdminStore((state) => state.updateState);
  const closeModal = useAdminStore((state) => state.closeModal);

  const isEdit = !!modalData?.state?.id;
  const subflowId = modalData?.subflowId;

  const [formData, setFormData] = useState({
    state_id: '',
    name: '',
    agent_instructions: '',
    transitions: '',
    on_enter: '',
    is_final: false,
  });

  useEffect(() => {
    if (modalData?.state) {
      const state = modalData.state;
      setFormData({
        state_id: state.state_id || '',
        name: state.name || '',
        agent_instructions: state.agent_instructions || '',
        transitions: state.transitions ? JSON.stringify(state.transitions, null, 2) : '',
        on_enter: state.on_enter ? JSON.stringify(state.on_enter, null, 2) : '',
        is_final: state.is_final || false,
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

    const transitions = parseJson(formData.transitions);
    const onEnter = parseJson(formData.on_enter);

    if (formData.transitions && transitions === null) {
      alert('Invalid JSON in Transitions');
      return;
    }
    if (formData.on_enter && onEnter === null) {
      alert('Invalid JSON in On Enter Actions');
      return;
    }

    const data = {
      state_id: formData.state_id.trim(),
      name: formData.name.trim(),
      agent_instructions: formData.agent_instructions.trim(),
      transitions,
      on_enter: onEnter,
      is_final: formData.is_final,
    };

    if (isEdit) {
      await updateState(modalData.state.id, data);
    } else {
      await createState(subflowId, data);
    }
  };

  return (
    <Modal title={isEdit ? 'Edit State' : 'Add State'} onClose={closeModal} size="large">
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>State ID</label>
            <input
              type="text"
              name="state_id"
              value={formData.state_id}
              onChange={handleChange}
              required
              placeholder="collect_amount"
            />
          </div>
          <div className="form-group">
            <label>Display Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="Collect Amount"
            />
          </div>
        </div>

        <div className="form-group">
          <label>Agent Instructions</label>
          <textarea
            name="agent_instructions"
            value={formData.agent_instructions}
            onChange={handleChange}
            rows={4}
            placeholder="Ask the user for the amount they want to send..."
          />
        </div>

        <div className="form-group">
          <label>Transitions (JSON)</label>
          <textarea
            name="transitions"
            value={formData.transitions}
            onChange={handleChange}
            rows={4}
            placeholder='[{"trigger": "amount_provided", "target_state": "confirm"}]'
          />
        </div>

        <div className="form-group">
          <label>On Enter Actions (JSON)</label>
          <textarea
            name="on_enter"
            value={formData.on_enter}
            onChange={handleChange}
            rows={3}
            placeholder='[{"action": "call_tool", "tool": "get_exchange_rate"}]'
          />
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              name="is_final"
              checked={formData.is_final}
              onChange={handleChange}
            />
            Final State
          </label>
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={closeModal}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary">
            {isEdit ? 'Save Changes' : 'Add State'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
