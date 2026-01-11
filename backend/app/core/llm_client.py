"""OpenAI API client wrapper with tool calling support."""

import asyncio
import json
import logging
from typing import Optional, List, Any
from dataclasses import dataclass, field

from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError

from app.config import get_settings

MAX_RETRIES = 3
RETRY_DELAY_BASE = 1  # seconds

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""

    id: str
    name: str
    parameters: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from the LLM."""

    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: str = "stop"
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient:
    """Client for interacting with OpenAI API."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def _convert_tools_to_openai_format(self, tools: List[dict]) -> List[dict]:
        """Convert internal tool format to OpenAI function format."""
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    async def complete(
        self,
        system_prompt: str,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a completion request to OpenAI.

        Args:
            system_prompt: The system prompt for context
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions (will be converted to OpenAI format)
            model: Model to use (defaults to config)
            temperature: Temperature for generation (defaults to config)
            max_tokens: Max tokens to generate (defaults to config)

        Returns:
            LLMResponse with text, tool calls, and metadata
        """
        model = model or settings.default_model
        temperature = temperature if temperature is not None else settings.default_temperature
        max_tokens = max_tokens or settings.default_max_tokens

        # Build messages with system prompt
        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)

        # Build request kwargs
        request_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": openai_messages,
            "temperature": temperature,
        }

        # Add tools if provided
        if tools:
            openai_tools = self._convert_tools_to_openai_format(tools)
            request_kwargs["tools"] = openai_tools
            request_kwargs["tool_choice"] = "auto"

        logger.debug(f"Sending request to OpenAI: model={model}, messages={len(messages)}, tools={len(tools) if tools else 0}")

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(**request_kwargs)

                # Parse response
                message = response.choices[0].message
                text = message.content or ""
                tool_calls = []

                if message.tool_calls:
                    for tc in message.tool_calls:
                        try:
                            params = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            params = {}

                        tool_calls.append(
                            ToolCall(
                                id=tc.id,
                                name=tc.function.name,
                                parameters=params,
                            )
                        )

                return LLMResponse(
                    text=text,
                    tool_calls=tool_calls,
                    stop_reason=response.choices[0].finish_reason or "stop",
                    model=response.model,
                    input_tokens=response.usage.prompt_tokens if response.usage else 0,
                    output_tokens=response.usage.completion_tokens if response.usage else 0,
                )

            except (RateLimitError, APIConnectionError) as e:
                last_error = e
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)

            except APIStatusError as e:
                if e.status_code >= 500:
                    last_error = e
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(f"LLM server error (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    # Don't retry 4xx client errors
                    logger.error(f"OpenAI API client error: {e}")
                    raise

            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                raise

        logger.error(f"LLM request failed after {MAX_RETRIES} attempts: {last_error}")
        raise last_error

    async def complete_with_tool_results(
        self,
        system_prompt: str,
        messages: List[dict],
        tools: List[dict],
        tool_results: List[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Continue a conversation after tool execution.

        Args:
            system_prompt: The system prompt
            messages: Previous messages including the assistant message with tool calls
            tools: Tool definitions
            tool_results: Results from tool execution

        Returns:
            LLMResponse with the continued generation
        """
        # Format tool results for OpenAI
        messages_with_results = messages.copy()
        for result in tool_results:
            messages_with_results.append({
                "role": "tool",
                "tool_call_id": result.get("tool_call_id", ""),
                "content": json.dumps(result.get("content", {})),
            })

        return await self.complete(
            system_prompt=system_prompt,
            messages=messages_with_results,
            tools=tools,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
