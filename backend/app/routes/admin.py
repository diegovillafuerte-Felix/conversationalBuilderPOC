"""Admin API routes for managing agents, tools, subflows, and templates."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.agent import Agent, Tool, ResponseTemplate
from app.models.subflow import Subflow, SubflowState
from app.schemas.admin import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListItem,
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    SubflowCreate,
    SubflowUpdate,
    SubflowResponse,
    SubflowStateResponse,
    StateCreate,
    StateUpdate,
    TemplateCreate,
    TemplateUpdate,
    ResponseTemplateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================================
# Helper Functions
# ============================================================================

def agent_to_list_item(agent: Agent) -> AgentListItem:
    """Convert Agent model to AgentListItem schema."""
    return AgentListItem(
        id=agent.id,
        name=agent.name,
        parent_agent_id=agent.parent_agent_id,
        description=agent.description,
        is_active=agent.is_active,
    )


def tool_to_response(tool: Tool) -> ToolResponse:
    """Convert Tool model to ToolResponse schema."""
    return ToolResponse(
        id=tool.id,
        agent_id=tool.agent_id,
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        api_config=tool.api_config,
        response_config=tool.response_config,
        requires_confirmation=tool.requires_confirmation,
        confirmation_template=tool.confirmation_template,
        side_effects=tool.side_effects,
        flow_transition=tool.flow_transition,
        created_at=tool.created_at,
    )


def state_to_response(state: SubflowState) -> SubflowStateResponse:
    """Convert SubflowState model to SubflowStateResponse schema."""
    return SubflowStateResponse(
        id=state.id,
        subflow_id=state.subflow_id,
        state_id=state.state_id,
        name=state.name,
        agent_instructions=state.agent_instructions,
        state_tools=state.state_tools,
        transitions=state.transitions,
        is_final=state.is_final,
        on_enter=state.on_enter,
    )


def subflow_to_response(subflow: Subflow) -> SubflowResponse:
    """Convert Subflow model to SubflowResponse schema."""
    return SubflowResponse(
        id=subflow.id,
        agent_id=subflow.agent_id,
        name=subflow.name,
        trigger_description=subflow.trigger_description,
        initial_state=subflow.initial_state,
        data_schema=subflow.data_schema,
        timeout_config=subflow.timeout_config,
        created_at=subflow.created_at,
        states=[state_to_response(s) for s in subflow.states],
    )


def template_to_response(template: ResponseTemplate) -> ResponseTemplateResponse:
    """Convert ResponseTemplate model to ResponseTemplateResponse schema."""
    return ResponseTemplateResponse(
        id=template.id,
        agent_id=template.agent_id,
        name=template.name,
        trigger_config=template.trigger_config,
        template=template.template,
        required_fields=template.required_fields,
        enforcement=template.enforcement,
    )


def agent_to_response(agent: Agent) -> AgentResponse:
    """Convert Agent model to AgentResponse schema."""
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        parent_agent_id=agent.parent_agent_id,
        description=agent.description,
        system_prompt_addition=agent.system_prompt_addition,
        model_config_json=agent.model_config_json,
        navigation_tools=agent.navigation_tools,
        context_requirements=agent.context_requirements,
        is_active=agent.is_active,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        children=[agent_to_list_item(c) for c in agent.children],
        tools=[tool_to_response(t) for t in agent.tools],
        subflows=[subflow_to_response(s) for s in agent.subflows],
        response_templates=[template_to_response(t) for t in agent.response_templates],
    )


# ============================================================================
# Agent Endpoints
# ============================================================================

@router.get("/agents", response_model=List[AgentListItem])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all agents."""
    result = await db.execute(select(Agent).order_by(Agent.name))
    agents = result.scalars().all()
    return [agent_to_list_item(a) for a in agents]


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get agent details with all relationships."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.children),
            selectinload(Agent.tools),
            selectinload(Agent.subflows).selectinload(Subflow.states),
            selectinload(Agent.response_templates),
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent_to_response(agent)


