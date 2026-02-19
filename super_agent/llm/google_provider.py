"""
Google Gemini LLM provider
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base import BaseLLM, Message, LLMResponse, ToolCall


class GoogleProvider(BaseLLM):
    """Google Gemini API provider"""
    
    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    def __init__(self, api_key: str, model: str = "gemini-pro", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.max_tokens = kwargs.get('max_tokens', 4096)
        self.temperature = kwargs.get('temperature', 0.7)
    
    def generate(self, messages: List[Message],
                 tools: Optional[List[Dict[str, Any]]] = None,
                 **kwargs) -> LLMResponse:
        """Generate a response using Google Gemini API"""
        
        # Convert messages to Gemini format
        contents = self._convert_messages(messages)
        
        # Prepare request body
        body = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": kwargs.get('max_tokens', self.max_tokens),
                "temperature": kwargs.get('temperature', self.temperature),
            }
        }
        
        # Add tools if provided
        if tools:
            body["tools"] = self._prepare_tools_google(tools)
        
        # Build URL
        url = self.API_URL_TEMPLATE.format(
            model=self.model,
            api_key=self.api_key
        )
        
        # Make request
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            return self._parse_response(result)
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Google API error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"Google API request failed: {e}")
    
    def generate_stream(self, messages: List[Message],
                        tools: Optional[List[Dict[str, Any]]] = None,
                        **kwargs):
        """Generate a streaming response (simplified)"""
        yield self.generate(messages, tools, **kwargs)
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to Gemini format"""
        contents = []
        
        for msg in messages:
            # Gemini uses 'user' and 'model' roles
            role = "user" if msg.role in ["user", "system"] else "model"
            
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        
        return contents
    
    def _prepare_tools_google(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare tools in Google format"""
        google_tools = []
        
        function_declarations = []
        for tool in tools:
            # Convert to Google function declaration format
            if 'name' in tool:
                func_decl = {
                    "name": tool.get('name', ''),
                    "description": tool.get('description', ''),
                    "parameters": tool.get('parameters', {})
                }
            elif 'function' in tool:
                func = tool['function']
                func_decl = {
                    "name": func.get('name', ''),
                    "description": func.get('description', ''),
                    "parameters": func.get('parameters', {})
                }
            else:
                continue
            
            function_declarations.append(func_decl)
        
        if function_declarations:
            google_tools.append({
                "functionDeclarations": function_declarations
            })
        
        return google_tools
    
    def _parse_response(self, result: Dict[str, Any]) -> LLMResponse:
        """Parse Google Gemini response"""
        candidates = result.get('candidates', [{}])
        
        if not candidates:
            return LLMResponse(
                content="",
                finish_reason="error"
            )
        
        candidate = candidates[0]
        content_parts = candidate.get('content', {}).get('parts', [])
        
        # Extract text content
        text_content = ""
        tool_calls = []
        
        for part in content_parts:
            if 'text' in part:
                text_content += part['text']
            elif 'functionCall' in part:
                fc = part['functionCall']
                tool_calls.append(ToolCall(
                    id=fc.get('name', ''),  # Google doesn't provide IDs
                    name=fc.get('name', ''),
                    arguments=fc.get('args', {})
                ))
        
        # Extract usage
        usage = result.get('usageMetadata', {})
        
        return LLMResponse(
            content=text_content,
            tool_calls=tool_calls,
            finish_reason=candidate.get('finishReason', 'stop'),
            usage={
                'prompt_tokens': usage.get('promptTokenCount', 0),
                'completion_tokens': usage.get('candidatesTokenCount', 0),
                'total_tokens': usage.get('totalTokenCount', 0)
            },
            raw_response=result
        )
