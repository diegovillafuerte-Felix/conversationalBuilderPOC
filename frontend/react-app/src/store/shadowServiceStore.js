import { create } from 'zustand';
import { shadowServiceApi } from '../services/shadowServiceApi';

export const useShadowServiceStore = create((set, get) => ({
  // State
  config: null,
  selectedSubagentId: null,
  selectedSubagent: null,
  isLoading: false,
  error: null,

  // Toast state
  toast: null,

  // Modal state
  openModal: null,
  modalData: null,

  // Actions
  loadConfig: async () => {
    set({ isLoading: true, error: null });
    try {
      const config = await shadowServiceApi.getConfig();
      set({ config, isLoading: false });
    } catch (error) {
      set({ isLoading: false, error: error.message });
      get().showToast('Failed to load shadow service config: ' + error.message, 'error');
    }
  },

  updateGlobalConfig: async (data) => {
    try {
      await shadowServiceApi.updateConfig(data);
      await get().loadConfig();
      get().showToast('Settings saved successfully', 'success');
    } catch (error) {
      get().showToast('Failed to save settings: ' + error.message, 'error');
      throw error;
    }
  },

  selectSubagent: (subagentId) => {
    const config = get().config;
    if (!config) return;

    const subagent = config.subagents?.find(s => s.id === subagentId);
    set({
      selectedSubagentId: subagentId,
      selectedSubagent: subagent || null,
    });
  },

  clearSelection: () => {
    set({ selectedSubagentId: null, selectedSubagent: null });
  },

  // Subagent CRUD
  updateSubagent: async (id, data) => {
    try {
      await shadowServiceApi.updateSubagent(id, data);
      await get().loadConfig();
      get().showToast('Subagent updated successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to update subagent: ' + error.message, 'error');
      throw error;
    }
  },

  createSubagent: async (data) => {
    try {
      await shadowServiceApi.createSubagent(data);
      await get().loadConfig();
      get().showToast('Subagent created successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to create subagent: ' + error.message, 'error');
      throw error;
    }
  },

  deleteSubagent: async (id) => {
    try {
      await shadowServiceApi.deleteSubagent(id);
      set({ selectedSubagentId: null, selectedSubagent: null });
      await get().loadConfig();
      get().showToast('Subagent deleted successfully', 'success');
      get().closeModal();
    } catch (error) {
      get().showToast('Failed to delete subagent: ' + error.message, 'error');
      throw error;
    }
  },

  // Toggle subagent enabled status
  toggleSubagent: async (id) => {
    const config = get().config;
    if (!config) return;

    const subagent = config.subagents?.find(s => s.id === id);
    if (!subagent) return;

    await get().updateSubagent(id, { ...subagent, enabled: !subagent.enabled });
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
