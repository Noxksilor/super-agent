"""
Base tool class and result type
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import json


@dataclass
class ToolResult:
    """Result of a tool execution"""
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'data': self.data
        }
    
    def __str__(self) -> str:
        if self.success:
            return f"SUCCESS: {self.output}"
        return f"ERROR: {self.error or self.output}"


class BaseTool(ABC):
    """Base class for all tools"""
    
    name: str = "base_tool"
    description: str = "Base tool class"
    parameters_schema: Dict[str, Any] = {}
    
    def __init__(self, config: Any = None):
        self.config = config
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema
        }
    
    def validate_parameters(self, **kwargs) -> tuple:
        """Validate parameters against schema"""
        if not self.parameters_schema:
            return True, None
        
        required = self.parameters_schema.get('required', [])
        properties = self.parameters_schema.get('properties', {})
        
        # Check required parameters
        for param in required:
            if param not in kwargs:
                return False, f"Missing required parameter: {param}"
        
        # Check parameter types (basic validation)
        for key, value in kwargs.items():
            if key in properties:
                expected_type = properties[key].get('type')
                if expected_type:
                    type_map = {
                        'string': str,
                        'integer': int,
                        'number': (int, float),
                        'boolean': bool,
                        'array': list,
                        'object': dict
                    }
                    if expected_type in type_map:
                        if not isinstance(value, type_map[expected_type]):
                            return False, f"Parameter {key} must be of type {expected_type}"
        
        return True, None
    
    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to OpenAI tool format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }
    
    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters_schema
        }
