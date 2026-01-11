import { useAdminStore } from '../../../store/adminStore';
import AgentTree from './AgentTree';

export default function Sidebar() {
  const showModal = useAdminStore((state) => state.showModal);

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>Felix Admin</h1>
        <button className="btn btn-primary" onClick={() => showModal('createAgent')}>
          + New Agent
        </button>
      </div>
      <AgentTree />
    </div>
  );
}
