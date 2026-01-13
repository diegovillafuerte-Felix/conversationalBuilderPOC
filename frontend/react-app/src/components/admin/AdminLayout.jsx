import { useEffect } from 'react';
import { useAdminStore } from '../../store/adminStore';
import Sidebar from './Sidebar/Sidebar';
import AgentDetail from './AgentDetail/AgentDetail';
import ShadowServicePage from './ShadowService/ShadowServicePage';
import Toast from './Common/Toast';
import AgentModal from './Modals/AgentModal';
import ToolModal from './Modals/ToolModal';
import SubflowModal from './Modals/SubflowModal';
import StateModal from './Modals/StateModal';
import TemplateModal from './Modals/TemplateModal';
import ConfirmModal from './Modals/ConfirmModal';

export default function AdminLayout() {
  const loadAgents = useAdminStore((state) => state.loadAgents);
  const openModal = useAdminStore((state) => state.openModal);
  const currentView = useAdminStore((state) => state.currentView);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  return (
    <div className="admin-container">
      <Sidebar />
      <main className="main-content">
        {currentView === 'agents' && <AgentDetail />}
        {currentView === 'shadowService' && <ShadowServicePage />}
      </main>

      {/* Modals */}
      {openModal === 'createAgent' && <AgentModal />}
      {openModal === 'tool' && <ToolModal />}
      {openModal === 'subflow' && <SubflowModal />}
      {openModal === 'state' && <StateModal />}
      {openModal === 'template' && <TemplateModal />}
      {openModal === 'confirmDelete' && <ConfirmModal />}

      {/* Toast notifications */}
      <Toast />
    </div>
  );
}
