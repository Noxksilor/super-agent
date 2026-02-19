"""
OpenAI LLM provider
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base import BaseLLM, Message, LLMResponse, ToolCall


class OpenAIProvider(BaseLLM):
    """OpenAI API provider"""
    
    API_URL = "https://api.openai.com/v1/chat/completions"
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.max_tokens = kwargs.get('max_tokens', 4096)
        self.temperature = kwargs.get('temperature', 0.7)
    
    def generate(self, messages: List[Message],
                 tools: Optional[List[Dict[str, Any]]] = None,
                 **kwargs) -> LLMResponse:
        """Generate a response using OpenAI API"""
        
        # Prepare request body
        body = {
            "model": self.model,
            "messages": self.prepare_messages(messages),
            "max_tokens": kwargs.get('max_tokens', self.max_tokens),
            "temperature": kwargs.get('temperature', self.temperature),
        }
        
        # Add tools if provided
        if tools:
            body["tools"] = self._prepare_tools_openai(tools)
            body["tool_choice"] = kwargs.get('tool_choice', 'auto')
        
        # Make request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
            raise Exception(f"OpenAI API error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"OpenAI API request failed: {e}")
    
    def generate_stream(self, messages: List[Message],
                        tools: Optional[List[Dict[str, Any]]] = None,
                        **kwargs):
        """Generate a streaming response (simplified - returns full response)"""
        # For simplicity, we don't implement streaming here
        # In production, you'd use SSE or websockets
        yield self.generate(messages, tools, **kwargs)
    
    def _prepare_tools_openai(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare tools in OpenAI format"""
        openai_tools = []
        for tool in tools:
            # Assume tools are already in OpenAI format or convert
            if 'type' in tool and tool['type'] == 'function':
                openai_tools.append(tool)
            else:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get('name', ''),
                        "description": tool.get('description', ''),
                        "parameters": tool.get('parameters', {})
                    }
                })
        return openai_tools
    
    def _parse_response(self, result: Dict[str, Any]) -> LLMResponse:
        """Parse OpenAI response"""
        choice = result.get('choices', [{}])[0]
        message = choice.get('message', {})
        
        # Extract content
        content = message.get('content', '') or ''
        
        # Extract tool calls
        tool_calls = []
        if 'tool_calls' in message:
            for tc in message['tool_calls']:
                if tc.get('type') == 'function':
                    func = tc.get('function', {})
                    try:
                        args = json.loads(func.get('arguments', '{}'))
                    except json.JSONDecodeError:
                        args = {}
                    
                    tool_calls.append(ToolCall(
                        id=tc.get('id', ''),
                        name=func.get('name', ''),
                        arguments=args
                    ))
        
        # Extract usage
        usage = result.get('usage', {})
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.get('finish_reason', 'stop'),
            usage={
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            },
            raw_response=result
        )
