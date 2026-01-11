/**
 * Agent Management for Felix Admin
 */

const API_BASE = 'http://localhost:8000/api/admin';

// State
let agents = [];
let selectedAgentId = null;
let selectedAgent = null;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    loadAgents();

    // Toggle confirmation template visibility
    document.getElementById('toolRequiresConfirmation').addEventListener('change', (e) => {
        document.getElementById('confirmationTemplateGroup').style.display =
            e.target.checked ? 'block' : 'none';
    });
});

// ============================================================================
// API Functions
// ============================================================================

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options,
    };

    const response = await fetch(url, config);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null;
    }

    return response.json();
}

// ============================================================================
// Agent Tree
// ============================================================================

async function loadAgents() {
    try {
        agents = await apiRequest('/agents');
        renderAgentTree();
        populateParentSelects();
    } catch (error) {
        showToast('Failed to load agents: ' + error.message, 'error');
    }
}

function renderAgentTree() {
    const tree = document.getElementById('agentTree');

    if (agents.length === 0) {
        tree.innerHTML = '<div class="empty-list">No agents configured</div>';
        return;
    }

    // Build tree structure
    const rootAgents = agents.filter(a => !a.parent_agent_id);
    const childMap = {};

    agents.forEach(agent => {
        if (agent.parent_agent_id) {
            if (!childMap[agent.parent_agent_id]) {
                childMap[agent.parent_agent_id] = [];
            }
            childMap[agent.parent_agent_id].push(agent);
        }
    });

    function renderAgent(agent, level = 0) {
        const children = childMap[agent.id] || [];
        const isSelected = agent.id === selectedAgentId;

        let html = `
            <div class="agent-tree-item ${isSelected ? 'selected' : ''} ${!agent.is_active ? 'inactive' : ''}"
                 onclick="selectAgent('${agent.id}')"
                 style="margin-left: ${level * 16}px">
                <div class="agent-name">${escapeHtml(agent.name)}</div>
                <div class="agent-desc">${escapeHtml(agent.description)}</div>
            </div>
        `;

        children.forEach(child => {
            html += renderAgent(child, level + 1);
        });

        return html;
    }

    tree.innerHTML = rootAgents.map(a => renderAgent(a)).join('');
}

function populateParentSelects() {
    const selects = [
        document.getElementById('agentParent'),
        document.getElementById('newAgentParent'),
    ];

    selects.forEach(select => {
        if (!select) return;

        const currentValue = select.value;
        select.innerHTML = '<option value="">None (Root Agent)</option>';

        agents.forEach(agent => {
            // Don't allow selecting self or children as parent
            if (selectedAgentId && (agent.id === selectedAgentId)) return;

            const option = document.createElement('option');
            option.value = agent.id;
            option.textContent = agent.name;
            select.appendChild(option);
        });

        select.value = currentValue;
    });
}

// ============================================================================
// Agent Selection and Display
// ============================================================================

async function selectAgent(agentId) {
    try {
        selectedAgentId = agentId;
        selectedAgent = await apiRequest(`/agents/${agentId}`);

        // Update tree selection
        renderAgentTree();

        // Show detail view
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('agentDetail').style.display = 'block';

        // Populate form
        populateAgentForm();

        // Load related data
        renderTools();
        renderSubflows();
        renderTemplates();

        // Switch to general tab
        switchTab('general');

    } catch (error) {
        showToast('Failed to load agent: ' + error.message, 'error');
    }
}

function populateAgentForm() {
    document.getElementById('agentName').textContent = selectedAgent.name;

    const statusEl = document.getElementById('agentStatus');
    statusEl.textContent = selectedAgent.is_active ? 'Active' : 'Inactive';
    statusEl.className = `agent-status ${selectedAgent.is_active ? '' : 'inactive'}`;

    document.getElementById('agentNameInput').value = selectedAgent.name;
    document.getElementById('agentDescription').value = selectedAgent.description;
    document.getElementById('agentParent').value = selectedAgent.parent_agent_id || '';
    document.getElementById('agentSystemPrompt').value = selectedAgent.system_prompt_addition || '';
    document.getElementById('agentModelConfig').value = JSON.stringify(selectedAgent.model_config_json || {}, null, 2);
    document.getElementById('agentNavTools').value = JSON.stringify(selectedAgent.navigation_tools || {}, null, 2);
    document.getElementById('agentIsActive').checked = selectedAgent.is_active;

    populateParentSelects();
}

