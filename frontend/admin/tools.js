/**
 * Tool Management for Felix Admin
 */

// ============================================================================
// Tool Rendering
// ============================================================================

function renderTools() {
    const container = document.getElementById('toolsList');
    const tools = selectedAgent.tools || [];

    if (tools.length === 0) {
        container.innerHTML = '<div class="empty-list">No tools configured</div>';
        return;
    }

    container.innerHTML = tools.map(tool => `
        <div class="list-item">
            <div class="list-item-header">
                <div class="list-item-title">${escapeHtml(tool.name)}</div>
                <div class="list-item-actions">
                    <button class="btn btn-secondary btn-small" onclick="editTool('${tool.id}')">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="confirmDeleteTool('${tool.id}', '${escapeHtml(tool.name)}')">Delete</button>
                </div>
            </div>
            <div class="list-item-desc">${escapeHtml(tool.description)}</div>
            <div class="list-item-meta">
                <span>Side Effects: <span class="badge ${tool.side_effects === 'financial' ? 'danger' : tool.side_effects === 'write' ? 'warning' : ''}">${tool.side_effects}</span></span>
                ${tool.requires_confirmation ? '<span class="badge warning">Requires Confirmation</span>' : ''}
                ${tool.flow_transition ? '<span class="badge">Has Flow Transition</span>' : ''}
            </div>
        </div>
    `).join('');
}

// ============================================================================
// Tool Modal
// ============================================================================

function showToolModal(toolId = null) {
    const isEdit = !!toolId;
    document.getElementById('toolModalTitle').textContent = isEdit ? 'Edit Tool' : 'Add Tool';
    document.getElementById('toolForm').reset();
    document.getElementById('toolId').value = '';
    document.getElementById('confirmationTemplateGroup').style.display = 'none';

    if (isEdit) {
        const tool = selectedAgent.tools.find(t => t.id === toolId);
        if (tool) {
            document.getElementById('toolId').value = tool.id;
            document.getElementById('toolName').value = tool.name;
            document.getElementById('toolDescription').value = tool.description;
            document.getElementById('toolSideEffects').value = tool.side_effects;
            document.getElementById('toolParameters').value = tool.parameters ? JSON.stringify(tool.parameters, null, 2) : '';
            document.getElementById('toolApiConfig').value = tool.api_config ? JSON.stringify(tool.api_config, null, 2) : '';
            document.getElementById('toolRequiresConfirmation').checked = tool.requires_confirmation;
            document.getElementById('toolConfirmationTemplate').value = tool.confirmation_template || '';
            document.getElementById('toolFlowTransition').value = tool.flow_transition ? JSON.stringify(tool.flow_transition, null, 2) : '';

            if (tool.requires_confirmation) {
                document.getElementById('confirmationTemplateGroup').style.display = 'block';
            }
        }
    }

    showModal('toolModal');
}

function editTool(toolId) {
    showToolModal(toolId);
}

