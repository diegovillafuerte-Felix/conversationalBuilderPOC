import { create } from 'zustand';
import { chatApi } from '../services/chatApi';

const WELCOME_MESSAGE = {
  id: 'welcome',
  content: '¡Hola! Soy Felix, tu asistente para enviar dinero, recargas y más. ¿En qué puedo ayudarte hoy?',
  type: 'assistant',
  timestamp: new Date().toISOString(),
};

export const useChatStore = create((set, get) => ({
  messages: [WELCOME_MESSAGE],
  debugEvents: [], // Store all debug events for the debug panel
  sessionId: null,
  userId: 'user_demo',
  agentName: 'Felix Assistant',
  pendingConfirmation: null,
  confirmationExpiresAt: null,
  isLoading: false,
  error: null,

  addMessage: (content, type, debugInfo = null, agentName = null) => {
    const message = {
      id: Date.now().toString(),
      content,
      type,
      timestamp: new Date().toISOString(),
    };
    set((state) => ({
      messages: [...state.messages, message],
    }));

    // If debug info provided, add to debug events
    if (debugInfo) {
      get().addDebugEvent({
        type: 'assistant_response',
        content,
        debug: debugInfo,
        agentName: agentName,
      });
    }
  },

  addDebugEvent: (event) => {
    const debugEvent = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      ...event,
    };
    set((state) => ({
      debugEvents: [...state.debugEvents, debugEvent],
    }));
  },

  sendMessage: async (text) => {
    const { userId, sessionId, addMessage, addDebugEvent } = get();

    addMessage(text, 'user');
    addDebugEvent({
      type: 'user_message',
      content: text,
    });
    set({ isLoading: true, error: null });

    try {
      const data = await chatApi.sendMessage(userId, text, sessionId);

      // Add debug event for tool calls
      if (data.tool_calls && data.tool_calls.length > 0) {
        data.tool_calls.forEach((tc) => {
          addDebugEvent({
            type: 'tool_call',
            toolName: tc.tool_name,
            parameters: tc.parameters,
            result: tc.result,
            requiresConfirmation: tc.requires_confirmation,
          });
        });
      }

      set({
        sessionId: data.session_id,
        agentName: data.agent_name,
        pendingConfirmation: data.pending_confirmation,
        confirmationExpiresAt: data.pending_confirmation?.expiresAt || null,
        isLoading: false,
      });

      // Add message with debug info and agent name
      addMessage(data.message, 'assistant', data.debug, data.agent_name);

      if (data.escalated) {
        addMessage('La conversación ha sido escalada a un agente humano.', 'system');
        addDebugEvent({
          type: 'escalation',
          message: 'Conversation escalated to human agent',
        });
      }

      return data;
    } catch (error) {
      console.error('Error sending message:', error);
      set({ isLoading: false, error: error.message });
      addMessage('Lo siento, hubo un error al procesar tu mensaje. Por favor intenta de nuevo.', 'system');
      addDebugEvent({
        type: 'error',
        error: error.message,
      });
      throw error;
    }
  },

  sendConfirmation: async (confirmed) => {
    const message = confirmed ? 'Sí' : 'No';
    set({ pendingConfirmation: null, confirmationExpiresAt: null });
    return get().sendMessage(message);
  },

  resetSession: async () => {
    const { sessionId } = get();

    if (sessionId) {
      try {
        await chatApi.endSession(sessionId);
      } catch (error) {
        console.error('Failed to end session:', error);
      }
    }

    set({
      messages: [WELCOME_MESSAGE],
      debugEvents: [],
      sessionId: null,
      agentName: 'Felix Assistant',
      pendingConfirmation: null,
      confirmationExpiresAt: null,
      isLoading: false,
      error: null,
    });
  },

  setUserId: (userId) => {
    set({ userId });
  },

  clearConfirmation: () => {
    set({ pendingConfirmation: null, confirmationExpiresAt: null });
  },
}));