// ============================================================================
// Agent CRUD Operations
// ============================================================================

function showCreateAgentModal() {
    document.getElementById('agentModalTitle').textContent = 'Create Agent';
    document.getElementById('createAgentForm').reset();
    populateParentSelects();
    showModal('agentModal');
}

async function createAgent(event) {
    event.preventDefault();

    const data = {
        name: document.getElementById('newAgentName').value.trim(),
        description: document.getElementById('newAgentDescription').value.trim(),
        parent_agent_id: document.getElementById('newAgentParent').value || null,
        model_config_json: {},
        navigation_tools: {},
    };

    try {
        const newAgent = await apiRequest('/agents', {
            method: 'POST',
            body: JSON.stringify(data),
        });

        closeModal('agentModal');
        await loadAgents();
        selectAgent(newAgent.id);
        showToast('Agent created successfully', 'success');

    } catch (error) {
        showToast('Failed to create agent: ' + error.message, 'error');
    }
}

async function saveAgent(event) {
    event.preventDefault();

    if (!selectedAgentId) return;

    let modelConfig, navTools;

    try {
        modelConfig = JSON.parse(document.getElementById('agentModelConfig').value || '{}');
    } catch (e) {
        showToast('Invalid JSON in Model Configuration', 'error');
        return;
    }

    try {
        navTools = JSON.parse(document.getElementById('agentNavTools').value || '{}');
    } catch (e) {
        showToast('Invalid JSON in Navigation Tools', 'error');
        return;
    }

    const data = {
        name: document.getElementById('agentNameInput').value.trim(),
        description: document.getElementById('agentDescription').value.trim(),
        parent_agent_id: document.getElementById('agentParent').value || null,
        system_prompt_addition: document.getElementById('agentSystemPrompt').value.trim() || null,
        model_config_json: modelConfig,
        navigation_tools: navTools,
        is_active: document.getElementById('agentIsActive').checked,
    };

    try {
        await apiRequest(`/agents/${selectedAgentId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });

        await loadAgents();
        await selectAgent(selectedAgentId);
        showToast('Agent saved successfully', 'success');

    } catch (error) {
        showToast('Failed to save agent: ' + error.message, 'error');
    }
}

async function cloneAgent() {
    if (!selectedAgentId) return;

    try {
        const cloned = await apiRequest(`/agents/${selectedAgentId}/clone`, {
            method: 'POST',
        });

        await loadAgents();
        selectAgent(cloned.id);
        showToast('Agent cloned successfully', 'success');

    } catch (error) {
        showToast('Failed to clone agent: ' + error.message, 'error');
    }
}

function confirmDeleteAgent() {
    if (!selectedAgentId) return;

    document.getElementById('confirmMessage').textContent =
        `Are you sure you want to delete "${selectedAgent.name}"? This will also delete all tools, subflows, and templates.`;

    document.getElementById('confirmDeleteBtn').onclick = deleteAgent;
    showModal('confirmModal');
}

async function deleteAgent() {
    if (!selectedAgentId) return;

    try {
        await apiRequest(`/agents/${selectedAgentId}`, {
            method: 'DELETE',
        });

        closeModal('confirmModal');
        selectedAgentId = null;
        selectedAgent = null;

        document.getElementById('agentDetail').style.display = 'none';
        document.getElementById('emptyState').style.display = 'flex';

        await loadAgents();
        showToast('Agent deleted successfully', 'success');

    } catch (error) {
        showToast('Failed to delete agent: ' + error.message, 'error');
    }
}

// ============================================================================
// Tab Navigation
// ============================================================================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// ============================================================================
// Utility Functions
// ============================================================================

function showModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function parseJsonField(value, defaultValue = null) {
    if (!value || !value.trim()) return defaultValue;
    try {
        return JSON.parse(value);
    } catch (e) {
        return null;
    }
}
