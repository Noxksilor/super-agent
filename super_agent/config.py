"""
Configuration for Super Agent
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import json


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: str = "ollama"  # openai, anthropic, google, ollama
    api_key: str = ""
    model: str = "llama3.2:3b"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class ToolConfig:
    """Tool configuration"""
    allowed_commands: List[str] = field(default_factory=lambda: [
        "python", "pip", "git", "docker", "n8n", "node", "npm"
    ])
    allowed_directories: List[str] = field(default_factory=lambda: [
        "C:\\ps_jobs",
        "C:\\n8n_workflows",
        "./workspace"
    ])
    max_command_timeout: int = 300  # seconds
    web_search_enabled: bool = True
    http_requests_enabled: bool = True


@dataclass
class AgentConfig:
    """Main agent configuration"""
    name: str = "SuperAgent"
    max_iterations: int = 100
    log_level: str = "INFO"
    log_dir: str = "./logs"
    workspace_dir: str = "./workspace"
    
    # Sub-configs
    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    
    # Project-specific paths
    ps_agent_mvp_path: str = "C:\\ps_jobs\\job_0001"
    n8n_endpoint: str = "http://localhost:5678"


def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """Load configuration from file or environment"""
    config = AgentConfig()
    
    # Try to load from file
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Update LLM config
        if 'llm' in data:
            for key, value in data['llm'].items():
                if hasattr(config.llm, key):
                    setattr(config.llm, key, value)
        
        # Update tool config
        if 'tools' in data:
            for key, value in data['tools'].items():
                if hasattr(config.tools, key):
                    setattr(config.tools, key, value)
        
        # Update main config
        for key in ['name', 'max_iterations', 'log_level', 'log_dir', 
                    'workspace_dir', 'ps_agent_mvp_path', 'n8n_endpoint']:
            if key in data:
                setattr(config, key, data[key])
    
    # Override with environment variables
    env_mappings = {
        'OPENAI_API_KEY': ('llm', 'api_key'),
        'ANTHROPIC_API_KEY': ('llm', 'api_key'),
        'GOOGLE_API_KEY': ('llm', 'api_key'),
        'LLM_PROVIDER': ('llm', 'provider'),
        'LLM_MODEL': ('llm', 'model'),
        'PS_AGENT_MVP_PATH': (None, 'ps_agent_mvp_path'),
        'N8N_ENDPOINT': (None, 'n8n_endpoint'),
    }
    
    for env_var, (subconfig, attr) in env_mappings.items():
        value = os.environ.get(env_var)
        if value:
            if subconfig:
                getattr(config, subconfig).__setattr__(attr, value)
            else:
                setattr(config, attr, value)
    
    # Auto-detect provider from API key (only if explicitly set)
    # Ollama is the default and doesn't need API key
    if os.environ.get('OPENAI_API_KEY'):
        config.llm.provider = "openai"
        config.llm.model = "gpt-4o-mini"
        config.llm.api_key = os.environ.get('OPENAI_API_KEY')
    elif os.environ.get('ANTHROPIC_API_KEY'):
        config.llm.provider = "anthropic"
        config.llm.model = "claude-3-sonnet-20240229"
    elif os.environ.get('GOOGLE_API_KEY'):
        config.llm.provider = "google"
        config.llm.model = "gemini-1.5-flash"
    
    return config


def save_config(config: AgentConfig, config_path: str) -> None:
    """Save configuration to file"""
    data = {
        'name': config.name,
        'max_iterations': config.max_iterations,
        'log_level': config.log_level,
        'log_dir': config.log_dir,
        'workspace_dir': config.workspace_dir,
        'ps_agent_mvp_path': config.ps_agent_mvp_path,
        'n8n_endpoint': config.n8n_endpoint,
        'llm': {
            'provider': config.llm.provider,
            'model': config.llm.model,
            'max_tokens': config.llm.max_tokens,
            'temperature': config.llm.temperature,
        },
        'tools': {
            'allowed_commands': config.tools.allowed_commands,
            'allowed_directories': config.tools.allowed_directories,
            'max_command_timeout': config.tools.max_command_timeout,
            'web_search_enabled': config.tools.web_search_enabled,
            'http_requests_enabled': config.tools.http_requests_enabled,
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
