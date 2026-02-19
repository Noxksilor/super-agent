"""
Anthropic Claude LLM provider
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base import BaseLLM, Message, LLMResponse, ToolCall


class AnthropicProvider(BaseLLM):
    """Anthropic Claude API provider"""
    
    API_URL = "https://api.anthropic.com/v1/messages"
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.max_tokens = kwargs.get('max_tokens', 4096)
        self.temperature = kwargs.get('temperature', 0.7)
    
    def generate(self, messages: List[Message],
                 tools: Optional[List[Dict[str, Any]]] = None,
                 **kwargs) -> LLMResponse:
        """Generate a response using Anthropic API"""
        
        # Separate system message from other messages
        system_content = ""
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Prepare request body
        body = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": kwargs.get('max_tokens', self.max_tokens),
        }
        
        if system_content:
            body["system"] = system_content
        
        if kwargs.get('temperature') is not None:
            body["temperature"] = kwargs.get('temperature')
        elif self.temperature is not None:
            body["temperature"] = self.temperature
        
        # Add tools if provided
        if tools:
            body["tools"] = self._prepare_tools_anthropic(tools)
        
        # Make request
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        try:
            req = urllib.request.Request(
                self.API_URL,
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            return self._parse_response(result)
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Anthropic API error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"Anthropic API request failed: {e}")
    
    def generate_stream(self, messages: List[Message],
                        tools: Optional[List[Dict[str, Any]]] = None,
                        **kwargs):
        """Generate a streaming response (simplified)"""
        yield self.generate(messages, tools, **kwargs)
    
    def _prepare_tools_anthropic(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare tools in Anthropic format"""
        anthropic_tools = []
        for tool in tools:
            # Convert to Anthropic format
            if 'name' in tool:
                anthropic_tools.append({
                    "name": tool.get('name', ''),
                    "description": tool.get('description', ''),
                    "input_schema": tool.get('parameters', tool.get('input_schema', {}))
                })
            elif 'function' in tool:
                func = tool['function']
                anthropic_tools.append({
                    "name": func.get('name', ''),
                    "description": func.get('description', ''),
                    "input_schema": func.get('parameters', {})
                })
        return anthropic_tools
    
    def _parse_response(self, result: Dict[str, Any]) -> LLMResponse:
        """Parse Anthropic response"""
        content_blocks = result.get('content', [])
        
        # Extract text content
        text_content = ""
        tool_calls = []
        
        for block in content_blocks:
            if block.get('type') == 'text':
                text_content += block.get('text', '')
            elif block.get('type') == 'tool_use':
                tool_calls.append(ToolCall(
                    id=block.get('id', ''),
                    name=block.get('name', ''),
                    arguments=block.get('input', {})
                ))
        
        # Extract usage
        usage = result.get('usage', {})
        
        return LLMResponse(
            content=text_content,
            tool_calls=tool_calls,
            finish_reason=result.get('stop_reason', 'stop'),
            usage={
                'prompt_tokens': usage.get('input_tokens', 0),
                'completion_tokens': usage.get('output_tokens', 0),
                'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
            },
            raw_response=result
        )
