"""
Ollama LLM provider for local models
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base import BaseLLM, Message, LLMResponse, ToolCall


class OllamaProvider(BaseLLM):
    """Ollama API provider for local LLM models"""
    
    DEFAULT_ENDPOINT = "http://localhost:11434"
    
    def __init__(self, api_key: str = "", model: str = "llama3.2:3b", **kwargs):
        # Ollama doesn't need an API key, but we accept the parameter for consistency
        super().__init__(api_key or "local", model, **kwargs)
        self.endpoint = kwargs.get('endpoint', self.DEFAULT_ENDPOINT)
        self.max_tokens = kwargs.get('max_tokens', 4096)
        self.temperature = kwargs.get('temperature', 0.7)
    
    def generate(self, messages: List[Message],
                 tools: Optional[List[Dict[str, Any]]] = None,
                 **kwargs) -> LLMResponse:
        """Generate a response using Ollama API"""
        
        # Convert messages to Ollama format
        ollama_messages = self._convert_messages(messages)
        
        # Prepare request body
        body = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": kwargs.get('max_tokens', self.max_tokens),
                "temperature": kwargs.get('temperature', self.temperature),
            }
        }
        
        # Note: Ollama supports tools but with different format
        # For now, we skip tools to keep it simple
        
        # Build URL
        url = f"{self.endpoint}/api/chat"
        
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
            
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            return self._parse_response(result)
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Ollama API error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Ollama connection error: {e.reason}. Make sure Ollama is running at {self.endpoint}")
        except Exception as e:
            raise Exception(f"Ollama API request failed: {e}")
    
    def generate_stream(self, messages: List[Message],
                        tools: Optional[List[Dict[str, Any]]] = None,
                        **kwargs):
        """Generate a streaming response (simplified)"""
        yield self.generate(messages, tools, **kwargs)
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to Ollama format"""
        ollama_messages = []
        
        for msg in messages:
            ollama_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return ollama_messages
    
    def _parse_response(self, result: Dict[str, Any]) -> LLMResponse:
        """Parse Ollama response"""
        message = result.get('message', {})
        content = message.get('content', '')
        
        # Extract usage info if available
        prompt_eval_count = result.get('prompt_eval_count', 0)
        eval_count = result.get('eval_count', 0)
        
        return LLMResponse(
            content=content,
            tool_calls=[],  # Ollama tools not implemented yet
            finish_reason='stop' if result.get('done', True) else 'incomplete',
            usage={
                'prompt_tokens': prompt_eval_count,
                'completion_tokens': eval_count,
                'total_tokens': prompt_eval_count + eval_count
            },
            raw_response=result
        )
    
    def check_health(self) -> bool:
        """Check if Ollama is running"""
        try:
            url = f"{self.endpoint}/api/tags"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """List available models in Ollama"""
        try:
            url = f"{self.endpoint}/api/tags"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                return [m.get('name', '') for m in result.get('models', [])]
        except:
            return []
