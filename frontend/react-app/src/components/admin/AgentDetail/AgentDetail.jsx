import { useAdminStore } from '../../../store/adminStore';
import GeneralTab from './GeneralTab';
import ToolsTab from './ToolsTab';
import SubflowsTab from './SubflowsTab';
import TemplatesTab from './TemplatesTab';

const TABS = [
  { id: 'general', label: 'General' },
  { id: 'tools', label: 'Tools' },
  { id: 'subflows', label: 'Subflows' },
  { id: 'templates', label: 'Templates' },
];

export default function AgentDetail() {
  const selectedAgent = useAdminStore((state) => state.selectedAgent);
  const activeTab = useAdminStore((state) => state.activeTab);
  const setActiveTab = useAdminStore((state) => state.setActiveTab);
  const cloneAgent = useAdminStore((state) => state.cloneAgent);
  const showModal = useAdminStore((state) => state.showModal);

  if (!selectedAgent) {
    return (
      <div className="empty-state">
        <h2>No Agent Selected</h2>
        <p>Select an agent from the sidebar or create a new one</p>
      </div>
    );
  }

  return (
    <div className="agent-detail">
      <div className="detail-header">
        <div className="header-info">
          <h2>{selectedAgent.name}</h2>
          <span className={`agent-status ${!selectedAgent.is_active ? 'inactive' : ''}`}>
            {selectedAgent.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => cloneAgent(selectedAgent.id)}>
            Clone
          </button>
          <button
            className="btn btn-danger"
            onClick={() => showModal('confirmDelete', { type: 'agent', id: selectedAgent.id, name: selectedAgent.name })}
          >
            Delete
          </button>
        </div>
      </div>

      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className={`tab-content ${activeTab === 'general' ? 'active' : ''}`}>
        {activeTab === 'general' && <GeneralTab />}
      </div>
      <div className={`tab-content ${activeTab === 'tools' ? 'active' : ''}`}>
        {activeTab === 'tools' && <ToolsTab />}
      </div>
      <div className={`tab-content ${activeTab === 'subflows' ? 'active' : ''}`}>
        {activeTab === 'subflows' && <SubflowsTab />}
      </div>
      <div className={`tab-content ${activeTab === 'templates' ? 'active' : ''}`}>
        {activeTab === 'templates' && <TemplatesTab />}
      </div>
    </div>
  );
}
