"""Admin API routes for managing agents via JSON config files."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_loader import (
    load_agent_config,
    save_agent_config,
    delete_agent_config,
    get_agent_ids,
    agent_exists,
    reload_configs,
)
from app.database import get_db
from app.auth import verify_admin_token
from app.core.agent_registry import get_agent_registry, AgentRegistryError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================================
# Helper Functions
# ============================================================================

def find_item_by_name(items: list, name: str) -> tuple[int, Optional[dict]]:
    """Find an item in a list by its 'name' field."""
    for i, item in enumerate(items):
        if item.get("name") == name:
            return i, item
    return -1, None


# ============================================================================
# Config Reload Endpoint
# ============================================================================

@router.post("/reload-config")
async def reload_config(_token: str = Depends(verify_admin_token)):
    """
    Hot-reload all configs from JSON files.

    This reloads both the JSON cache and the AgentRegistry.
    Use this after editing agent configs to update the runtime.

    Unlike the old sync-to-db endpoint, this doesn't touch the database
    since agent configs are now loaded directly from JSON.
    """
    try:
        # Clear JSON config cache
        reload_configs()

        # Reload agent registry (validates configs)
        registry = get_agent_registry()
        registry.reload()

        agent_ids = get_agent_ids()
        return {
            "message": "Configs reloaded successfully",
            "agents": agent_ids,
            "count": len(agent_ids)
        }
    except AgentRegistryError as e:
        logger.error(f"Failed to reload configs: {e}")
        raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


# ============================================================================
# Agent Endpoints
# ============================================================================

@router.get("/agents")
async def list_agents(_token: str = Depends(verify_admin_token)):
    """List all agents from JSON files."""
    agents = []
    for agent_id in get_agent_ids():
        config = load_agent_config(agent_id)
        if config:
            agents.append({
                "id": agent_id,
                "name": config.get("name", agent_id),
                "description": config.get("description", ""),
                "parent_agent": config.get("parent_agent"),
                "is_active": config.get("is_active", True),
                "tools_count": len(config.get("tools", [])),
                "subflows_count": len(config.get("subflows", [])),
            })
    return agents


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, _token: str = Depends(verify_admin_token)):
    """Get full agent config from JSON."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Add computed fields for frontend compatibility
    return {
        "id": agent_id,
        "name": config.get("name", agent_id),
        "description": config.get("description", ""),
        "parent_agent_id": config.get("parent_agent"),
        "system_prompt_addition": config.get("system_prompt_addition", ""),
        "model_config_json": config.get("model_config", {}),
        "navigation_tools": config.get("navigation", {}),
        "is_active": config.get("is_active", True),
        # Nested entities
        "tools": config.get("tools", []),
        "subflows": config.get("subflows", []),
        "response_templates": config.get("response_templates", []),
        # Full config for reference
        "config": config,
    }


