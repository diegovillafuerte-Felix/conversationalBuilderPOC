/**
 * Subflow and State Management for Felix Admin
 */

// ============================================================================
// Subflow Rendering
// ============================================================================

function renderSubflows() {
    const container = document.getElementById('subflowsList');
    const subflows = selectedAgent.subflows || [];

    if (subflows.length === 0) {
        container.innerHTML = '<div class="empty-list">No subflows configured</div>';
        return;
    }

    container.innerHTML = subflows.map(subflow => `
        <div class="list-item">
            <div class="list-item-header">
                <div class="list-item-title">${escapeHtml(subflow.name)}</div>
                <div class="list-item-actions">
                    <button class="btn btn-secondary btn-small" onclick="editSubflow('${subflow.id}')">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="confirmDeleteSubflow('${subflow.id}', '${escapeHtml(subflow.name)}')">Delete</button>
                </div>
            </div>
            <div class="list-item-desc">${escapeHtml(subflow.trigger_description)}</div>
            <div class="list-item-meta">
                <span>Initial State: <code>${escapeHtml(subflow.initial_state)}</code></span>
                <span>${subflow.states.length} state(s)</span>
            </div>
            ${renderSubflowStates(subflow)}
        </div>
    `).join('');
}

function renderSubflowStates(subflow) {
    if (!subflow.states || subflow.states.length === 0) {
        return `
            <div class="subflow-states">
                <div class="subflow-states-header">
                    <h4>States</h4>
                    <button class="btn btn-secondary btn-small" onclick="showStateModal('${subflow.id}')">+ Add State</button>
                </div>
                <div class="empty-list" style="padding: 16px;">No states defined</div>
            </div>
        `;
    }

    return `
        <div class="subflow-states">
            <div class="subflow-states-header">
                <h4>States</h4>
                <button class="btn btn-secondary btn-small" onclick="showStateModal('${subflow.id}')">+ Add State</button>
            </div>
            ${subflow.states.map(state => `
                <div class="state-item ${state.is_final ? 'final' : ''}">
                    <div class="state-info">
                        <strong>${escapeHtml(state.name)}</strong>
                        <span class="state-id">(${escapeHtml(state.state_id)})</span>
                        ${state.is_final ? '<span class="badge">Final</span>' : ''}
                    </div>
                    <div class="list-item-actions">
                        <button class="btn btn-secondary btn-small" onclick="editState('${subflow.id}', '${state.id}')">Edit</button>
                        <button class="btn btn-danger btn-small" onclick="confirmDeleteState('${state.id}', '${escapeHtml(state.name)}')">Delete</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

// ============================================================================
// Subflow Modal
// ============================================================================

function showSubflowModal(subflowId = null) {
    const isEdit = !!subflowId;
    document.getElementById('subflowModalTitle').textContent = isEdit ? 'Edit Subflow' : 'Add Subflow';
    document.getElementById('subflowForm').reset();
    document.getElementById('subflowId').value = '';

    if (isEdit) {
        const subflow = selectedAgent.subflows.find(s => s.id === subflowId);
        if (subflow) {
            document.getElementById('subflowId').value = subflow.id;
            document.getElementById('subflowName').value = subflow.name;
            document.getElementById('subflowTrigger').value = subflow.trigger_description;
            document.getElementById('subflowInitialState').value = subflow.initial_state;
            document.getElementById('subflowDataSchema').value = subflow.data_schema ? JSON.stringify(subflow.data_schema, null, 2) : '';
        }
    }

    showModal('subflowModal');
}

function editSubflow(subflowId) {
    showSubflowModal(subflowId);
}

async function saveSubflow(event) {
    event.preventDefault();

    const subflowId = document.getElementById('subflowId').value;
    const isEdit = !!subflowId;

    let dataSchema = parseJsonField(document.getElementById('subflowDataSchema').value);
    if (document.getElementById('subflowDataSchema').value && dataSchema === null) {
        showToast('Invalid JSON in Data Schema', 'error');
        return;
    }

    const data = {
        name: document.getElementById('subflowName').value.trim(),
        trigger_description: document.getElementById('subflowTrigger').value.trim(),
        initial_state: document.getElementById('subflowInitialState').value.trim(),
        data_schema: dataSchema,
    };

    try {
        if (isEdit) {
            await apiRequest(`/subflows/${subflowId}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        } else {
            await apiRequest(`/agents/${selectedAgentId}/subflows`, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        }

        closeModal('subflowModal');
        await selectAgent(selectedAgentId);
        showToast(`Subflow ${isEdit ? 'updated' : 'created'} successfully`, 'success');

    } catch (error) {
        showToast(`Failed to ${isEdit ? 'update' : 'create'} subflow: ` + error.message, 'error');
    }
}

function confirmDeleteSubflow(subflowId, subflowName) {
    document.getElementById('confirmMessage').textContent =
        `Are you sure you want to delete the subflow "${subflowName}"? This will also delete all its states.`;

    document.getElementById('confirmDeleteBtn').onclick = () => deleteSubflow(subflowId);
    showModal('confirmModal');
}

async function deleteSubflow(subflowId) {
    try {
        await apiRequest(`/subflows/${subflowId}`, {
            method: 'DELETE',
        });

        closeModal('confirmModal');
        await selectAgent(selectedAgentId);
        showToast('Subflow deleted successfully', 'success');

    } catch (error) {
        showToast('Failed to delete subflow: ' + error.message, 'error');
    }
}

// ============================================================================
// State Modal
// ============================================================================

function showStateModal(subflowId, stateId = null) {
    const isEdit = !!stateId;
    document.getElementById('stateModalTitle').textContent = isEdit ? 'Edit State' : 'Add State';
    document.getElementById('stateForm').reset();
    document.getElementById('stateDbId').value = '';
    document.getElementById('stateSubflowId').value = subflowId;

    if (isEdit) {
        const subflow = selectedAgent.subflows.find(s => s.id === subflowId);
        const state = subflow?.states.find(st => st.id === stateId);
        if (state) {
            document.getElementById('stateDbId').value = state.id;
            document.getElementById('stateId').value = state.state_id;
            document.getElementById('stateName').value = state.name;
            document.getElementById('stateInstructions').value = state.agent_instructions;
            document.getElementById('stateTransitions').value = state.transitions ? JSON.stringify(state.transitions, null, 2) : '';
            document.getElementById('stateOnEnter').value = state.on_enter ? JSON.stringify(state.on_enter, null, 2) : '';
            document.getElementById('stateIsFinal').checked = state.is_final;
        }
    }

    showModal('stateModal');
}

function editState(subflowId, stateId) {
    showStateModal(subflowId, stateId);
}

async function saveState(event) {
    event.preventDefault();

    const stateDbId = document.getElementById('stateDbId').value;
    const subflowId = document.getElementById('stateSubflowId').value;
    const isEdit = !!stateDbId;

    let transitions = parseJsonField(document.getElementById('stateTransitions').value);
    let onEnter = parseJsonField(document.getElementById('stateOnEnter').value);

    if (document.getElementById('stateTransitions').value && transitions === null) {
        showToast('Invalid JSON in Transitions', 'error');
        return;
    }
    if (document.getElementById('stateOnEnter').value && onEnter === null) {
        showToast('Invalid JSON in On Enter Actions', 'error');
        return;
    }

    const data = {
        state_id: document.getElementById('stateId').value.trim(),
        name: document.getElementById('stateName').value.trim(),
        agent_instructions: document.getElementById('stateInstructions').value.trim(),
        transitions: transitions,
        on_enter: onEnter,
        is_final: document.getElementById('stateIsFinal').checked,
    };

    try {
        if (isEdit) {
            await apiRequest(`/states/${stateDbId}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        } else {
            await apiRequest(`/subflows/${subflowId}/states`, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        }

        closeModal('stateModal');
        await selectAgent(selectedAgentId);
        showToast(`State ${isEdit ? 'updated' : 'created'} successfully`, 'success');

    } catch (error) {
        showToast(`Failed to ${isEdit ? 'update' : 'create'} state: ` + error.message, 'error');
    }
}

function confirmDeleteState(stateId, stateName) {
    document.getElementById('confirmMessage').textContent =
        `Are you sure you want to delete the state "${stateName}"?`;

    document.getElementById('confirmDeleteBtn').onclick = () => deleteState(stateId);
    showModal('confirmModal');
}

async function deleteState(stateId) {
    try {
        await apiRequest(`/states/${stateId}`, {
            method: 'DELETE',
        });

        closeModal('confirmModal');
        await selectAgent(selectedAgentId);
        showToast('State deleted successfully', 'success');

    } catch (error) {
        showToast('Failed to delete state: ' + error.message, 'error');
    }
}
