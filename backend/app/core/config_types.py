"""Configuration dataclasses for in-memory agent configuration.

These dataclasses replace the SQLAlchemy ORM models (Agent, Tool, etc.)
for agent configuration. Session/message data still uses DB models.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.routing import RoutingConfig, RoutingType


class PromptMode(Enum):
    """Mode for context assembly - controls how much context is included.

    FULL: Main conversation - includes all sections (base prompt, agent desc,
          user profile, product context, history, flow state, navigation, language)
    ROUTING: Routing decisions - minimal context for agent/flow routing only
             (brief system prompt, routing tools only, single user message)
    """
    FULL = "full"
    ROUTING = "routing"


@dataclass
class ToolConfig:
    """Tool definition loaded from JSON config."""
    name: str
    description: str
    parameters: List[dict] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_template: Optional[str] = None
    side_effects: str = "none"  # none, read, write, financial
    flow_transition: Optional[dict] = None
    routing: Optional[RoutingConfig] = None

    def to_openai_tool(self) -> dict:
        """Convert to OpenAI API tool format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {"type": param.get("type", "string")}
            if "description" in param:
                prop["description"] = param["description"]
            if "enum" in param.get("validation", {}):
                prop["enum"] = param["validation"]["enum"]
            properties[param["name"]] = prop
            if param.get("required", False):
                required.append(param["name"])

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolConfig":
        """Create from JSON tool config."""
        routing = None

        # Parse explicit routing config
        if "routing" in data:
            routing = RoutingConfig.from_dict(data["routing"])
        # Legacy: starts_flow field
        elif "starts_flow" in data:
            routing = RoutingConfig(
                type=RoutingType.START_FLOW,
                target=data["starts_flow"]
            )
        # Infer routing from tool name conventions
        elif data["name"].startswith("enter_"):
            routing = RoutingConfig(
                type=RoutingType.ENTER_AGENT,
                target=data["name"].replace("enter_", "")
            )
        elif data["name"].startswith("start_flow_"):
            routing = RoutingConfig(
                type=RoutingType.START_FLOW,
                target=data["name"].replace("start_flow_", "")
            )
        elif data["name"] in ["go_home", "up_one_level", "escalate_to_human"]:
            routing = RoutingConfig(
                type=RoutingType.NAVIGATION,
                target=data["name"]
            )

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            parameters=data.get("parameters", []),
            requires_confirmation=data.get("requires_confirmation", False),
            confirmation_template=data.get("confirmation_template"),
            side_effects=data.get("side_effects", "none"),
            flow_transition=data.get("flow_transition"),
            routing=routing,
        )


@dataclass
class SubflowStateConfig:
    """Flow state definition loaded from JSON config."""
    state_id: str
    name: str
    agent_instructions: str
    state_tools: List[str] = field(default_factory=list)
    transitions: List[dict] = field(default_factory=list)
    on_enter: Optional[dict] = None
    is_final: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "SubflowStateConfig":
        """Create from JSON state config."""
        return cls(
            state_id=data["id"],
            name=data.get("name", data["id"]),
            agent_instructions=data.get("agent_instructions", ""),
            state_tools=data.get("state_tools", []),
            transitions=data.get("transitions", []),
            on_enter=data.get("on_enter"),
            is_final=data.get("is_final", False),
        )


@dataclass
class SubflowConfig:
    """Subflow definition loaded from JSON config."""
    config_id: str
    agent_id: str  # Parent agent's config_id
    name: str
    trigger_description: str
    initial_state: str
    data_schema: dict = field(default_factory=dict)
    timeout_config: dict = field(default_factory=dict)
    states: Dict[str, SubflowStateConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict, agent_id: str) -> "SubflowConfig":
        """Create from JSON subflow config."""
        states = {}
        for state_data in data.get("states", []):
            state = SubflowStateConfig.from_dict(state_data)
            states[state.state_id] = state

        return cls(
            config_id=data["id"],
            agent_id=agent_id,
            name=data.get("name", data["id"]),
            trigger_description=data.get("trigger_description", ""),
            initial_state=data.get("initial_state", ""),
            data_schema=data.get("data_schema", {}),
            timeout_config=data.get("timeout_config", {}),
            states=states,
        )


@dataclass
class ResponseTemplateConfig:
    """Response template loaded from JSON config."""
    name: str
    trigger_config: dict
    template: str
    required_fields: List[str] = field(default_factory=list)
    enforcement: str = "suggested"

    @classmethod
    def from_dict(cls, data: dict) -> "ResponseTemplateConfig":
        """Create from JSON template config."""
        return cls(
            name=data.get("name", ""),
            trigger_config=data.get("trigger_config", {}),
            template=data.get("template", ""),
            required_fields=data.get("required_fields", []),
            enforcement=data.get("enforcement", "suggested"),
        )


@dataclass
class AgentConfig:
    """Agent configuration loaded from JSON config."""
    config_id: str
    name: str
    description: str
    parent_agent_id: Optional[str] = None
    system_prompt_addition: Optional[str] = None
    model_config: dict = field(default_factory=lambda: {
        "model": "gpt-5.2",
        "temperature": 0.7,
        "maxTokens": 1024
    })
    navigation_tools: dict = field(default_factory=lambda: {
        "canGoUp": False,
        "canGoHome": False,
        "canEscalate": True
    })
    context_requirements: List[dict] = field(default_factory=list)
    tools: List[ToolConfig] = field(default_factory=list)
    subflows: List[SubflowConfig] = field(default_factory=list)
    response_templates: List[ResponseTemplateConfig] = field(default_factory=list)
    raw_config: dict = field(default_factory=dict)  # Full JSON for reference
    default_tools: List[str] = field(default_factory=list)  # Tool whitelist for non-flow contexts

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """Create AgentConfig from JSON config dict."""
        config_id = data.get("id", "")

        tools = [ToolConfig.from_dict(t) for t in data.get("tools", [])]
        subflows = [SubflowConfig.from_dict(s, config_id) for s in data.get("subflows", [])]
        response_templates = [
            ResponseTemplateConfig.from_dict(t)
            for t in data.get("response_templates", [])
        ]

        return cls(
            config_id=config_id,
            name=data.get("name", config_id),
            description=data.get("description", ""),
            parent_agent_id=data.get("parent_agent"),
            system_prompt_addition=data.get("system_prompt_addition"),
            model_config=data.get("model_config", {
                "model": "gpt-5.2",
                "temperature": 0.7,
                "maxTokens": 1024
            }),
            navigation_tools=data.get("navigation", {
                "canGoUp": False,
                "canGoHome": False,
                "canEscalate": True
            }),
            context_requirements=data.get("context_requirements", []),
            tools=tools,
            subflows=subflows,
            response_templates=response_templates,
            raw_config=data,
            default_tools=data.get("default_tools", []),
        )

    def get_tool(self, name: str) -> Optional[ToolConfig]:
        """Get tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_subflow(self, config_id: str) -> Optional[SubflowConfig]:
        """Get subflow by config_id."""
        for subflow in self.subflows:
            if subflow.config_id == config_id:
                return subflow
        return None
