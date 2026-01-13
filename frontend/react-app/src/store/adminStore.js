import { create } from 'zustand';
import { adminApi } from '../services/adminApi';

export const useAdminStore = create((set, get) => ({
  agents: [],
  selectedAgentId: null,
  selectedAgent: null,
  activeTab: 'general',
  isLoading: false,
  error: null,

  // View state (agents or shadowService)
  currentView: 'agents',

  // Toast state
  toast: null,

  // Modal state
  openModal: null,
  modalData: null,

  // Actions
  loadAgents: async () => {
    set({ isLoading: true, error: null });
    try {
      const agents = await adminApi.getAgents();
      set({ agents, isLoading: false });
    } catch (error) {
      set({ isLoading: false, error: error.message });
      get().showToast('Failed to load agents: ' + error.message, 'error');
    }
  },

  selectAgent: async (agentId) => {
    set({ isLoading: true, error: null });
    try {
      const agent = await adminApi.getAgent(agentId);
      set({
        selectedAgentId: agentId,
        selectedAgent: agent,
        activeTab: 'general',
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false, error: error.message });
      get().showToast('Failed to load agent: ' + error.message, 'error');
    }
  },

  clearSelection: () => {
    set({ selectedAgentId: null, selectedAgent: null });
  },

  setActiveTab: (tab) => {
    set({ activeTab: tab });
  },

  setView: (view) => {
    set({ currentView: view });
  },

  // Agent CRUD
  createAgent: async (data) => {
    try {
      const newAgent = await adminApi.createAgent(data);
      await get().loadAgents();
      await get().selectAgent(newAgent.id);
      get().showToast('Agent created successfully', 'success');
      get().closeModal();
      return newAgent;
    } catch (error) {
      get().showToast('Failed to create agent: ' + error.message, 'error');
      throw error;
    }
  },

  updateAgent: async (id, data) => {
    try {
      await adminApi.updateAgent(id, data);
      await get().loadAgents();
      await get().selectAgent(id);
      get().showToast('Agent saved successfully', 'success');
    } catch (error) {
      get().showToast('Failed to save agent: ' + error.message, 'error');
      throw error;
    }
  },

  deleteAgent: async (id) => {
    try {
      await adminApi.deleteAgent(id);
      set({ selectedAgentId: null, selectedAgent: null });
      await get().loadAgents();
      get().showToast('Agent deleted successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to delete agent: ' + error.message, 'error');
      throw error;
    }
  },

  cloneAgent: async (id) => {
    try {
      const cloned = await adminApi.cloneAgent(id);
      await get().loadAgents();
      await get().selectAgent(cloned.id);
      get().showToast('Agent cloned successfully', 'success');
    } catch (error) {
      get().showToast('Failed to clone agent: ' + error.message, 'error');
      throw error;
    }
  },

  // Tool CRUD
  createTool: async (agentId, data) => {
    try {
      await adminApi.createTool(agentId, data);
      await get().selectAgent(agentId);
      get().showToast('Tool created successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to create tool: ' + error.message, 'error');
      throw error;
    }
  },

  updateTool: async (id, data) => {
    try {
      await adminApi.updateTool(id, data);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('Tool updated successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to update tool: ' + error.message, 'error');
      throw error;
    }
  },

  deleteTool: async (id) => {
    try {
      await adminApi.deleteTool(id);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('Tool deleted successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to delete tool: ' + error.message, 'error');
      throw error;
    }
  },

  // Subflow CRUD
  createSubflow: async (agentId, data) => {
    try {
      await adminApi.createSubflow(agentId, data);
      await get().selectAgent(agentId);
      get().showToast('Subflow created successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to create subflow: ' + error.message, 'error');
      throw error;
    }
  },

  updateSubflow: async (id, data) => {
    try {
      await adminApi.updateSubflow(id, data);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('Subflow updated successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to update subflow: ' + error.message, 'error');
      throw error;
    }
  },

  deleteSubflow: async (id) => {
    try {
      await adminApi.deleteSubflow(id);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('Subflow deleted successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to delete subflow: ' + error.message, 'error');
      throw error;
    }
  },

  // State CRUD
  createState: async (subflowId, data) => {
    try {
      await adminApi.createState(subflowId, data);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('State created successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to create state: ' + error.message, 'error');
      throw error;
    }
  },

  updateState: async (id, data) => {
    try {
      await adminApi.updateState(id, data);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('State updated successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to update state: ' + error.message, 'error');
      throw error;
    }
  },

  deleteState: async (id) => {
    try {
      await adminApi.deleteState(id);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('State deleted successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to delete state: ' + error.message, 'error');
      throw error;
    }
  },

  // Template CRUD
  createTemplate: async (agentId, data) => {
    try {
      await adminApi.createTemplate(agentId, data);
      await get().selectAgent(agentId);
      get().showToast('Template created successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to create template: ' + error.message, 'error');
      throw error;
    }
  },

  updateTemplate: async (id, data) => {
    try {
      await adminApi.updateTemplate(id, data);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('Template updated successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to update template: ' + error.message, 'error');
      throw error;
    }
  },

  deleteTemplate: async (id) => {
    try {
      await adminApi.deleteTemplate(id);
      await get().selectAgent(get().selectedAgentId);
      get().showToast('Template deleted successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to delete template: ' + error.message, 'error');
      throw error;
    }
  },

  // Modal actions
  showModal: (modalType, data = null) => {
    set({ openModal: modalType, modalData: data });
  },

  closeModal: () => {
    set({ openModal: null, modalData: null });
  },

  // Toast actions
  showToast: (message, type = 'info') => {
    set({ toast: { message, type } });
    setTimeout(() => {
      set({ toast: null });
    }, 3000);
  },
}));
