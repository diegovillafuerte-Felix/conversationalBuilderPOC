// Felix Chat Client

const API_URL = 'http://localhost:8000/api/chat';
const USER_ID = 'user_demo';

let sessionId = null;
let pendingConfirmation = false;

// DOM Elements
const messagesContainer = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const sessionIdSpan = document.getElementById('sessionId');
const agentNameSpan = document.getElementById('agentName');
const confirmationButtons = document.getElementById('confirmationButtons');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    messageInput.focus();
});

// Handle key press
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Send message
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Add user message to chat
    addMessage(message, 'user');
    messageInput.value = '';

    // Disable input while processing
    setInputState(false);

    // Show typing indicator
    showTypingIndicator();

    try {
        const response = await fetch(`${API_URL}/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: USER_ID,
                message: message,
                session_id: sessionId,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update session info
        sessionId = data.session_id;
        sessionIdSpan.textContent = `Sesión: ${sessionId.substring(0, 8)}...`;
        agentNameSpan.textContent = data.agent_name;

        // Remove typing indicator
        removeTypingIndicator();

        // Add assistant response
        addMessage(data.message, 'assistant');

        // Handle pending confirmation
        if (data.pending_confirmation) {
            pendingConfirmation = true;
            confirmationButtons.style.display = 'flex';
        } else {
            pendingConfirmation = false;
            confirmationButtons.style.display = 'none';
        }

        // Check if escalated
        if (data.escalated) {
            addMessage('La conversación ha sido escalada a un agente humano.', 'system');
        }

    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator();
        addMessage('Lo siento, hubo un error al procesar tu mensaje. Por favor intenta de nuevo.', 'system');
    }

    // Re-enable input
    setInputState(true);
    messageInput.focus();
}

// Send confirmation
async function sendConfirmation(confirmed) {
    const message = confirmed ? 'Sí' : 'No';
    confirmationButtons.style.display = 'none';
    messageInput.value = message;
    await sendMessage();
}

// Add message to chat
function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'message assistant';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    messagesContainer.appendChild(indicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Set input state
function setInputState(enabled) {
    messageInput.disabled = !enabled;
    sendButton.disabled = !enabled;
}

// Reset session
function resetSession() {
    sessionId = null;
    pendingConfirmation = false;
    confirmationButtons.style.display = 'none';
    sessionIdSpan.textContent = 'Nueva sesión';
    agentNameSpan.textContent = 'Felix Assistant';

    // Clear messages except the first welcome message
    messagesContainer.innerHTML = `
        <div class="message assistant">
            <div class="message-content">
                ¡Hola! Soy Felix, tu asistente para enviar dinero, recargas y más. ¿En qué puedo ayudarte hoy?
            </div>
        </div>
    `;

    messageInput.focus();
}
