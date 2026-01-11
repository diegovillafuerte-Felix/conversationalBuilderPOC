import { useAdminStore } from '../../../store/adminStore';
import Modal from '../Common/Modal';

export default function ConfirmModal() {
  const modalData = useAdminStore((state) => state.modalData);
  const closeModal = useAdminStore((state) => state.closeModal);
  const deleteAgent = useAdminStore((state) => state.deleteAgent);
  const deleteTool = useAdminStore((state) => state.deleteTool);
  const deleteSubflow = useAdminStore((state) => state.deleteSubflow);
  const deleteState = useAdminStore((state) => state.deleteState);
  const deleteTemplate = useAdminStore((state) => state.deleteTemplate);

  const { type, id, name } = modalData || {};

  const handleConfirm = async () => {
    switch (type) {
      case 'agent':
        await deleteAgent(id);
        break;
      case 'tool':
        await deleteTool(id);
        break;
      case 'subflow':
        await deleteSubflow(id);
        break;
      case 'state':
        await deleteState(id);
        break;
      case 'template':
        await deleteTemplate(id);
        break;
    }
  };

  const getMessage = () => {
    switch (type) {
      case 'agent':
        return `Are you sure you want to delete "${name}"? This will also delete all tools, subflows, and templates.`;
      case 'subflow':
        return `Are you sure you want to delete the subflow "${name}"? This will also delete all its states.`;
      default:
        return `Are you sure you want to delete "${name}"?`;
    }
  };

  return (
    <Modal title="Confirm Delete" onClose={closeModal} size="small">
      <p style={{ marginBottom: '20px' }}>{getMessage()}</p>
      <div className="form-actions">
        <button className="btn btn-secondary" onClick={closeModal}>
          Cancel
        </button>
        <button className="btn btn-danger" onClick={handleConfirm}>
          Delete
        </button>
      </div>
    </Modal>
  );
}