async function saveTool(event) {
    event.preventDefault();

    const toolId = document.getElementById('toolId').value;
    const isEdit = !!toolId;

    // Parse JSON fields
    let parameters = parseJsonField(document.getElementById('toolParameters').value);
    let apiConfig = parseJsonField(document.getElementById('toolApiConfig').value);
    let flowTransition = parseJsonField(document.getElementById('toolFlowTransition').value);

    // Validate JSON if provided
    if (document.getElementById('toolParameters').value && parameters === null) {
        showToast('Invalid JSON in Parameters field', 'error');
        return;
    }
    if (document.getElementById('toolApiConfig').value && apiConfig === null) {
        showToast('Invalid JSON in API Configuration field', 'error');
        return;
    }
    if (document.getElementById('toolFlowTransition').value && flowTransition === null) {
        showToast('Invalid JSON in Flow Transition field', 'error');
        return;
    }

    const data = {
        name: document.getElementById('toolName').value.trim(),
        description: document.getElementById('toolDescription').value.trim(),
        side_effects: document.getElementById('toolSideEffects').value,
        parameters: parameters,
        api_config: apiConfig,
        requires_confirmation: document.getElementById('toolRequiresConfirmation').checked,
        confirmation_template: document.getElementById('toolConfirmationTemplate').value.trim() || null,
        flow_transition: flowTransition,
    };

    try {
        if (isEdit) {
            await apiRequest(`/tools/${toolId}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        } else {
            await apiRequest(`/agents/${selectedAgentId}/tools`, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        }

        closeModal('toolModal');
        await selectAgent(selectedAgentId);
        showToast(`Tool ${isEdit ? 'updated' : 'created'} successfully`, 'success');

    } catch (error) {
        showToast(`Failed to ${isEdit ? 'update' : 'create'} tool: ` + error.message, 'error');
    }
}

function confirmDeleteTool(toolId, toolName) {
    document.getElementById('confirmMessage').textContent =
        `Are you sure you want to delete the tool "${toolName}"?`;

    document.getElementById('confirmDeleteBtn').onclick = () => deleteTool(toolId);
    showModal('confirmModal');
}

async function deleteTool(toolId) {
    try {
        await apiRequest(`/tools/${toolId}`, {
            method: 'DELETE',
        });

        closeModal('confirmModal');
        await selectAgent(selectedAgentId);
        showToast('Tool deleted successfully', 'success');

    } catch (error) {
        showToast('Failed to delete tool: ' + error.message, 'error');
    }
}

// ============================================================================
// Template Rendering
// ============================================================================

function renderTemplates() {
    const container = document.getElementById('templatesList');
    const templates = selectedAgent.response_templates || [];

    if (templates.length === 0) {
        container.innerHTML = '<div class="empty-list">No templates configured</div>';
        return;
    }

    container.innerHTML = templates.map(template => `
        <div class="list-item">
            <div class="list-item-header">
                <div class="list-item-title">${escapeHtml(template.name)}</div>
                <div class="list-item-actions">
                    <button class="btn btn-secondary btn-small" onclick="editTemplate('${template.id}')">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="confirmDeleteTemplate('${template.id}', '${escapeHtml(template.name)}')">Delete</button>
                </div>
            </div>
            <div class="list-item-desc">${escapeHtml(template.template.substring(0, 100))}${template.template.length > 100 ? '...' : ''}</div>
            <div class="list-item-meta">
                <span>Enforcement: <span class="badge ${template.enforcement === 'mandatory' ? 'danger' : ''}">${template.enforcement}</span></span>
                <span>Trigger: ${escapeHtml(JSON.stringify(template.trigger_config))}</span>
            </div>
        </div>
    `).join('');
}

// ============================================================================
// Template Modal
// ============================================================================

function showTemplateModal(templateId = null) {
    const isEdit = !!templateId;
    document.getElementById('templateModalTitle').textContent = isEdit ? 'Edit Template' : 'Add Template';
    document.getElementById('templateForm').reset();
    document.getElementById('templateId').value = '';

    if (isEdit) {
        const template = selectedAgent.response_templates.find(t => t.id === templateId);
        if (template) {
            document.getElementById('templateId').value = template.id;
            document.getElementById('templateName').value = template.name;
            document.getElementById('templateEnforcement').value = template.enforcement;
            document.getElementById('templateTriggerConfig').value = JSON.stringify(template.trigger_config, null, 2);
            document.getElementById('templateContent').value = template.template;
            document.getElementById('templateRequiredFields').value = (template.required_fields || []).join(', ');
        }
    }

    showModal('templateModal');
}

function editTemplate(templateId) {
    showTemplateModal(templateId);
}

async function saveTemplate(event) {
    event.preventDefault();

    const templateId = document.getElementById('templateId').value;
    const isEdit = !!templateId;

    let triggerConfig = parseJsonField(document.getElementById('templateTriggerConfig').value);
    if (!triggerConfig) {
        showToast('Invalid JSON in Trigger Configuration', 'error');
        return;
    }

    const requiredFieldsStr = document.getElementById('templateRequiredFields').value.trim();
    const requiredFields = requiredFieldsStr
        ? requiredFieldsStr.split(',').map(f => f.trim()).filter(f => f)
        : null;

    const data = {
        name: document.getElementById('templateName').value.trim(),
        enforcement: document.getElementById('templateEnforcement').value,
        trigger_config: triggerConfig,
        template: document.getElementById('templateContent').value.trim(),
        required_fields: requiredFields,
    };

    try {
        if (isEdit) {
            await apiRequest(`/templates/${templateId}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        } else {
            await apiRequest(`/agents/${selectedAgentId}/templates`, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        }

        closeModal('templateModal');
        await selectAgent(selectedAgentId);
        showToast(`Template ${isEdit ? 'updated' : 'created'} successfully`, 'success');

    } catch (error) {
        showToast(`Failed to ${isEdit ? 'update' : 'create'} template: ` + error.message, 'error');
    }
}

function confirmDeleteTemplate(templateId, templateName) {
    document.getElementById('confirmMessage').textContent =
        `Are you sure you want to delete the template "${templateName}"?`;

    document.getElementById('confirmDeleteBtn').onclick = () => deleteTemplate(templateId);
    showModal('confirmModal');
}

async function deleteTemplate(templateId) {
    try {
        await apiRequest(`/templates/${templateId}`, {
            method: 'DELETE',
        });

        closeModal('confirmModal');
        await selectAgent(selectedAgentId);
        showToast('Template deleted successfully', 'success');

    } catch (error) {
        showToast('Failed to delete template: ' + error.message, 'error');
    }
}
