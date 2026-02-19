"""
Base LLM provider class
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Message:
    """Chat message"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class ToolCall:
    """Tool call from LLM"""
    id: str
    name: str
    arguments: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments
        }


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Any = None
    
    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLM(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    def generate(self, messages: List[Message], 
                 tools: Optional[List[Dict[str, Any]]] = None,
                 **kwargs) -> LLMResponse:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def generate_stream(self, messages: List[Message],
                        tools: Optional[List[Dict[str, Any]]] = None,
                        **kwargs):
        """Generate a streaming response"""
        pass
    
    def prepare_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to provider format"""
        return [m.to_dict() for m in messages]
    
    def prepare_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to provider format"""
        return tools


def get_llm_provider(provider: str, api_key: str, model: str, **kwargs) -> 'BaseLLM':
    """Factory function to get LLM provider"""
    if provider == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(api_key, model, **kwargs)
    elif provider == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key, model, **kwargs)
    elif provider == "google":
        from .google_provider import GoogleProvider
        return GoogleProvider(api_key, model, **kwargs)
    elif provider == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(api_key, model, **kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
