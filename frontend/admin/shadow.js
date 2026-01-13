// Shadow Service Admin JavaScript

let shadowConfig = null;
let currentView = 'agents';

// ============================================================================
// View Switching
// ============================================================================

function switchView(view) {
    currentView = view;

    // Update nav buttons
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });

    // Toggle sidebar content
    document.getElementById('agentsViewSidebar').style.display = view === 'agents' ? 'block' : 'none';
    document.getElementById('shadowViewSidebar').style.display = view === 'shadow' ? 'block' : 'none';

    // Toggle main content
    document.getElementById('emptyState').style.display = view === 'agents' && !selectedAgentId ? 'flex' : 'none';
    document.getElementById('agentDetail').style.display = view === 'agents' && selectedAgentId ? 'block' : 'none';
    document.getElementById('shadowServiceView').style.display = view === 'shadow' ? 'block' : 'none';

    // Load shadow config if switching to shadow view
    if (view === 'shadow' && !shadowConfig) {
        loadShadowConfig();
    }
}

// ============================================================================
// Shadow Service API
// ============================================================================

async function loadShadowConfig() {
    try {
        const response = await apiRequest('/shadow-service');
        shadowConfig = response;
        renderShadowConfig();
    } catch (error) {
        showToast('Failed to load shadow service config: ' + error.message, 'error');
    }
}