@router.post("/agents/{agent_id}")
async def create_agent(
    agent_id: str,
    config: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Create a new agent JSON file."""
    if agent_exists(agent_id):
        raise HTTPException(status_code=400, detail="Agent already exists")

    # Ensure required structure
    if "id" not in config:
        config["id"] = agent_id

    save_agent_config(agent_id, config)
    return {"id": agent_id, "message": "Agent created", **config}


@router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    updates: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Update agent config in JSON file."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Deep merge updates into config
    for key, value in updates.items():
        config[key] = value

    save_agent_config(agent_id, config)
    return {"id": agent_id, "message": "Agent updated", **config}


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, _token: str = Depends(verify_admin_token)):
    """Delete agent JSON file."""
    if not delete_agent_config(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": f"Agent '{agent_id}' deleted successfully"}


@router.post("/agents/{agent_id}/clone")
async def clone_agent(
    agent_id: str,
    new_agent_id: str = Body(..., embed=True),
    _token: str = Depends(verify_admin_token)
):
    """Clone an agent to a new JSON file."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent_exists(new_agent_id):
        raise HTTPException(status_code=400, detail="Target agent ID already exists")

    # Clone config with new ID
    cloned = config.copy()
    cloned["id"] = new_agent_id

    # Update name to indicate it's a copy
    if "name" in cloned:
        cloned["name"] = f"{cloned['name']} (Copy)"

    save_agent_config(new_agent_id, cloned)
    return {"id": new_agent_id, "message": "Agent cloned", **cloned}


# ============================================================================
# Tool Endpoints (modify tools array in agent JSON)
# ============================================================================

@router.get("/agents/{agent_id}/tools")
async def list_tools(agent_id: str, _token: str = Depends(verify_admin_token)):
    """List tools for an agent."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config.get("tools", [])


@router.post("/agents/{agent_id}/tools")
async def create_tool(
    agent_id: str,
    tool: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Add a tool to an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    if "name" not in tool:
        raise HTTPException(status_code=400, detail="Tool must have a 'name' field")

    tools = config.get("tools", [])

    # Check for duplicate name
    if any(t.get("name") == tool["name"] for t in tools):
        raise HTTPException(status_code=400, detail="Tool with this name already exists")

    tools.append(tool)
    config["tools"] = tools
    save_agent_config(agent_id, config)

    return {"message": "Tool added", "tool": tool}


@router.put("/agents/{agent_id}/tools/{tool_name}")
async def update_tool(
    agent_id: str,
    tool_name: str,
    tool: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Update a tool in an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    tools = config.get("tools", [])
    idx, existing = find_item_by_name(tools, tool_name)

    if idx == -1:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Replace the tool
    tools[idx] = tool
    config["tools"] = tools
    save_agent_config(agent_id, config)

    return {"message": "Tool updated", "tool": tool}


@router.delete("/agents/{agent_id}/tools/{tool_name}")
async def delete_tool(
    agent_id: str,
    tool_name: str,
    _token: str = Depends(verify_admin_token)
):
    """Delete a tool from an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    tools = config.get("tools", [])
    idx, _ = find_item_by_name(tools, tool_name)

    if idx == -1:
        raise HTTPException(status_code=404, detail="Tool not found")

    deleted = tools.pop(idx)
    config["tools"] = tools
    save_agent_config(agent_id, config)

    return {"message": "Tool deleted", "tool": deleted}


# ============================================================================
# Subflow Endpoints (modify subflows array in agent JSON)
# ============================================================================

@router.get("/agents/{agent_id}/subflows")
async def list_subflows(agent_id: str, _token: str = Depends(verify_admin_token)):
    """List subflows for an agent."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config.get("subflows", [])


@router.get("/agents/{agent_id}/subflows/{subflow_id}")
async def get_subflow(
    agent_id: str,
    subflow_id: str,
    _token: str = Depends(verify_admin_token)
):
    """Get a specific subflow."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    subflows = config.get("subflows", [])
    for sf in subflows:
        if sf.get("id") == subflow_id:
            return sf

    raise HTTPException(status_code=404, detail="Subflow not found")


@router.post("/agents/{agent_id}/subflows")
async def create_subflow(
    agent_id: str,
    subflow: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Add a subflow to an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    if "id" not in subflow:
        raise HTTPException(status_code=400, detail="Subflow must have an 'id' field")

    subflows = config.get("subflows", [])

    # Check for duplicate ID
    if any(sf.get("id") == subflow["id"] for sf in subflows):
        raise HTTPException(status_code=400, detail="Subflow with this ID already exists")

    subflows.append(subflow)
    config["subflows"] = subflows
    save_agent_config(agent_id, config)

    return {"message": "Subflow added", "subflow": subflow}


@router.put("/agents/{agent_id}/subflows/{subflow_id}")
async def update_subflow(
    agent_id: str,
    subflow_id: str,
    subflow: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Update a subflow in an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    subflows = config.get("subflows", [])

    for i, sf in enumerate(subflows):
        if sf.get("id") == subflow_id:
            subflows[i] = subflow
            config["subflows"] = subflows
            save_agent_config(agent_id, config)
            return {"message": "Subflow updated", "subflow": subflow}

    raise HTTPException(status_code=404, detail="Subflow not found")


@router.delete("/agents/{agent_id}/subflows/{subflow_id}")
async def delete_subflow(
    agent_id: str,
    subflow_id: str,
    _token: str = Depends(verify_admin_token)
):
    """Delete a subflow from an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    subflows = config.get("subflows", [])

    for i, sf in enumerate(subflows):
        if sf.get("id") == subflow_id:
            deleted = subflows.pop(i)
            config["subflows"] = subflows
            save_agent_config(agent_id, config)
            return {"message": "Subflow deleted", "subflow": deleted}

    raise HTTPException(status_code=404, detail="Subflow not found")


# ============================================================================
# Subflow State Endpoints (modify states array in subflow)
# ============================================================================

@router.get("/agents/{agent_id}/subflows/{subflow_id}/states")
async def list_states(
    agent_id: str,
    subflow_id: str,
    _token: str = Depends(verify_admin_token)
):
    """List states for a subflow."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    for sf in config.get("subflows", []):
        if sf.get("id") == subflow_id:
            return sf.get("states", [])

    raise HTTPException(status_code=404, detail="Subflow not found")


@router.post("/agents/{agent_id}/subflows/{subflow_id}/states")
async def create_state(
    agent_id: str,
    subflow_id: str,
    state: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Add a state to a subflow."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    if "id" not in state:
        raise HTTPException(status_code=400, detail="State must have an 'id' field")

    subflows = config.get("subflows", [])

    for sf in subflows:
        if sf.get("id") == subflow_id:
            states = sf.get("states", [])

            # Check for duplicate state ID
            if any(s.get("id") == state["id"] for s in states):
                raise HTTPException(status_code=400, detail="State with this ID already exists")

            states.append(state)
            sf["states"] = states
            config["subflows"] = subflows
            save_agent_config(agent_id, config)

            return {"message": "State added", "state": state}

    raise HTTPException(status_code=404, detail="Subflow not found")


@router.put("/agents/{agent_id}/subflows/{subflow_id}/states/{state_id}")
async def update_state(
    agent_id: str,
    subflow_id: str,
    state_id: str,
    state: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Update a state in a subflow."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    subflows = config.get("subflows", [])

    for sf in subflows:
        if sf.get("id") == subflow_id:
            states = sf.get("states", [])

            for i, s in enumerate(states):
                if s.get("id") == state_id:
                    states[i] = state
                    sf["states"] = states
                    config["subflows"] = subflows
                    save_agent_config(agent_id, config)
                    return {"message": "State updated", "state": state}

            raise HTTPException(status_code=404, detail="State not found")

    raise HTTPException(status_code=404, detail="Subflow not found")


@router.delete("/agents/{agent_id}/subflows/{subflow_id}/states/{state_id}")
async def delete_state(
    agent_id: str,
    subflow_id: str,
    state_id: str,
    _token: str = Depends(verify_admin_token)
):
    """Delete a state from a subflow."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    subflows = config.get("subflows", [])

    for sf in subflows:
        if sf.get("id") == subflow_id:
            states = sf.get("states", [])

            for i, s in enumerate(states):
                if s.get("id") == state_id:
                    deleted = states.pop(i)
                    sf["states"] = states
                    config["subflows"] = subflows
                    save_agent_config(agent_id, config)
                    return {"message": "State deleted", "state": deleted}

            raise HTTPException(status_code=404, detail="State not found")

    raise HTTPException(status_code=404, detail="Subflow not found")


# ============================================================================
# Response Template Endpoints (modify response_templates array in agent JSON)
# ============================================================================

@router.get("/agents/{agent_id}/templates")
async def list_templates(agent_id: str, _token: str = Depends(verify_admin_token)):
    """List response templates for an agent."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config.get("response_templates", [])


@router.post("/agents/{agent_id}/templates")
async def create_template(
    agent_id: str,
    template: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Add a response template to an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    if "name" not in template:
        raise HTTPException(status_code=400, detail="Template must have a 'name' field")

    templates = config.get("response_templates", [])

    # Check for duplicate name
    template_name = template.get("name")
    if any(t.get("name") == template_name for t in templates):
        raise HTTPException(status_code=400, detail="Template with this name already exists")

    templates.append(template)
    config["response_templates"] = templates
    save_agent_config(agent_id, config)

    return {"message": "Template added", "template": template}


@router.put("/agents/{agent_id}/templates/{template_name}")
async def update_template(
    agent_id: str,
    template_name: str,
    template: dict = Body(...),
    _token: str = Depends(verify_admin_token)
):
    """Update a response template in an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    templates = config.get("response_templates", [])

    for i, t in enumerate(templates):
        if t.get("name") == template_name:
            templates[i] = template
            config["response_templates"] = templates
            save_agent_config(agent_id, config)
            return {"message": "Template updated", "template": template}

    raise HTTPException(status_code=404, detail="Template not found")


@router.delete("/agents/{agent_id}/templates/{template_name}")
async def delete_template(
    agent_id: str,
    template_name: str,
    _token: str = Depends(verify_admin_token)
):
    """Delete a response template from an agent's JSON config."""
    config = load_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")

    templates = config.get("response_templates", [])

    for i, t in enumerate(templates):
        if t.get("name") == template_name:
            deleted = templates.pop(i)
            config["response_templates"] = templates
            save_agent_config(agent_id, config)
            return {"message": "Template deleted", "template": deleted}

    raise HTTPException(status_code=404, detail="Template not found")
