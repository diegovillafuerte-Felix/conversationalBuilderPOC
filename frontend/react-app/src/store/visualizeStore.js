import { create } from 'zustand';
import { adminApi, conversationApi } from '../services/adminApi';

export const useVisualizeStore = create((set, get) => ({
  // Data
  agents: [],
  selectedAgent: null,
  selectedSubflow: null,

  // UI state
  isLoading: false,
  error: null,
  activeView: 'hierarchy', // 'hierarchy' | 'flows' | 'tools' | 'conversations'
  conversations: [],
  selectedConversation: null,
  conversationEvents: [],
  isConversationLoading: false,

  // Detail panel
  detailPanel: null, // { type: 'agent' | 'state', data: {...} }

  // Actions
  loadAgents: async () => {
    set({ isLoading: true, error: null });
    try {
      const agents = await adminApi.getAgents();
      // Load full details for each agent
      const fullAgents = await Promise.all(
        agents.map(agent => adminApi.getAgent(agent.id))
      );
      set({ agents: fullAgents, isLoading: false });
    } catch (error) {
      set({ isLoading: false, error: error.message });
    }
  },

  setActiveView: (view) => {
    set({ activeView: view, detailPanel: null });
  },

  selectAgent: (agent) => {
    set({ selectedAgent: agent, selectedSubflow: null });
  },

  selectSubflow: (subflow) => {
    set({ selectedSubflow: subflow });
  },

  showDetailPanel: (type, data) => {
    set({ detailPanel: { type, data } });
  },

  hideDetailPanel: () => {
    set({ detailPanel: null });
  },

  loadConversations: async (params = {}) => {
    set({ isConversationLoading: true, error: null });
    try {
      const conversations = await conversationApi.listConversations(params);
      set({ conversations, isConversationLoading: false });
    } catch (error) {
      set({ isConversationLoading: false, error: error.message });
    }
  },

  openConversation: async (conversationId) => {
    set({ isConversationLoading: true, error: null });
    try {
      const [conversation, events] = await Promise.all([
        conversationApi.getConversation(conversationId),
        conversationApi.getConversationEvents(conversationId),
      ]);
      set({
        selectedConversation: conversation,
        conversationEvents: events.events || [],
        isConversationLoading: false,
      });
    } catch (error) {
      set({ isConversationLoading: false, error: error.message });
    }
  },

  clearConversationSelection: () => {
    set({ selectedConversation: null, conversationEvents: [] });
  },

  // Graph transformation utilities
  getHierarchyGraph: () => {
    const { agents } = get();
    const nodes = [];
    const edges = [];

    // Create nodes for each agent
    agents.forEach((agent) => {
      nodes.push({
        id: agent.id,
        type: 'agentNode',
        data: {
          label: agent.name,
          agent: agent,
          toolCount: agent.tools?.length || 0,
          subflowCount: agent.subflows?.length || 0,
          isActive: agent.is_active !== false,
        },
        position: { x: 0, y: 0 }, // Will be set by dagre
      });
    });

    // Create edges for parent-child relationships
    agents.forEach((agent) => {
      if (agent.parent_agent) {
        const parentAgent = agents.find(a => a.id === agent.parent_agent);
        if (parentAgent) {
          edges.push({
            id: `${parentAgent.id}-${agent.id}`,
            source: parentAgent.id,
            target: agent.id,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#6b7280', strokeWidth: 2 },
          });
        }
      }
    });

    // Add cross-agent routing edges (dashed)
    agents.forEach((agent) => {
      if (agent.tools) {
        agent.tools.forEach((tool) => {
          if (tool.routing?.cross_agent) {
            const targetAgent = agents.find(a => a.id === tool.routing.cross_agent);
            if (targetAgent) {
              edges.push({
                id: `routing-${agent.id}-${targetAgent.id}-${tool.name}`,
                source: agent.id,
                target: targetAgent.id,
                type: 'smoothstep',
                animated: true,
                style: { stroke: '#3b82f6', strokeWidth: 2, strokeDasharray: '5,5' },
                label: tool.name,
                labelStyle: { fontSize: 10, fill: '#6b7280' },
              });
            }
          }
        });
      }
    });

    return { nodes, edges };
  },

  getSubflowGraph: (subflow) => {
    if (!subflow || !subflow.states) return { nodes: [], edges: [] };

    const nodes = [];
    const edges = [];

    // Create nodes for each state
    subflow.states.forEach((state) => {
      const isInitial = state.id === subflow.initial_state;
      nodes.push({
        id: state.id,
        type: 'stateNode',
        data: {
          label: state.name || state.id,
          state: state,
          isInitial,
          isFinal: state.is_final === true,
          hasOnEnter: !!(state.on_enter?.callTool || state.on_enter?.message),
          stateToolsCount: state.state_tools?.length || 0,
        },
        position: { x: 0, y: 0 },
      });
    });

    // Create edges for transitions
    subflow.states.forEach((state) => {
      if (state.transitions) {
        state.transitions.forEach((transition, idx) => {
          edges.push({
            id: `${state.id}-${transition.target}-${idx}`,
            source: state.id,
            target: transition.target,
            type: 'smoothstep',
            label: transition.trigger,
            labelStyle: { fontSize: 10, fill: '#6b7280' },
            style: { stroke: '#6b7280', strokeWidth: 2 },
            markerEnd: { type: 'arrowclosed', color: '#6b7280' },
          });
        });
      }
    });

    return { nodes, edges };
  },
}));