async function saveShadowGlobalSettings(event) {
    event.preventDefault();

    const config = {
        enabled: document.getElementById('shadowEnabled').checked,
        global_cooldown_messages: parseInt(document.getElementById('shadowCooldown').value),
        max_messages_per_response: parseInt(document.getElementById('shadowMaxMessages').value),
    };

    try {
        await apiRequest('/shadow-service', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
        await loadShadowConfig();
        showToast('Settings saved successfully', 'success');
    } catch (error) {
        showToast('Failed to save settings: ' + error.message, 'error');
    }
}

// ============================================================================
// Render Functions
// ============================================================================

function renderShadowConfig() {
    if (!shadowConfig) return;

    // Update global settings
    document.getElementById('shadowEnabled').checked = shadowConfig.enabled ?? true;
    document.getElementById('shadowCooldown').value = shadowConfig.global_cooldown_messages ?? 3;
    document.getElementById('shadowMaxMessages').value = shadowConfig.max_messages_per_response ?? 1;

    // Render subagents
    renderSubagentsGrid();
}

function renderSubagentsGrid() {
    const grid = document.getElementById('subagentsGrid');
    const subagents = shadowConfig?.subagents || [];

    if (subagents.length === 0) {
        grid.innerHTML = `
            <div class="empty-list">
                No shadow subagents configured.
                <br><br>
                <button class="btn btn-primary" onclick="showSubagentModal()">Create First Subagent</button>
            </div>
        `;
        return;
    }

    grid.innerHTML = subagents.map(subagent => `
        <div class="subagent-card ${!subagent.enabled ? 'disabled' : ''}" onclick="showSubagentModal('${subagent.id}')">
            <div class="subagent-card-header">
                <div class="subagent-card-title">
                    <h4>${getSourceLabel(subagent)}</h4>
                    <span class="badge ${subagent.enabled ? '' : 'warning'}">${subagent.enabled ? 'Active' : 'Disabled'}</span>
                </div>
                <label class="toggle-switch" onclick="event.stopPropagation()">
                    <input type="checkbox" ${subagent.enabled ? 'checked' : ''} onchange="toggleSubagent('${subagent.id}')">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            <div class="subagent-card-body">
                <div class="subagent-stat">
                    <span class="stat-label">Threshold</span>
                    <span class="stat-value">${subagent.relevance_threshold}%</span>
                </div>
                <div class="subagent-stat">
                    <span class="stat-label">Priority</span>
                    <span class="stat-value">${subagent.priority}</span>
                </div>
                <div class="subagent-stat">
                    <span class="stat-label">Cooldown</span>
                    <span class="stat-value">${subagent.cooldown_messages} msgs</span>
                </div>
                <div class="subagent-stat">
                    <span class="stat-label">Max Length</span>
                    <span class="stat-value">${subagent.max_tip_length} chars</span>
                </div>
            </div>
            ${subagent.active_campaigns && subagent.active_campaigns.length > 0 ? `
                <div class="subagent-card-footer">
                    <span class="campaigns-count">${subagent.active_campaigns.length} active campaign${subagent.active_campaigns.length !== 1 ? 's' : ''}</span>
                </div>
            ` : ''}
            ${subagent.full_agent_id ? `
                <div class="subagent-card-footer">
                    <span class="linked-agent">Links to: ${subagent.full_agent_id}</span>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function getSourceLabel(subagent) {
    if (typeof subagent.source_label === 'object') {
        return subagent.source_label.en || subagent.source_label.es || subagent.id;
    }
    return subagent.source_label || subagent.id;
}

// ============================================================================
// Subagent CRUD
// ============================================================================

async function toggleSubagent(id) {
    const subagent = shadowConfig.subagents.find(s => s.id === id);
    if (!subagent) return;

    const updated = { ...subagent, enabled: !subagent.enabled };

    try {
        await apiRequest(`/shadow-service/subagents/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updated),
        });
        await loadShadowConfig();
        showToast(`Subagent ${updated.enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch (error) {
        showToast('Failed to toggle subagent: ' + error.message, 'error');
    }
}

function showSubagentModal(subagentId = null) {
    const modal = document.getElementById('subagentModal');
    const form = document.getElementById('subagentForm');
    const title = document.getElementById('subagentModalTitle');
    const deleteBtn = document.getElementById('deleteSubagentBtn');

    form.reset();

    if (subagentId) {
        // Edit mode
        const subagent = shadowConfig.subagents.find(s => s.id === subagentId);
        if (!subagent) return;

        title.textContent = `Edit Subagent: ${subagentId}`;
        deleteBtn.style.display = 'block';
        document.getElementById('subagentOriginalId').value = subagentId;
        document.getElementById('subagentId').value = subagent.id;
        document.getElementById('subagentId').disabled = true;
        document.getElementById('subagentEnabled').checked = subagent.enabled ?? true;
        document.getElementById('subagentSourceLabelEn').value = subagent.source_label?.en || '';
        document.getElementById('subagentSourceLabelEs').value = subagent.source_label?.es || '';
        document.getElementById('subagentThreshold').value = subagent.relevance_threshold ?? 80;
        document.getElementById('subagentPriority').value = subagent.priority ?? 1;
        document.getElementById('subagentModel').value = subagent.model || 'claude-3-haiku-20240307';
        document.getElementById('subagentTemperature').value = subagent.temperature ?? 0.3;
        document.getElementById('subagentCooldown').value = subagent.cooldown_messages ?? 5;
        document.getElementById('subagentMaxLength').value = subagent.max_tip_length ?? 280;
        document.getElementById('subagentLinkedAgent').value = subagent.full_agent_id || '';
        document.getElementById('subagentToneEn').value = subagent.tone?.en || '';
        document.getElementById('subagentToneEs').value = subagent.tone?.es || '';
        document.getElementById('subagentPromptEn').value = subagent.system_prompt_addition?.en || '';
        document.getElementById('subagentPromptEs').value = subagent.system_prompt_addition?.es || '';
        document.getElementById('subagentIntents').value = (subagent.activation_intents || []).join(', ');
    } else {
        // Create mode
        title.textContent = 'Create Subagent';
        deleteBtn.style.display = 'none';
        document.getElementById('subagentOriginalId').value = '';
        document.getElementById('subagentId').disabled = false;
    }

    showModal('subagentModal');
}

async function saveSubagent(event) {
    event.preventDefault();

    const originalId = document.getElementById('subagentOriginalId').value;
    const isEdit = !!originalId;

    const subagentConfig = {
        id: document.getElementById('subagentId').value,
        enabled: document.getElementById('subagentEnabled').checked,
        source_label: {
            en: document.getElementById('subagentSourceLabelEn').value,
            es: document.getElementById('subagentSourceLabelEs').value,
        },
        relevance_threshold: parseInt(document.getElementById('subagentThreshold').value),
        priority: parseInt(document.getElementById('subagentPriority').value),
        model: document.getElementById('subagentModel').value,
        temperature: parseFloat(document.getElementById('subagentTemperature').value),
        cooldown_messages: parseInt(document.getElementById('subagentCooldown').value),
        max_tip_length: parseInt(document.getElementById('subagentMaxLength').value),
        full_agent_id: document.getElementById('subagentLinkedAgent').value || null,
        tone: {
            en: document.getElementById('subagentToneEn').value,
            es: document.getElementById('subagentToneEs').value,
        },
        system_prompt_addition: {
            en: document.getElementById('subagentPromptEn').value,
            es: document.getElementById('subagentPromptEs').value,
        },
        activation_intents: document.getElementById('subagentIntents').value
            ? document.getElementById('subagentIntents').value.split(',').map(s => s.trim()).filter(Boolean)
            : [],
    };

    try {
        if (isEdit) {
            await apiRequest(`/shadow-service/subagents/${originalId}`, {
                method: 'PUT',
                body: JSON.stringify(subagentConfig),
            });
            showToast('Subagent updated successfully', 'success');
        } else {
            await apiRequest('/shadow-service/subagents', {
                method: 'POST',
                body: JSON.stringify(subagentConfig),
            });
            showToast('Subagent created successfully', 'success');
        }
        closeModal('subagentModal');
        await loadShadowConfig();
    } catch (error) {
        showToast('Failed to save subagent: ' + error.message, 'error');
    }
}

async function deleteSubagent() {
    const id = document.getElementById('subagentOriginalId').value;
    if (!id) return;

    if (!confirm(`Are you sure you want to delete subagent "${id}"?`)) {
        return;
    }

    try {
        await apiRequest(`/shadow-service/subagents/${id}`, {
            method: 'DELETE',
        });
        showToast('Subagent deleted successfully', 'success');
        closeModal('subagentModal');
        await loadShadowConfig();
    } catch (error) {
        showToast('Failed to delete subagent: ' + error.message, 'error');
    }
}
