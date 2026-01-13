import { useAdminStore } from '../../../store/adminStore';
import AgentTree from './AgentTree';

export default function Sidebar() {
  const showModal = useAdminStore((state) => state.showModal);
  const currentView = useAdminStore((state) => state.currentView);
  const setView = useAdminStore((state) => state.setView);

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>Felix Admin</h1>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <button
          className={`nav-item ${currentView === 'agents' ? 'active' : ''}`}
          onClick={() => setView('agents')}
        >
          Agents
        </button>
        <button
          className={`nav-item ${currentView === 'shadowService' ? 'active' : ''}`}
          onClick={() => setView('shadowService')}
        >
          Shadow Service
        </button>
      </nav>

      {/* Agents Section */}
      {currentView === 'agents' && (
        <>
          <div className="sidebar-section-header">
            <button className="btn btn-primary btn-small" onClick={() => showModal('createAgent')}>
              + New Agent
            </button>
          </div>
          <AgentTree />
        </>
      )}

      {/* Shadow Service Section */}
      {currentView === 'shadowService' && (
        <div className="sidebar-section-info">
          <p>Configure shadow subagents that provide contextual tips and promotions.</p>
        </div>
      )}
    </div>
  );
}