@router.post("/agents", response_model=AgentResponse)
async def create_agent(request: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new agent."""
    # Validate parent exists if specified
    if request.parent_agent_id:
        result = await db.execute(
            select(Agent).where(Agent.id == request.parent_agent_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Parent agent not found")

    agent = Agent(
        name=request.name,
        description=request.description,
        parent_agent_id=request.parent_agent_id,
        system_prompt_addition=request.system_prompt_addition,
        model_config_json=request.model_config_json,
        navigation_tools=request.navigation_tools,
        context_requirements=request.context_requirements,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent, ["children", "tools", "subflows", "response_templates"])

    return agent_to_response(agent)


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    request: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an agent."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.children),
            selectinload(Agent.tools),
            selectinload(Agent.subflows).selectinload(Subflow.states),
            selectinload(Agent.response_templates),
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update fields if provided
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    return agent_to_response(agent)


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete an agent and all related entities."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(agent)
    await db.commit()

    return {"message": "Agent deleted successfully"}


@router.post("/agents/{agent_id}/clone", response_model=AgentResponse)
async def clone_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Clone an agent with its tools and templates."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.tools),
            selectinload(Agent.response_templates),
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create cloned agent
    cloned = Agent(
        name=f"{source.name} (Copy)",
        description=source.description,
        parent_agent_id=source.parent_agent_id,
        system_prompt_addition=source.system_prompt_addition,
        model_config_json=source.model_config_json,
        navigation_tools=source.navigation_tools,
        context_requirements=source.context_requirements,
    )
    db.add(cloned)
    await db.flush()

    # Clone tools
    for tool in source.tools:
        cloned_tool = Tool(
            agent_id=cloned.id,
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            api_config=tool.api_config,
            response_config=tool.response_config,
            requires_confirmation=tool.requires_confirmation,
            confirmation_template=tool.confirmation_template,
            side_effects=tool.side_effects,
            flow_transition=tool.flow_transition,
        )
        db.add(cloned_tool)

    # Clone templates
    for template in source.response_templates:
        cloned_template = ResponseTemplate(
            agent_id=cloned.id,
            name=template.name,
            trigger_config=template.trigger_config,
            template=template.template,
            required_fields=template.required_fields,
            enforcement=template.enforcement,
        )
        db.add(cloned_template)

    await db.commit()
    await db.refresh(cloned, ["children", "tools", "subflows", "response_templates"])

    return agent_to_response(cloned)


# ============================================================================
# Tool Endpoints
# ============================================================================

@router.get("/agents/{agent_id}/tools", response_model=List[ToolResponse])
async def list_tools(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """List tools for an agent."""
    result = await db.execute(
        select(Tool).where(Tool.agent_id == agent_id).order_by(Tool.name)
    )
    tools = result.scalars().all()
    return [tool_to_response(t) for t in tools]


@router.post("/agents/{agent_id}/tools", response_model=ToolResponse)
async def create_tool(
    agent_id: UUID,
    request: ToolCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a tool to an agent."""
    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    tool = Tool(
        agent_id=agent_id,
        name=request.name,
        description=request.description,
        parameters=request.parameters,
        api_config=request.api_config,
        response_config=request.response_config,
        requires_confirmation=request.requires_confirmation,
        confirmation_template=request.confirmation_template,
        side_effects=request.side_effects,
        flow_transition=request.flow_transition,
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)

    return tool_to_response(tool)


@router.put("/tools/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    request: ToolUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool, field, value)

    await db.commit()
    await db.refresh(tool)

    return tool_to_response(tool)


@router.delete("/tools/{tool_id}")
async def delete_tool(tool_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    await db.delete(tool)
    await db.commit()

    return {"message": "Tool deleted successfully"}


# ============================================================================
# Subflow Endpoints
# ============================================================================

@router.get("/agents/{agent_id}/subflows", response_model=List[SubflowResponse])
async def list_subflows(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """List subflows for an agent."""
    result = await db.execute(
        select(Subflow)
        .where(Subflow.agent_id == agent_id)
        .options(selectinload(Subflow.states))
        .order_by(Subflow.name)
    )
    subflows = result.scalars().all()
    return [subflow_to_response(s) for s in subflows]


@router.post("/agents/{agent_id}/subflows", response_model=SubflowResponse)
async def create_subflow(
    agent_id: UUID,
    request: SubflowCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a subflow for an agent."""
    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    subflow = Subflow(
        agent_id=agent_id,
        name=request.name,
        trigger_description=request.trigger_description,
        initial_state=request.initial_state,
        data_schema=request.data_schema,
        timeout_config=request.timeout_config,
    )
    db.add(subflow)
    await db.commit()
    await db.refresh(subflow, ["states"])

    return subflow_to_response(subflow)


@router.put("/subflows/{subflow_id}", response_model=SubflowResponse)
async def update_subflow(
    subflow_id: UUID,
    request: SubflowUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a subflow."""
    result = await db.execute(
        select(Subflow)
        .where(Subflow.id == subflow_id)
        .options(selectinload(Subflow.states))
    )
    subflow = result.scalar_one_or_none()

    if not subflow:
        raise HTTPException(status_code=404, detail="Subflow not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subflow, field, value)

    await db.commit()
    await db.refresh(subflow)

    return subflow_to_response(subflow)


@router.delete("/subflows/{subflow_id}")
async def delete_subflow(subflow_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a subflow and its states."""
    result = await db.execute(select(Subflow).where(Subflow.id == subflow_id))
    subflow = result.scalar_one_or_none()

    if not subflow:
        raise HTTPException(status_code=404, detail="Subflow not found")

    await db.delete(subflow)
    await db.commit()

    return {"message": "Subflow deleted successfully"}


# ============================================================================
# SubflowState Endpoints
# ============================================================================

@router.get("/subflows/{subflow_id}/states", response_model=List[SubflowStateResponse])
async def list_states(subflow_id: UUID, db: AsyncSession = Depends(get_db)):
    """List states for a subflow."""
    result = await db.execute(
        select(SubflowState)
        .where(SubflowState.subflow_id == subflow_id)
        .order_by(SubflowState.state_id)
    )
    states = result.scalars().all()
    return [state_to_response(s) for s in states]


@router.post("/subflows/{subflow_id}/states", response_model=SubflowStateResponse)
async def create_state(
    subflow_id: UUID,
    request: StateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a state to a subflow."""
    # Verify subflow exists
    result = await db.execute(select(Subflow).where(Subflow.id == subflow_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subflow not found")

    # Check for duplicate state_id
    result = await db.execute(
        select(SubflowState)
        .where(SubflowState.subflow_id == subflow_id)
        .where(SubflowState.state_id == request.state_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="State ID already exists in this subflow")

    state = SubflowState(
        subflow_id=subflow_id,
        state_id=request.state_id,
        name=request.name,
        agent_instructions=request.agent_instructions,
        state_tools=request.state_tools,
        transitions=request.transitions,
        is_final=request.is_final,
        on_enter=request.on_enter,
    )
    db.add(state)
    await db.commit()
    await db.refresh(state)

    return state_to_response(state)


@router.put("/states/{state_id}", response_model=SubflowStateResponse)
async def update_state(
    state_id: UUID,
    request: StateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a subflow state."""
    result = await db.execute(select(SubflowState).where(SubflowState.id == state_id))
    state = result.scalar_one_or_none()

    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(state, field, value)

    await db.commit()
    await db.refresh(state)

    return state_to_response(state)


@router.delete("/states/{state_id}")
async def delete_state(state_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a subflow state."""
    result = await db.execute(select(SubflowState).where(SubflowState.id == state_id))
    state = result.scalar_one_or_none()

    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    await db.delete(state)
    await db.commit()

    return {"message": "State deleted successfully"}


# ============================================================================
# ResponseTemplate Endpoints
# ============================================================================

@router.get("/agents/{agent_id}/templates", response_model=List[ResponseTemplateResponse])
async def list_templates(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """List response templates for an agent."""
    result = await db.execute(
        select(ResponseTemplate)
        .where(ResponseTemplate.agent_id == agent_id)
        .order_by(ResponseTemplate.name)
    )
    templates = result.scalars().all()
    return [template_to_response(t) for t in templates]


@router.post("/agents/{agent_id}/templates", response_model=ResponseTemplateResponse)
async def create_template(
    agent_id: UUID,
    request: TemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a response template for an agent."""
    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    template = ResponseTemplate(
        agent_id=agent_id,
        name=request.name,
        trigger_config=request.trigger_config,
        template=request.template,
        required_fields=request.required_fields,
        enforcement=request.enforcement,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return template_to_response(template)


@router.put("/templates/{template_id}", response_model=ResponseTemplateResponse)
async def update_template(
    template_id: UUID,
    request: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a response template."""
    result = await db.execute(
        select(ResponseTemplate).where(ResponseTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return template_to_response(template)


@router.delete("/templates/{template_id}")
async def delete_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a response template."""
    result = await db.execute(
        select(ResponseTemplate).where(ResponseTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()

    return {"message": "Template deleted successfully"}
