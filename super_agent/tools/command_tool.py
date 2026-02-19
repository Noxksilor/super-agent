"""
Command execution tool
"""

import subprocess
import shlex
import os
from typing import Optional, Dict, Any
from .base import BaseTool, ToolResult


class CommandTool(BaseTool):
    """Execute shell commands"""
    
    name = "execute_command"
    description = """Execute a shell command on the system. 
Use this to run python scripts, git commands, docker, n8n, or other CLI tools.
Commands are validated against allowed commands list for safety."""
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command (optional)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 300)",
                "default": 300
            },
            "env": {
                "type": "object",
                "description": "Environment variables to set",
                "additionalProperties": {"type": "string"}
            }
        },
        "required": ["command"]
    }
    
    def execute(self, command: str, cwd: Optional[str] = None, 
                timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None,
                **kwargs) -> ToolResult:
        try:
            # Validate command
            is_allowed, error = self._validate_command(command)
            if not is_allowed:
                return ToolResult(
                    success=False,
                    output="",
                    error=error
                )
            
            # Validate working directory
            if cwd and not self._is_path_allowed(cwd):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Access denied: working directory '{cwd}' is not in allowed directories"
                )
            
            # Set timeout
            if timeout is None:
                timeout = self.config.tools.max_command_timeout if self.config else 300
            
            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                timeout=timeout,
                capture_output=True,
                text=True,
                env=exec_env
            )
            
            # Prepare output
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            
            success = result.returncode == 0
            
            return ToolResult(
                success=success,
                output=output.strip() if output.strip() else "(no output)",
                error=None if success else f"Command exited with code {result.returncode}",
                data={
                    'return_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'command': command,
                    'cwd': cwd
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout} seconds"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _validate_command(self, command: str) -> tuple:
        """Validate that command uses allowed executables"""
        if not self.config or not hasattr(self.config, 'tools'):
            return True, None
        
        allowed_commands = self.config.tools.allowed_commands
        
        # Parse the command to get the base executable
        try:
            # Handle shell operators and pipes by taking the first command
            base_command = command.split('|')[0].split('&&')[0].split('||')[0].strip()
            
            # Get the executable name
            parts = shlex.split(base_command)
            if not parts:
                return False, "Empty command"
            
            executable = parts[0].lower()
            
            # On Windows, check for .exe, .bat, .cmd extensions
            for ext in ['', '.exe', '.bat', '.cmd', '.ps1']:
                check_name = executable + ext if ext else executable
                if check_name in allowed_commands or executable in allowed_commands:
                    return True, None
            
            # Check if any allowed command matches
            for allowed in allowed_commands:
                if executable == allowed or executable.endswith(allowed):
                    return True, None
            
            return False, f"Command '{executable}' is not in allowed commands: {allowed_commands}"
        except Exception as e:
            return False, f"Failed to parse command: {e}"
    
    def _is_path_allowed(self, path: str) -> bool:
        if not self.config or not hasattr(self.config, 'tools'):
            return True
        allowed_dirs = self.config.tools.allowed_directories
        abs_path = os.path.abspath(path)
        for allowed_dir in allowed_dirs:
            if abs_path.startswith(os.path.abspath(allowed_dir)):
                return True
        return False
